# Region Growing segmentation (GRASS i.segment) of the 2024-09-13 mosaic.
# Runs GRASS through the "grass_obia" conda environment, block by block.

import os
import subprocess
import shutil
import rasterio
from rasterio.windows import Window
import geopandas as gpd
import pandas as pd
import numpy as np
import warnings
from shapely.geometry import box
from shapely.errors import ShapelyDeprecationWarning
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

tile_size = 3000
buffer_size = 500      # overlap read around each block, clipped out afterwards
vMemory = 4000         # MB per GRASS process
max_workers = 28
vBands = [1, 2, 3]     # mosaic bands B11, B8A, B02

vScale = 0.7           # i.segment threshold
vMinSize = 20          # pixels

path_img = "data/mosaics/mosaic_2024_09_13.tif"
dir_out = "segmentation/"
os.makedirs(dir_out, exist_ok=True)

out_name = "segmentation_region_growing.gpkg"
path_out_final = os.path.join(dir_out, out_name)

dir_temp = os.path.join(dir_out, "temp_tiles")
os.makedirs(dir_temp, exist_ok=True)
grass_db = os.path.join(dir_temp, "grassdata")


def process_tile_with_overlap(row_off, col_off, tile_size, buffer_size, vBands, path_img, dir_temp, grass_db):
    idx = f"{row_off}_{col_off}"

    path_crop = os.path.join(dir_temp, f"crop_{idx}.tif")
    path_gpkg = os.path.join(dir_temp, f"vec_{idx}.gpkg")
    loc_temp = os.path.join(grass_db, f"loc_{idx}")

    try:
        with rasterio.open(path_img) as src:
            w, h = src.width, src.height

            # block extent without buffer, used to clip the result
            width_unbuffered = min(tile_size, w - col_off)
            height_unbuffered = min(tile_size, h - row_off)
            window_unbuffered = Window(col_off, row_off, width_unbuffered, height_unbuffered)
            transform_unbuffered = src.window_transform(window_unbuffered)

            tl_x, tl_y = transform_unbuffered * (0, 0)
            br_x, br_y = transform_unbuffered * (width_unbuffered, height_unbuffered)
            unbuffered_box = box(min(tl_x, br_x), min(tl_y, br_y), max(tl_x, br_x), max(tl_y, br_y))

            row_start = max(0, row_off - buffer_size)
            row_end = min(h, row_off + height_unbuffered + buffer_size)
            col_start = max(0, col_off - buffer_size)
            col_end = min(w, col_off + width_unbuffered + buffer_size)

            buf_width = col_end - col_start
            buf_height = row_end - row_start
            window_buffered = Window(col_start, row_start, buf_width, buf_height)
            transform_buffered = src.window_transform(window_buffered)

            crop_data = src.read(vBands, window=window_buffered)
            nodata_val = src.nodata if src.nodata is not None else -9999

            # skip empty blocks
            if (crop_data == nodata_val).all() or crop_data.max() <= 0:
                return None

            # reflectance scaled to 0-1
            crop_data = crop_data.astype('float32')
            crop_data[crop_data < 0] = 0.0
            crop_data = np.clip(crop_data / 10000.0, 0.0, 1.0)

            kwargs = src.meta.copy()
            kwargs.update({
                'height': buf_height,
                'width': buf_width,
                'transform': transform_buffered,
                'count': len(vBands),
                'dtype': 'float32',
                'nodata': 0.0
            })

            with rasterio.open(path_crop, 'w', **kwargs) as dst:
                dst.write(crop_data)

        if os.path.exists(loc_temp):
            shutil.rmtree(loc_temp)

        subprocess.run([
            "conda", "run", "-n", "grass_obia",
            "grass", "-c", path_crop, loc_temp, "-e"
        ], capture_output=True, text=True, check=True)

        # -d: Queen neighborhood, -w: normalized band weights
        grass_commands = f"""
        r.import input="{path_crop}" output=matrix_{idx} --overwrite
        i.group group=group_{idx} input=$(g.list type=raster pattern="matrix_{idx}.*" separator=",") --overwrite
        i.segment -w -d group=group_{idx} output=seg_{idx} threshold={vScale} minsize={vMinSize} memory={vMemory} --overwrite
        r.to.vect input=seg_{idx} output=vec_{idx} type=area --overwrite
        v.out.ogr input=vec_{idx} output="{path_gpkg}" format=GPKG --overwrite
        """

        mapset_path = os.path.join(loc_temp, "PERMANENT")
        subprocess.run([
            "conda", "run", "-n", "grass_obia",
            "grass", mapset_path, "--exec", "sh", "-c", grass_commands
        ], capture_output=True, text=True, check=True)

        if os.path.exists(path_gpkg):
            gdf = gpd.read_file(path_gpkg)
            if not gdf.empty:
                bbox_gdf = gpd.GeoDataFrame(geometry=[unbuffered_box], crs=gdf.crs)
                gdf_filt = gpd.clip(gdf, bbox_gdf)
                return gdf_filt if not gdf_filt.empty else None

        return None

    except subprocess.CalledProcessError as e:
        print(f"\n[GRASS error - block {idx}]\n{e.stderr}\n")
        return None
    except Exception as e:
        print(f"\n[Python error - block {idx}]: {str(e)}\n")
        return None
    finally:
        if os.path.exists(loc_temp): shutil.rmtree(loc_temp)
        if os.path.exists(path_crop): os.remove(path_crop)
        if os.path.exists(path_gpkg): os.remove(path_gpkg)


if __name__ == '__main__':
    tiles_to_process = []
    with rasterio.open(path_img) as src:
        w, h = src.width, src.height
        for row_off in range(0, h, tile_size):
            for col_off in range(0, w, tile_size):
                tiles_to_process.append((row_off, col_off))

    geometries = []
    total_tiles = len(tiles_to_process)
    tiles_done = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_tile_with_overlap, r, c, tile_size, buffer_size, vBands, path_img, dir_temp, grass_db): (r, c)
            for r, c in tiles_to_process
        }

        for future in as_completed(futures):
            r, c = futures[future]
            tiles_done += 1
            try:
                gdf_result = future.result()
                if gdf_result is not None:
                    geometries.append(gdf_result)
                    print(f"[{tiles_done}/{total_tiles}] Segmented: row {r}, column {c}")
                else:
                    print(f"[{tiles_done}/{total_tiles}] Skipped (nodata): row {r}, column {c}")
            except Exception as exc:
                print(f"[{tiles_done}/{total_tiles}] Failed: block {r}_{c}: {exc}")

    if geometries:
        gdf_final = pd.concat(geometries, ignore_index=True)
        gdf_final.to_file(path_out_final, driver="GPKG")
        print(f"Saved: {out_name}")
    else:
        print("No valid block produced geometries.")

    if os.path.exists(dir_temp):
        shutil.rmtree(dir_temp)
