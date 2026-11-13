# Regularizes the landscape metrics of each segmentation and merges them into the
# 2024 spectral cube. Run from the repository root (the saved cubes keep relative paths).

library(sits)
library(sf)

ROI <- st_read("roi/study_area.shp")
s2_cube_local <- readRDS("data/cube/2024_BDC/s2_cube_local.rds")

period <- "P16D"

dir_metrics_GRASS        <- "data/cube/metrics/GRASS/"
input_dir_GRASS          <- "data/metrics/GRASS"

dir_metrics_SNIC         <- "data/cube/metrics/SNIC/"
input_dir_SNIC           <- "data/metrics/SNIC"

dir_metrics_FELZENSZWALB <- "data/cube/metrics/FELZENSZWALB/"
input_dir_FELZENSZWALB   <- "data/metrics/FELZENSZWALB"

if (!dir.exists(dir_metrics_GRASS))        dir.create(dir_metrics_GRASS, recursive = TRUE)
if (!dir.exists(dir_metrics_SNIC))         dir.create(dir_metrics_SNIC, recursive = TRUE)
if (!dir.exists(dir_metrics_FELZENSZWALB)) dir.create(dir_metrics_FELZENSZWALB, recursive = TRUE)

# Defines the SEGMENTATION-METRICS collection (AREA, PERIM, SHAPE with their own value limits)
sits_config(config_user_file = "config/sits_config_user.yml")

cube_metrics_GRASS <- sits_cube(
  source     = "BDC",
  collection = "SEGMENTATION-METRICS",
  data_dir   = input_dir_GRASS,
  parse_info = c("satellite", "sensor", "tile", "band", "date")
)

cube_metrics_GRASS <- sits_regularize(
  cube       = cube_metrics_GRASS,
  period     = period,
  roi        = ROI,
  res        = 10,
  multicores = 28,
  memsize    = 180,
  progress   = TRUE,
  output_dir = dir_metrics_GRASS
)

reg_cube_metrics_GRASS <- sits_merge(s2_cube_local, cube_metrics_GRASS)

cube_metrics_SNIC <- sits_cube(
  source     = "BDC",
  collection = "SEGMENTATION-METRICS",
  data_dir   = input_dir_SNIC,
  parse_info = c("satellite", "sensor", "tile", "band", "date")
)

cube_metrics_SNIC <- sits_regularize(
  cube       = cube_metrics_SNIC,
  period     = period,
  roi        = ROI,
  res        = 10,
  multicores = 28,
  memsize    = 180,
  progress   = TRUE,
  output_dir = dir_metrics_SNIC
)

reg_cube_metrics_SNIC <- sits_merge(s2_cube_local, cube_metrics_SNIC)

cube_metrics_FELZENSZWALB <- sits_cube(
  source     = "BDC",
  collection = "SEGMENTATION-METRICS",
  data_dir   = input_dir_FELZENSZWALB,
  parse_info = c("satellite", "sensor", "tile", "band", "date")
)

cube_metrics_FELZENSZWALB <- sits_regularize(
  cube       = cube_metrics_FELZENSZWALB,
  period     = period,
  roi        = ROI,
  res        = 10,
  multicores = 28,
  memsize    = 180,
  progress   = TRUE,
  output_dir = dir_metrics_FELZENSZWALB
)

reg_cube_metrics_FELZENSZWALB <- sits_merge(s2_cube_local, cube_metrics_FELZENSZWALB)

save(reg_cube_metrics_GRASS, reg_cube_metrics_SNIC, reg_cube_metrics_FELZENSZWALB,
     file = "data/cube/cubes_segmentation_metrics.RData")
