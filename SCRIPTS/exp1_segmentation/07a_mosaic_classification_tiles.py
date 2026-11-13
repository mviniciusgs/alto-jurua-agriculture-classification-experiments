# Mosaics the classified tiles (sits output) of each segmentation into a single raster.

import contextlib
from pathlib import Path
import rasterio
from rasterio.merge import merge

root_dir = Path("data/classification")
output_dir = root_dir / "mosaics"

# class folder -> name of the output mosaic
target_folders = {
    root_dir / "V3_SEG" / "GRASS":        "map_region_growing",
    root_dir / "V3_SEG" / "FELZENSZWALB": "map_felzenszwalb",
    root_dir / "V3_SEG" / "SNIC":         "map_snic",
}

output_dir.mkdir(parents=True, exist_ok=True)

for folder, mosaic_name in target_folders.items():
    if not folder.exists():
        print(f"Warning: folder not found -> {folder}")
        continue

    class_files = list(folder.glob("*class*.tif"))

    if not class_files:
        print(f"Warning: no 'class*.tif' file in {folder}")
        continue

    print(f"{folder}: {len(class_files)} files")

    out_path = output_dir / f"{mosaic_name}.tif"

    try:
        with contextlib.ExitStack() as stack:
            datasets = [stack.enter_context(rasterio.open(f)) for f in class_files]
            mosaic, out_transform = merge(datasets)
            out_meta = datasets[0].meta.copy()

        out_meta.update({
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform
        })

        with rasterio.open(out_path, "w", **out_meta) as dest:
            dest.write(mosaic)

        print(f"Saved: {out_path}")

    except Exception as e:
        print(f"Failed to mosaic {mosaic_name}: {e}")
