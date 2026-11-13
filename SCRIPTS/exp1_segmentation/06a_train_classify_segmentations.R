# Random Forest training, classification and Bayesian smoothing for the cubes with the
# metrics of each segmentation (GRASS = Region Growing, FELZENSZWALB, SNIC).
# Run from the repository root.

library(sits)
library(readr)
library(dplyr)

load("data/cube/cubes_segmentation_metrics.RData")

stopifnot(
  exists("reg_cube_metrics_GRASS"),
  exists("reg_cube_metrics_SNIC"),
  exists("reg_cube_metrics_FELZENSZWALB")
)

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

# ---- Region Growing (GRASS) ----

output_dir_class_GRASS <- "data/classification/V3_SEG/GRASS"
if (!dir.exists(output_dir_class_GRASS)) dir.create(output_dir_class_GRASS, recursive = TRUE)

DB_FULL_seg_GRASS <- reg_cube_metrics_GRASS

samples_seg_GRASS <- sits_get_data(
  cube       = DB_FULL_seg_GRASS,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_seg_GRASS <- "all_samples_GRASS-ST2A-GRASS-16d-rfor-2024-V3"

set.seed(SEED)
model_seg_GRASS <- sits_train(
  samples_seg_GRASS,
  ml_method = sits_rfor(num_trees = 200)
)

probs_cube_seg_GRASS <- sits_classify(
  data       = DB_FULL_seg_GRASS,
  ml_model   = model_seg_GRASS,
  output_dir = output_dir_class_GRASS,
  version    = version_seg_GRASS,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

probs_bayes_seg_GRASS <- sits_smooth(
  cube           = probs_cube_seg_GRASS,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_class_GRASS,
  version        = paste(version_seg_GRASS, "w13-nf05-s20-V1", sep = "-")
)

class_cube_seg_GRASS <- sits_label_classification(
  cube       = probs_bayes_seg_GRASS,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_class_GRASS,
  version    = paste(version_seg_GRASS, "w13-nf05-s20-V1", sep = "-")
)

# ---- Felzenszwalb ----

output_dir_class_FELZENSZWALB <- "data/classification/V3_SEG/FELZENSZWALB"
if (!dir.exists(output_dir_class_FELZENSZWALB)) dir.create(output_dir_class_FELZENSZWALB, recursive = TRUE)

DB_FULL_seg_FELZENSZWALB <- reg_cube_metrics_FELZENSZWALB

samples_seg_FELZENSZWALB <- sits_get_data(
  cube       = DB_FULL_seg_FELZENSZWALB,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_seg_FELZENSZWALB <- "all_samples_FELZENSZWALB-ST2A-FELZENSZWALB-16d-rfor-2024-V3"

set.seed(SEED)
model_seg_FELZENSZWALB <- sits_train(
  samples_seg_FELZENSZWALB,
  ml_method = sits_rfor(num_trees = 200)
)

probs_cube_seg_FELZENSZWALB <- sits_classify(
  data       = DB_FULL_seg_FELZENSZWALB,
  ml_model   = model_seg_FELZENSZWALB,
  output_dir = output_dir_class_FELZENSZWALB,
  version    = version_seg_FELZENSZWALB,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

probs_bayes_seg_FELZENSZWALB <- sits_smooth(
  cube           = probs_cube_seg_FELZENSZWALB,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_class_FELZENSZWALB,
  version        = paste(version_seg_FELZENSZWALB, "w13-nf05-s20-V1", sep = "-")
)

class_cube_seg_FELZENSZWALB <- sits_label_classification(
  cube       = probs_bayes_seg_FELZENSZWALB,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_class_FELZENSZWALB,
  version    = paste(version_seg_FELZENSZWALB, "w13-nf05-s20-V1", sep = "-")
)

# ---- SNIC ----

output_dir_class_SNIC <- "data/classification/V3_SEG/SNIC"
if (!dir.exists(output_dir_class_SNIC)) dir.create(output_dir_class_SNIC, recursive = TRUE)

DB_FULL_seg_SNIC <- reg_cube_metrics_SNIC

samples_seg_SNIC <- sits_get_data(
  cube       = DB_FULL_seg_SNIC,
  samples    = samples_2024_sits,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = TRUE
)

version_seg_SNIC <- "all_samples_SNIC-ST2A-SNIC-16d-rfor-2024-V3"

set.seed(SEED)
model_seg_SNIC <- sits_train(
  samples_seg_SNIC,
  ml_method = sits_rfor(num_trees = 200)
)

probs_cube_seg_SNIC <- sits_classify(
  data       = DB_FULL_seg_SNIC,
  ml_model   = model_seg_SNIC,
  output_dir = output_dir_class_SNIC,
  version    = version_seg_SNIC,
  multicores = N_CORES,
  memsize    = MEM_CLASS,
  progress   = FALSE,
  verbose    = TRUE
)

probs_bayes_seg_SNIC <- sits_smooth(
  cube           = probs_cube_seg_SNIC,
  window_size    = 13,
  neigh_fraction = 0.5,
  smoothness     = 20,
  memsize        = MEM_CLASS,
  multicores     = N_CORES_SMOOTH,
  output_dir     = output_dir_class_SNIC,
  version        = paste(version_seg_SNIC, "w13-nf05-s20-V1", sep = "-")
)

class_cube_seg_SNIC <- sits_label_classification(
  cube       = probs_bayes_seg_SNIC,
  memsize    = MEM_CLASS,
  multicores = N_CORES,
  output_dir = output_dir_class_SNIC,
  version    = paste(version_seg_SNIC, "w13-nf05-s20-V1", sep = "-")
)

results_all <- list(
  GRASS        = list(cube_full = DB_FULL_seg_GRASS,        samples = samples_seg_GRASS,        probs = probs_cube_seg_GRASS,        bayes = probs_bayes_seg_GRASS,        class = class_cube_seg_GRASS),
  FELZENSZWALB = list(cube_full = DB_FULL_seg_FELZENSZWALB, samples = samples_seg_FELZENSZWALB, probs = probs_cube_seg_FELZENSZWALB, bayes = probs_bayes_seg_FELZENSZWALB, class = class_cube_seg_FELZENSZWALB),
  SNIC         = list(cube_full = DB_FULL_seg_SNIC,         samples = samples_seg_SNIC,         probs = probs_cube_seg_SNIC,         bayes = probs_bayes_seg_SNIC,         class = class_cube_seg_SNIC)
)

save(
  samples_seg_GRASS, samples_seg_FELZENSZWALB, samples_seg_SNIC,
  DB_FULL_seg_GRASS, DB_FULL_seg_FELZENSZWALB, DB_FULL_seg_SNIC,
  model_seg_GRASS, model_seg_FELZENSZWALB, model_seg_SNIC,
  probs_cube_seg_GRASS, probs_cube_seg_FELZENSZWALB, probs_cube_seg_SNIC,
  probs_bayes_seg_GRASS, probs_bayes_seg_FELZENSZWALB, probs_bayes_seg_SNIC,
  class_cube_seg_GRASS, class_cube_seg_FELZENSZWALB, class_cube_seg_SNIC,
  results_all,
  file = "data/classification/classification_results.RData"
)
