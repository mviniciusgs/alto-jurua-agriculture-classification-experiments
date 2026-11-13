# Extracts the class of each map at the reviewed validation points.
# Segmentation experiment (SEG).

library(sf)
library(terra)
library(dplyr)
library(tools)

points_file <- "samples/validation_points_reviewed.gpkg"
raster_dir  <- "maps/"

raster_pattern <- "^map_(region_growing|felzenszwalb|snic)\\.tif$"
output_file    <- "samples/validation_points_maps_SEG.gpkg"

temp_dir <- file.path(tempdir(), "raster_reproj_temp")
if (!dir.exists(temp_dir)) dir.create(temp_dir, recursive = TRUE)

class_dict <- c(
  "1"  = "AGPE", "2"  = "AGUA", "3"  = "AL",   "4"  = "DMC",  "5"  = "DMF",
  "6"  = "PA",   "7"  = "PH",   "8"  = "PSI",  "9"  = "SE",   "10" = "URB",
  "11" = "VSA",  "12" = "VSI",  "13" = "FLO",  "14" = "NFLO", "0"  = "NoData",
  "255"= "NoData"
)

points <- sf::st_read(points_file, quiet = TRUE)

# "fid" would clash with the GeoPackage feature id
if ("fid" %in% names(points)) {
  points <- points %>% dplyr::rename(fid_original = fid)
}

points_crs <- st_crs(points)
points_vect <- terra::vect(points)

raster_paths <- list.files(path = raster_dir, pattern = raster_pattern, full.names = TRUE)

if (length(raster_paths) == 0) {
  stop("No raster found in ", raster_dir)
}

# rasters go to the CRS of the points ("near" keeps the class codes)
reprojected_paths <- character(length(raster_paths))

for (i in seq_along(raster_paths)) {
  r <- rast(raster_paths[i])
  nm <- basename(raster_paths[i])

  r_crs <- crs(r)
  if (r_crs == "" || is.na(r_crs)) {
    stop(sprintf("Raster '%s' has no CRS.", nm))
  }

  out_temp <- file.path(temp_dir, nm)

  if (st_crs(r_crs) == points_crs) {
    file.copy(raster_paths[i], out_temp, overwrite = TRUE)
  } else {
    r_proj <- project(r, y = crs(points_crs$wkt), method = "near")
    writeRaster(r_proj, out_temp, overwrite = TRUE)
  }

  reprojected_paths[i] <- out_temp
}

rasters <- terra::rast(reprojected_paths)
clean_names <- tools::file_path_sans_ext(basename(reprojected_paths))
names(rasters) <- clean_names

extracted <- terra::extract(rasters, points_vect, ID = FALSE)

na_by_column <- sapply(extracted, function(x) sum(is.na(x)) / length(x) * 100)
cat("% NA per extracted column:\n")
print(round(na_by_column, 2))

final_points <- dplyr::bind_cols(points, extracted) %>%
  dplyr::mutate(
    dplyr::across(
      dplyr::all_of(clean_names),
      ~ class_dict[as.character(.)]
    )
  )

if (!dir.exists(dirname(output_file))) {
  dir.create(dirname(output_file), recursive = TRUE)
}

sf::st_write(final_points, output_file,
             append = FALSE,
             delete_dsn = TRUE,
             quiet = TRUE)

unlink(temp_dir, recursive = TRUE, force = TRUE)

print(head(final_points %>% sf::st_drop_geometry() %>% dplyr::select(dplyr::all_of(clean_names))))
