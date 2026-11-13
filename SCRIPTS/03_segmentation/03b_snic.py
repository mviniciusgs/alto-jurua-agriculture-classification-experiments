# SNIC segmentation of the 2024-09-13 mosaic, block by block.

import os
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape
import warnings
from tqdm import tqdm
import concurrent.futures

warnings.filterwarnings("ignore")


def process_snic_block(args):
    input_tiff, col_r, row_r, w_tile, h_tile, bands, num_segments, compactness = args
    window = Window(col_r, row_r, w_tile, h_tile)

    try:
        with rasterio.open(input_tiff) as src:
            window_transform = src.window_transform(window)
            img_tile = src.read(bands, window=window)

        data_mask = np.any(img_tile > 0, axis=0)

        if not np.any(data_mask):
            return []

        img_reshaped = np.moveaxis(img_tile, 0, -1).astype(np.float64)

        from pysnic.algorithms.snic import snic

        segments_list, _, _ = snic(
            img_reshaped.tolist(),
            num_segments,
            compactness
        )

        segments = np.array(segments_list, dtype=np.int32)

        return [shape(geom) for geom, val in shapes(segments, mask=data_mask, transform=window_transform)]

    except Exception as e:
        return {"error": f"Block col={col_r}, row={row_r} failed: {str(e)}"}


if __name__ == '__main__':

    input_tiff = "data/mosaics/mosaic_2024_09_13.tif"
    output_dir = "segmentation"
    os.makedirs(output_dir, exist_ok=True)
    output_gpkg = os.path.join(output_dir, "segmentation_snic.gpkg")

    N_CORES = 15               # kept low: pysnic lists use a lot of memory
    TILE_SIZE = 3000
    TARGET_BANDS = [1, 4, 5]   # mosaic bands B11, NDVI, SOIL
    NUM_SEGMENTS = 15000       # per block
    COMPACTNESS = 0.1

    with rasterio.open(input_tiff) as src:
        total_width = src.width
        total_height = src.height
        original_crs = src.crs

    block_cols = list(range(0, total_width, TILE_SIZE))
    block_rows = list(range(0, total_height, TILE_SIZE))
    print(f"{len(block_cols) * len(block_rows)} blocks of {TILE_SIZE}x{TILE_SIZE} px, {N_CORES} processes")

    tasks = []
    for r in block_rows:
        for c in block_cols:
            h_tile = min(TILE_SIZE, total_height - r)
            w_tile = min(TILE_SIZE, total_width - c)
            tasks.append((input_tiff, c, r, w_tile, h_tile, TARGET_BANDS, NUM_SEGMENTS, COMPACTNESS))

    all_polygons = []
    errors = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=N_CORES) as executor:
        futures = {executor.submit(process_snic_block, task): task for task in tasks}

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Blocks"):
            result = future.result()

            if isinstance(result, dict) and "error" in result:
                errors.append(result["error"])
            else:
                all_polygons.extend(result)

    if errors:
        print(f"\n{len(errors)} blocks failed:")
        for err in errors[:5]:
            print(err)
        if len(errors) > 5:
            print("...")

    if len(all_polygons) > 0:
        gdf = gpd.GeoDataFrame(
            {'id_snic': range(1, len(all_polygons) + 1)},
            geometry=all_polygons,
            crs=original_crs
        )
        gdf.to_file(output_gpkg, driver="GPKG")
        print(f"Saved: {output_gpkg} ({len(all_polygons)} polygons)")
    else:
        print("No valid polygon was generated.")
