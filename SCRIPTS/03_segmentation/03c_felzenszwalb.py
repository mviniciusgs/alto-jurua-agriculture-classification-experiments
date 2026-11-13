# Felzenszwalb segmentation of the 2024-09-13 mosaic, in 8 x 8 blocks with overlap.
# Small polygons inside PRODES forest are merged into their largest neighbor.

import os
# one BLAS thread per worker to avoid oversubscription in the pool
os.environ["MALLOC_TRIM_THRESHOLD_"] = "0"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import gc
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.features import shapes
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, box
from skimage.segmentation import felzenszwalb
from rasterstats import zonal_stats
import warnings
from multiprocessing import Pool
from tqdm import tqdm

warnings.filterwarnings("ignore")

input_tiff = "data/mosaics/mosaic_2024_09_13.tif"
mask_prodes = "maps/prodes_forest_2024.tif"
output_dir = "segmentation/"
os.makedirs(output_dir, exist_ok=True)

output_gpkg = os.path.join(output_dir, "segmentation_felzenszwalb.gpkg")

SCALE = 200
SIGMA = 0.2
MIN_SIZE = 20
PIXEL_LIMIT = 50     # polygons with fewer PRODES forest pixels are merged
NUM_CORES = 40

N_TILES_X = 8
N_TILES_Y = 8
BUFFER_PIXELS = 120


def process_block(args):
    window_id, data_window, buffer_window, buffer_transform, mosaic_crs, prodes_crs = args

    with rasterio.open(input_tiff) as src:
        img = src.read([2, 4, 5], window=buffer_window)    # mosaic bands B8A, NDVI, SOIL
        data_mask = np.any(img > 0, axis=0)
        data_bounds = src.window_bounds(data_window)

    if not np.any(data_mask):
        return None

    img_reshaped = np.moveaxis(img, 0, -1)
    del img

    segments = felzenszwalb(img_reshaped, scale=SCALE, sigma=SIGMA, min_size=MIN_SIZE)
    segments = segments.astype(np.int32)
    del img_reshaped

    polygons = []
    ids = []
    for geom, val in shapes(segments, mask=data_mask, transform=buffer_transform):
        polygons.append(shape(geom))
        ids.append(int(val) + (window_id * 5000000))

    del segments, data_mask

    if not polygons:
        return None

    gdf_block = gpd.GeoDataFrame({'segment_id': ids, 'geometry': polygons}, crs=mosaic_crs)

    # same CRS as the PRODES mask before clipping and zonal stats
    if gdf_block.crs != prodes_crs:
        gdf_block = gdf_block.to_crs(prodes_crs)

    clip_df = gpd.GeoDataFrame(geometry=[box(*data_bounds)], crs=mosaic_crs)
    if clip_df.crs != prodes_crs:
        clip_df = clip_df.to_crs(prodes_crs)

    gdf_block = gpd.clip(gdf_block, clip_df.geometry.iloc[0])

    gdf_block = gdf_block[gdf_block.geometry.is_valid & (~gdf_block.geometry.is_empty)]
    if gdf_block.empty:
        return None

    stats = zonal_stats(gdf_block, mask_prodes, stats=['sum'], nodata=0)
    gdf_block['forest_pixels'] = [s['sum'] if s['sum'] is not None else 0 for s in stats]

    return gdf_block


if __name__ == "__main__":
    with rasterio.open(mask_prodes) as src_p:
        prodes_crs = src_p.crs

    with rasterio.open(input_tiff) as src:
        width = src.width
        height = src.height
        mosaic_crs = src.crs

        block_w = int(width / N_TILES_X)
        block_h = int(height / N_TILES_Y)

        block_args = []
        window_id = 0

        for i in range(N_TILES_X):
            for j in range(N_TILES_Y):
                col_off = i * block_w
                row_off = j * block_h
                w = block_w if (col_off + block_w) <= width else (width - col_off)
                h = block_h if (row_off + block_h) <= height else (height - row_off)

                data_window = Window(col_off, row_off, w, h)

                col_off_buf = max(0, col_off - BUFFER_PIXELS)
                row_off_buf = max(0, row_off - BUFFER_PIXELS)
                w_buf = min(width, col_off + w + BUFFER_PIXELS) - col_off_buf
                h_buf = min(height, row_off + h + BUFFER_PIXELS) - row_off_buf

                buffer_window = Window(col_off_buf, row_off_buf, w_buf, h_buf)
                buffer_transform = src.window_transform(buffer_window)

                block_args.append((window_id, data_window, buffer_window, buffer_transform, mosaic_crs, prodes_crs))
                window_id += 1

    gdfs = []
    with Pool(NUM_CORES) as pool:
        for gdf_result in tqdm(pool.imap_unordered(process_block, block_args),
                               total=len(block_args), desc="Blocks", unit=" block"):
            if gdf_result is not None and not gdf_result.empty:
                gdfs.append(gdf_result)

    if gdfs:
        gdf_global = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=prodes_crs)
        del gdfs
        gc.collect()

        is_small = (gdf_global['forest_pixels'] > 0) & (gdf_global['forest_pixels'] < PIXEL_LIMIT)
        gdf_small = gdf_global[is_small]
        gdf_large = gdf_global[~is_small]

        if not gdf_small.empty and not gdf_large.empty:
            neighbors = gpd.sjoin(gdf_small, gdf_large, how='inner', predicate='intersects')

            if not neighbors.empty:
                neighbors['neighbor_area'] = neighbors.geometry.area
                largest_neighbors = neighbors.sort_values('neighbor_area').groupby(level=0).last()

                mapping = largest_neighbors['segment_id_right'].to_dict()
                gdf_global.loc[mapping.keys(), 'segment_id'] = list(mapping.values())

                gdf_global = gdf_global.dissolve(by='segment_id', as_index=False)

        if 'forest_pixels' in gdf_global.columns:
            gdf_global = gdf_global.drop(columns=['forest_pixels'])

        if gdf_global.crs != mosaic_crs:
            gdf_global = gdf_global.to_crs(mosaic_crs)

        gdf_global.to_file(output_gpkg, driver="GPKG")
        print(f"Saved: {output_gpkg}")
    else:
        print("No polygon was generated.")
