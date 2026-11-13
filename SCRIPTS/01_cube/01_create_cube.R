# Sentinel-2 16-day data cube (BDC) for 2024, with spectral mixture fractions.

library(sits)
library(sf)
library(tibble)

roi <- st_read("roi/study_area.shp")
output_dir <- "data/cube/2024_BDC"
dir.create(output_dir, recursive = TRUE)

bands <- c("NDVI", "EVI", "NBR", "B02", "B03", "B04", "B05", "B06", "B07",
           "B08", "B8A", "B11", "B12", "CLOUD")

s2_cube <- sits_cube(
  source     = "BDC",
  collection = "SENTINEL-2-16D",
  bands      = bands,
  roi        = roi,
  start_date = as.Date("2024-01-01"),
  end_date   = as.Date("2024-12-31"),
  multicore  = 8L
)

options(timeout = 10000)

reg_cube <- sits_cube_copy(
  cube       = s2_cube,
  output_dir = output_dir,
  roi        = roi,
  n_tries    = 10L,
  multicore  = 8L
)

# Endmember reflectances (x 10000); "water" is the shade endmember
endmembers <- tribble(
  ~type,    ~B02, ~B03, ~B04, ~B05, ~B06, ~B07, ~B08, ~B8A, ~B11, ~B12,
  "forest",  164,  480,  194,  808, 2582, 3149, 3536, 3466, 1497,  598,
  "soil",    839, 1116, 1278, 1614, 2142, 2361, 2474, 2754, 3198, 2315,
  "water",   110,  193,  119,  108,   26,   35,   10,   10,   26,   24
)

s2_cube_local <- sits_mixture_model(
  data       = reg_cube,
  endmembers = endmembers,
  multicores = 20,
  memsize    = 150,
  output_dir = output_dir
)

s2_cube_local <- sits_select(
  s2_cube_local,
  bands = c("B02", "B03", "B04", "B05", "B06", "B07", "B08", "B11", "B12", "B8A",
            "NDVI", "NBR", "EVI", "FOREST", "SOIL", "WATER")
)

saveRDS(s2_cube_local, file.path(output_dir, "s2_cube_local.rds"))
