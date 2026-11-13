# Compares the retrained DB_FULL models with the original model (Region Growing, DB_FULL):
# Gini importance (MeanDecreaseGini), the 200 trees and the OOB error.
# Run from the repository root.

suppressWarnings(suppressMessages(library(sits)))

models_dir <- "models"

rf_orig <- environment(readRDS(file.path(models_dir, "original/rfor_model_DB_FULL_region_growing.rds")))$model

compare <- function(name, file) {
  rf_new <- environment(readRDS(file))$model
  g_o <- randomForest::importance(rf_orig, type = 2)[, "MeanDecreaseGini"]
  g_n <- randomForest::importance(rf_new, type = 2)[, "MeanDecreaseGini"]
  same_vars <- identical(names(g_o), names(g_n))
  max_diff <- if (same_vars) max(abs(g_o - g_n)) else NA
  trees <- all(vapply(seq_len(rf_orig$ntree), function(k)
    identical(randomForest::getTree(rf_new, k), randomForest::getTree(rf_orig, k)), logical(1)))
  cat(sprintf("\n== %s\n   same %d variables: %s | identical Gini: %s (max difference = %s)\n   %d identical trees: %s | OOB original = %.4f | new = %.4f\n",
              name, length(g_o), same_vars, identical(g_o, g_n), format(max_diff), rf_orig$ntree, trees,
              rf_orig$err.rate[rf_orig$ntree, "OOB"], rf_new$err.rate[rf_new$ntree, "OOB"]))
  invisible(list(original = g_o, new = g_n))
}

r1 <- compare("rfor_model_exp_DB_FULL.rds",       file.path(models_dir, "retrained/rfor_model_exp_DB_FULL.rds"))
r2 <- compare("rfor_model_seg_region_growing.rds", file.path(models_dir, "retrained/rfor_model_seg_region_growing.rds"))

# mean Gini importance per band (mean of the 23 dates)
band <- sub("[0-9]+$", "", names(r1$original))
tab <- data.frame(original = tapply(r1$original, band, mean), new_DB_FULL = tapply(r1$new, band, mean))
tab <- tab[order(-tab$original), ]
cat("\nMean Gini per band:\n"); print(round(tab, 4))
