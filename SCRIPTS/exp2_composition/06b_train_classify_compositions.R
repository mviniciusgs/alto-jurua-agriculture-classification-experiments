# Cube composition experiment, on the Region Growing (GRASS) cube.
# DB_IS and DB_S correspond to the maps DB_B_IS and DB_B_S.
# Run from the repository root.

library(sits)
library(readr)
library(dplyr)

load("data/cube/cubes_segmentation_metrics.RData")
stopifnot(exists("reg_cube_metrics_GRASS"))

N_CORES        <- 24
MEM_CLASS      <- 150
N_CORES_SMOOTH <- 5
SEED           <- 146

samples_2024 <- read_csv("samples/training_samples_2024.csv")

samples_2024_sits <- samples_2024 %>%
  mutate(
    start_date = as.Date("2024-01-01"),
    end_date   = as.Date("2024-12-31")
  ) %>%
  rename(label = class)

spectral_bands <- c("B02","B03","B04","B05","B06","B07","B08","B8A","B11","B12")
index_bands    <- c("EVI","NDVI","NBR","FOREST","SOIL","WATER")
metric_bands   <- c("AREA","PERIM","SHAPE")

# ---- DB_FULL ----

output_dir_DB_FULL_GRASS <- "data/classification/V3_EXP/GRASS/DB_FULL"
if (!dir.exists(output_dir_DB_FULL_GRASS)) dir.create(output_dir_DB_FULL_GRASS, recursive = TRUE)

DB_FULL_GRASS <- reg_cube_metrics_GRASS

samples_DB_FULL_GRASS <- sits_get_data(
  cube       = DB_FULL_GRASS,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_DB_FULL_GRASS <- "DB_FULL-GRASS-ST2A-16d-rfor-2024-V1"

set.seed(SEED)
model_DB_FULL_GRASS <- sits_train(
  samples_DB_FULL_GRASS,
  ml_method = sits_rfor(num_trees = 200)
)

probs_DB_FULL_GRASS <- sits_classify(
  data       = DB_FULL_GRASS,
  ml_model   = model_DB_FULL_GRASS,
  output_dir = output_dir_DB_FULL_GRASS,
  version    = version_DB_FULL_GRASS,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

bayes_DB_FULL_GRASS <- sits_smooth(
  cube           = probs_DB_FULL_GRASS,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_DB_FULL_GRASS,
  version        = paste(version_DB_FULL_GRASS, "w13-nf05-s20-V1", sep = "-")
)

class_DB_FULL_GRASS <- sits_label_classification(
  cube       = bayes_DB_FULL_GRASS,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_DB_FULL_GRASS,
  version    = paste(version_DB_FULL_GRASS, "w13-nf05-s20-V1", sep = "-")
)

# ---- DB_B ----

output_dir_DB_B_GRASS <- "data/classification/V3_EXP/GRASS/DB_B"
if (!dir.exists(output_dir_DB_B_GRASS)) dir.create(output_dir_DB_B_GRASS, recursive = TRUE)

DB_B_GRASS <- sits_select(
  data  = reg_cube_metrics_GRASS,
  bands = spectral_bands
)

samples_DB_B_GRASS <- sits_get_data(
  cube       = DB_B_GRASS,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_DB_B_GRASS <- "DB_B-GRASS-ST2A-16d-rfor-2024-V1"

set.seed(SEED)
model_DB_B_GRASS <- sits_train(
  samples_DB_B_GRASS,
  ml_method = sits_rfor(num_trees = 200)
)

probs_DB_B_GRASS <- sits_classify(
  data       = DB_B_GRASS,
  ml_model   = model_DB_B_GRASS,
  output_dir = output_dir_DB_B_GRASS,
  version    = version_DB_B_GRASS,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

bayes_DB_B_GRASS <- sits_smooth(
  cube           = probs_DB_B_GRASS,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_DB_B_GRASS,
  version        = paste(version_DB_B_GRASS, "w13-nf05-s20-V1", sep = "-")
)

class_DB_B_GRASS <- sits_label_classification(
  cube       = bayes_DB_B_GRASS,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_DB_B_GRASS,
  version    = paste(version_DB_B_GRASS, "w13-nf05-s20-V1", sep = "-")
)

# ---- DB_IS ----

output_dir_DB_IS_GRASS <- "data/classification/V3_EXP/GRASS/DB_IS"
if (!dir.exists(output_dir_DB_IS_GRASS)) dir.create(output_dir_DB_IS_GRASS, recursive = TRUE)

DB_IS_GRASS <- sits_select(
  data  = reg_cube_metrics_GRASS,
  bands = c(spectral_bands, index_bands)
)

samples_DB_IS_GRASS <- sits_get_data(
  cube       = DB_IS_GRASS,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_DB_IS_GRASS <- "DB_IS-GRASS-ST2A-16d-rfor-2024-V1"

set.seed(SEED)
model_DB_IS_GRASS <- sits_train(
  samples_DB_IS_GRASS,
  ml_method = sits_rfor(num_trees = 200)
)

probs_DB_IS_GRASS <- sits_classify(
  data       = DB_IS_GRASS,
  ml_model   = model_DB_IS_GRASS,
  output_dir = output_dir_DB_IS_GRASS,
  version    = version_DB_IS_GRASS,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

bayes_DB_IS_GRASS <- sits_smooth(
  cube           = probs_DB_IS_GRASS,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_DB_IS_GRASS,
  version        = paste(version_DB_IS_GRASS, "w13-nf05-s20-V1", sep = "-")
)

class_DB_IS_GRASS <- sits_label_classification(
  cube       = bayes_DB_IS_GRASS,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_DB_IS_GRASS,
  version    = paste(version_DB_IS_GRASS, "w13-nf05-s20-V1", sep = "-")
)

# ---- DB_S ----

output_dir_DB_S_GRASS <- "data/classification/V3_EXP/GRASS/DB_S"
if (!dir.exists(output_dir_DB_S_GRASS)) dir.create(output_dir_DB_S_GRASS, recursive = TRUE)

DB_S_GRASS <- sits_select(
  data  = reg_cube_metrics_GRASS,
  bands = c(spectral_bands, metric_bands)
)

samples_DB_S_GRASS <- sits_get_data(
  cube       = DB_S_GRASS,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_DB_S_GRASS <- "DB_S-GRASS-ST2A-16d-rfor-2024-V1"

set.seed(SEED)
model_DB_S_GRASS <- sits_train(
  samples_DB_S_GRASS,
  ml_method = sits_rfor(num_trees = 200)
)

probs_DB_S_GRASS <- sits_classify(
  data       = DB_S_GRASS,
  ml_model   = model_DB_S_GRASS,
  output_dir = output_dir_DB_S_GRASS,
  version    = version_DB_S_GRASS,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

bayes_DB_S_GRASS <- sits_smooth(
  cube           = probs_DB_S_GRASS,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_DB_S_GRASS,
  version        = paste(version_DB_S_GRASS, "w13-nf05-s20-V1", sep = "-")
)

class_DB_S_GRASS <- sits_label_classification(
  cube       = bayes_DB_S_GRASS,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_DB_S_GRASS,
  version    = paste(version_DB_S_GRASS, "w13-nf05-s20-V1", sep = "-")
)
