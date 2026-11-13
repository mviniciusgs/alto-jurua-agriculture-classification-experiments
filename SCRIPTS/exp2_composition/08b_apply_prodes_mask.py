# Applies the PRODES masks to the classification mosaics:
# non-forest (code 3) -> 14 (NFLO) over any class; forest (code 1) -> 13 (FLO) only
# over VSA (11) and VSI (12).

import os
import sys
import rioxarray
import numpy as np

MAP_NAMES = ["map_DB_FULL", "map_DB_B", "map_DB_B_IS", "map_DB_B_S"]

mosaics_dir = "data/classification/mosaics"
masks_dir   = "maps"
output_dir  = "data/classification/final_maps"

os.makedirs(output_dir, exist_ok=True)

forest_mask_raw    = rioxarray.open_rasterio(os.path.join(masks_dir, "prodes_forest_2024.tif"), masked=False)
nonforest_mask_raw = rioxarray.open_rasterio(os.path.join(masks_dir, "prodes_nonforest_2024.tif"), masked=False)

mosaic_files = [os.path.join(mosaics_dir, f"{n}.tif") for n in MAP_NAMES]
mosaic_files = [p for p in mosaic_files if os.path.exists(p)]

if not mosaic_files:
    sys.exit(f"No mosaic found in {mosaics_dir}")

# crop the PRODES masks to the extent of the mosaics once, before the loop
min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")
for path in mosaic_files:
    with rioxarray.open_rasterio(path) as r:
        b = r.rio.bounds()
        min_x, min_y = min(min_x, b[0]), min(min_y, b[1])
        max_x, max_y = max(max_x, b[2]), max(max_y, b[3])

target_crs = rioxarray.open_rasterio(mosaic_files[0]).rio.crs
forest_mask_crop    = forest_mask_raw.rio.clip_box(min_x, min_y, max_x, max_y, crs=target_crs)
nonforest_mask_crop = nonforest_mask_raw.rio.clip_box(min_x, min_y, max_x, max_y, crs=target_crs)

for mosaic_path in sorted(mosaic_files):
    name = os.path.basename(mosaic_path)
    print(name)

    mosaic = rioxarray.open_rasterio(mosaic_path, masked=False)
    mosaic.rio.write_nodata(0, inplace=True)

    forest_res    = forest_mask_crop.rio.reproject_match(mosaic, resampling=0)      # nearest
    nonforest_res = nonforest_mask_crop.rio.reproject_match(mosaic, resampling=0)

    is_secondary_veg = (mosaic.values == 11) | (mosaic.values == 12)

    final_values = np.where(
        nonforest_res.values == 3, 14,
        np.where(is_secondary_veg & (forest_res.values == 1), 13, mosaic.values)
    )

    final_mosaic = mosaic.copy(data=final_values)
    final_mosaic.rio.write_nodata(0, inplace=True)
    final_mosaic = final_mosaic.astype(np.uint8)

    final_mosaic.rio.to_raster(
        os.path.join(output_dir, name),
        dtype="uint8",
        compress="lzw",
        tiled=True,
        windowed=True
    )

    mosaic.close()
    forest_res.close()
    nonforest_res.close()

forest_mask_raw.close()
nonforest_mask_raw.close()
