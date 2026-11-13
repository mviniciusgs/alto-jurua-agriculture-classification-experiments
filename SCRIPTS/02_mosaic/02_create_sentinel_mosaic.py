# Mosaic of the 2024-09-13 composition (all tiles, 7 bands), input of the segmentations.

import re
import gc
from pathlib import Path
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject
from rasterio.enums import Resampling

source_dir = Path("data/cube/2024_BDC")
output_dir = Path("data/mosaics")
output_dir.mkdir(parents=True, exist_ok=True)

tiles = ["001014", "002015", "002014", "002013", "003013", "003015", "003014"]
dates = ["2024-09-13"]
target_bands = ["B11", "B8A", "B02", "NDVI", "SOIL", "WATER", "FOREST"]

NODATA_IN = -9999
NODATA_OUT = -9999

tiles_pattern = "|".join(tiles)

for d in dates:
    print(f"\n--- Date: {d} ---")

    f_list = {}
    for b in target_bands:
        pattern = re.compile(f"({tiles_pattern}).*_{b}_.*{d}")
        f_list[b] = [
            str(p) for p in source_dir.rglob("*.tif")
            if pattern.search(p.name) and ".sits" not in p.parts
        ]

    missing = [b for b, files in f_list.items() if len(files) == 0]
    if missing:
        print(f"Skipping {d}. Missing files for: {', '.join(missing)}")
        continue

    # B02 sets the output dtype (uint16, reflectance 0-10000); a 0-1 fraction band
    # cast to uint16 would be truncated to 0
    with rasterio.open(f_list["B02"][0]) as src:
        out_dtype = src.profile["dtype"]

    for b in ["SOIL", "FOREST", "WATER"]:
        with rasterio.open(f_list[b][0]) as src:
            arr = src.read(1)
        valid = arr[arr != NODATA_IN]
        if valid.size == 0:
            continue
        if valid.max() <= 1.5 and np.issubdtype(arr.dtype, np.floating) \
                and np.issubdtype(np.dtype(out_dtype), np.integer):
            raise ValueError(f"[{d}] Band '{b}' looks like a 0-1 fraction ({arr.dtype}) "
                             f"but the output dtype is '{out_dtype}'.")

    # the B02 mosaic is the spatial reference for all bands
    b02_datasets = [rasterio.open(f) for f in f_list["B02"]]
    for ds in b02_datasets:
        if ds.nodata != NODATA_IN:
            print(f"Warning: {ds.name} declares nodata={ds.nodata}, expected {NODATA_IN}")

    m_ref, m_ref_transform = merge(b02_datasets, nodata=NODATA_IN)

    with rasterio.open(f_list["B02"][0]) as src:
        out_profile = src.profile.copy()

    for ds in b02_datasets:
        ds.close()

    out_profile.update({
        "height": m_ref.shape[1],
        "width": m_ref.shape[2],
        "transform": m_ref_transform,
        "count": len(target_bands),
        "compress": "lzw",
        "bigtiff": "yes",
        "nodata": NODATA_OUT,
    })

    nodata_mask = (m_ref[0] == NODATA_IN)

    mosaic = np.zeros((len(target_bands), m_ref.shape[1], m_ref.shape[2]), dtype=out_dtype)

    for i, b in enumerate(target_bands):
        if b == "B02":
            mosaic[i] = m_ref[0]
            continue

        b_datasets = [rasterio.open(f) for f in f_list[b]]
        m_temp, m_temp_transform = merge(b_datasets, nodata=NODATA_IN)

        for ds in b_datasets:
            ds.close()

        if b == "NDVI":
            # rescale from [-10000, 10000] to [0, 10000]
            nodata_local = (m_temp[0] == NODATA_IN)
            m_temp = np.round((m_temp.astype(np.float64) + 10000) / 2)
            m_temp[0][nodata_local] = NODATA_OUT

        elif b in ["SOIL", "FOREST", "WATER"]:
            # negative fractions set to 0
            nodata_local = (m_temp[0] == NODATA_IN)
            m_temp[m_temp < 0] = 0
            m_temp[0][nodata_local] = NODATA_OUT

        dest_array = np.full((1, m_ref.shape[1], m_ref.shape[2]), NODATA_OUT, dtype=out_dtype)

        reproject(
            source=m_temp.astype(out_dtype),
            destination=dest_array,
            src_transform=m_temp_transform,
            src_crs=out_profile["crs"],
            dst_transform=m_ref_transform,
            dst_crs=out_profile["crs"],
            src_nodata=NODATA_IN,
            dst_nodata=NODATA_OUT,
            resampling=Resampling.nearest
        )

        mosaic[i] = dest_array[0]
        mosaic[i][nodata_mask] = NODATA_OUT

    out_name = f"mosaic_{d.replace('-', '_')}.tif"

    with rasterio.open(output_dir / out_name, "w", **out_profile) as dst:
        dst.write(mosaic)
        dst.descriptions = tuple(target_bands)

    del m_ref, b02_datasets, mosaic, m_temp, dest_array
    gc.collect()

    print(f"Saved: {out_name}")
