# Stratified random sampling of validation points on the concordance map
# (strata: the 12 classes + DISCORD; FLO and NFLO excluded from the universe).

library(terra)
library(sf)
library(dplyr)

RASTER_PATH <- "maps/concordance_sampling_strata.tif"
OUTPUT_GPKG <- "results/validation_points_sampled.gpkg"

NODATA_VALS     <- c(0, 255)
EXCLUDE_CLASSES <- c(13, 14)

DISCORD_ID <- 99
UI_DISCORD <- 0.50    # expected user's accuracy of the DISCORD stratum

# expected user's accuracy (Ui) per stratum, used only to size the sample
strata_dict <- data.frame(
  id_raster = c(1,2,3,4,5,6,7,8,9,10,11,12, DISCORD_ID),
  Classe    = c("AGPE","AGUA","AL","DMC","DMF","PA","PH","PSI","SE","URB","VSA","VSI", "DISCORD"),
  Ui        = c(0.80, 0.90, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.90, 0.90, UI_DISCORD)
)

TARGET_SE    <- 0.01   # target standard error of the overall accuracy
RARE_LIMIT   <- 0.05   # Wi < 5%: rare stratum
MIN_RARE     <- 75     # minimum points in rare strata
MIN_DISCORD  <- 150    # minimum points in DISCORD
SURPLUS_PCT  <- 0.50   # surplus over the minimum, kept for the manual review

BUFFER_PX          <- 5   # border erosion (pixels) in all strata but DISCORD
BUFFER_PX_DISCORD  <- 0   # DISCORD lies on class borders, so it is not eroded

SEED <- 42

set.seed(SEED)

dir.create(dirname(OUTPUT_GPKG), recursive = TRUE, showWarnings = FALSE)

r <- rast(RASTER_PATH)
r[r %in% NODATA_VALS] <- NA
r[r %in% EXCLUDE_CLASSES] <- NA

# Wi recomputed over the remaining strata (= 100%)
freq_df <- as.data.frame(freq(r))
freq_df <- freq_df[!is.na(freq_df$value), ]

total_px <- sum(freq_df$count)

df_wi <- freq_df %>%
  rename(id_raster = value, n_pixels = count) %>%
  left_join(strata_dict, by = "id_raster") %>%
  filter(!is.na(Classe)) %>%
  mutate(Wi = n_pixels / total_px)

print(df_wi %>% select(Classe, n_pixels, Wi, Ui))

if (!(DISCORD_ID %in% df_wi$id_raster)) {
  warning("No DISCORD pixel found: RASTER_PATH may point to a classification raster ",
          "instead of the concordance raster.")
}

# total sample size (Cochran Eq. 5.25 / Olofsson Eq. 13)
df_wi <- df_wi %>% mutate(Si = sqrt(Ui * (1 - Ui)))
sum_WiSi <- sum(df_wi$Wi * df_wi$Si)
n_total <- ceiling((sum_WiSi / TARGET_SE)^2)

cat(sprintf("\nn_total (Eq. 13, target SE = %.3f): %d\n", TARGET_SE, n_total))

df_wi <- df_wi %>%
  mutate(type = case_when(
    id_raster == DISCORD_ID ~ "discord",
    Wi < RARE_LIMIT         ~ "rare",
    TRUE                    ~ "common"
  ))

n_fixed_total <- MIN_RARE * sum(df_wi$type == "rare") +
  MIN_DISCORD * sum(df_wi$type == "discord")
n_remaining    <- max(n_total - n_fixed_total, 0)
sum_Wi_common  <- sum(df_wi$Wi[df_wi$type == "common"])

df_wi <- df_wi %>%
  mutate(
    n_min = case_when(
      type == "discord" ~ MIN_DISCORD,
      type == "rare"    ~ MIN_RARE,
      TRUE              ~ round(n_remaining * Wi / sum_Wi_common)
    ),
    n_min = pmax(n_min, MIN_RARE),
    n_max = ceiling(n_min * (1 + SURPLUS_PCT))
  )

print(df_wi %>% select(Classe, Wi, Ui, type, n_min, n_max))
cat(sprintf("\nSum n_min: %d | Sum n_max: %d\n", sum(df_wi$n_min), sum(df_wi$n_max)))

# a pixel is eligible only if its whole (2 * buffer_px + 1)^2 neighborhood is of the same stratum
erode_mask <- function(r, class_id, buffer_px) {
  m <- as.numeric(r == class_id)
  if (buffer_px == 0) {
    m[m == 0] <- NA
    return(m)
  }
  window <- matrix(1, nrow = 2 * buffer_px + 1, ncol = 2 * buffer_px + 1)
  eroded <- focal(m, w = window, fun = min, na.rm = FALSE)
  eroded[eroded == 0] <- NA
  eroded
}

sample_class_points <- function(r, class_id, n, class_name, buffer_px) {
  m <- erode_mask(r, class_id, buffer_px)
  valid_cells <- which(!is.na(values(m, mat = FALSE)))

  cat(sprintf("  %s: %d cells after %d px erosion\n", class_name, length(valid_cells), buffer_px))

  if (length(valid_cells) < n) {
    warning(sprintf("%s: only %d cells available, %d requested.", class_name, length(valid_cells), n))
    n <- length(valid_cells)
  }

  cells <- sample(valid_cells, size = n, replace = FALSE)
  xy <- xyFromCell(m, cells)
  pts <- st_as_sf(as.data.frame(xy), coords = c("x", "y"), crs = crs(r))
  pts$Classe <- class_name
  pts
}

points_list <- lapply(seq_len(nrow(df_wi)), function(i) {
  buffer_i <- if (df_wi$id_raster[i] == DISCORD_ID) BUFFER_PX_DISCORD else BUFFER_PX
  sample_class_points(r, df_wi$id_raster[i], df_wi$n_max[i], df_wi$Classe[i], buffer_i)
})

final_points <- do.call(rbind, points_list)

cat(sprintf("\nTotal points: %d\n", nrow(final_points)))

st_write(final_points, OUTPUT_GPKG, delete_dsn = TRUE)
