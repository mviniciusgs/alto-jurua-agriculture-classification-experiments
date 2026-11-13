# AREA, PERIM and SHAPE of each segmentation, rasterized on the grid of each tile
# and copied to every 16-day date of the cube (the metrics are static).

import os
import shutil
import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features

reference_dir = "data/cube/2024_BDC/"

dates_16d = [
    "2024-01-01", "2024-01-17", "2024-02-02", "2024-02-18", "2024-03-05",
    "2024-03-21", "2024-04-06", "2024-04-22", "2024-05-08", "2024-05-24",
    "2024-06-09", "2024-06-25", "2024-07-11", "2024-07-27", "2024-08-12",
    "2024-08-28", "2024-09-13", "2024-09-29", "2024-10-15", "2024-10-31",
    "2024-11-16", "2024-12-02", "2024-12-18"
]

tiles = ["001014", "002015", "002014", "002013", "003013", "003015", "003014"]
target_metrics = ["AREA", "PERIM", "SHAPE"]

# B02 of this date gives the grid of each tile
sat, sen, ref_date = "SENTINEL-2", "MSI", "2024-07-27"

datasets = {
    "GRASS": (
        "segmentation/segmentation_region_growing.gpkg",
        "data/metrics/GRASS/",
    ),
    "SNIC": (
        "segmentation/segmentation_snic.gpkg",
        "data/metrics/SNIC/",
    ),
    "FELZENSZWALB": (
        "segmentation/segmentation_felzenszwalb.gpkg",
        "data/metrics/FELZENSZWALB/",
    ),
}


def compute_metrics(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf['AREA'] = gdf.geometry.area / 10000    # ha

    perimeter_m = gdf.geometry.length

    # shape index P / (4 * sqrt(A)), with P in m and A in m2
    gdf['SHAPE'] = perimeter_m / (4 * np.sqrt(gdf.geometry.area))

    gdf['PERIM'] = perimeter_m / 1000    # km

    return gdf


def process_dataset(name: str, path_gpkg: str, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    print(f"\nDataset: {name}")
    gdf = gpd.read_file(path_gpkg)
    gdf = compute_metrics(gdf)
    print(f"{len(gdf)} polygons")

    for tile_id in tiles:
        ref_name = f"{sat}_{sen}_{tile_id}_B02_{ref_date}.tif"
        ref_path = os.path.join(reference_dir, ref_name)

        if not os.path.exists(ref_path):
            print(f"Warning: tile {tile_id} not found at {ref_path}")
            continue

        print(f"Tile {tile_id}")

        with rasterio.open(ref_path) as src:
            meta = src.meta.copy()
            out_transform = src.transform
            out_shape = src.shape
            meta.update(dtype=rasterio.float32, count=1, compress="lzw", tiled=True)

        for metric in target_metrics:
            shapes = (
                (geom, value) for geom, value in zip(gdf.geometry, gdf[metric])
            )

            burned = features.rasterize(
                shapes=shapes,
                out_shape=out_shape,
                transform=out_transform,
                fill=0,
                all_touched=False,
                dtype=rasterio.float32,
            )

            base_path = os.path.join(out_dir, f"{sat}_{sen}_{tile_id}_{metric}_{dates_16d[0]}.tif")

            with rasterio.open(base_path, "w", **meta) as dst:
                dst.write(burned, 1)

            for date in dates_16d[1:]:
                shutil.copyfile(base_path, os.path.join(out_dir, f"{sat}_{sen}_{tile_id}_{metric}_{date}.tif"))

            del burned

    print(f"Dataset {name} done: {out_dir}")


for name, (path_gpkg, out_dir) in datasets.items():
    process_dataset(name, path_gpkg, out_dir)
