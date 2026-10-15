# Repository Memory & Knowledge Base: Drought Project Latur (2016–2026)

> **MANDATORY INSTRUCTION FOR AI AGENTS**:
> Always reference this `memory.md` file before planning, modifying, or executing tasks in this repository.
> **STRICT CONSTRAINT**: NEVER read raw `.tif` or `.tiff` raster files directly into context. To inspect raster metadata, dimensions, bounding boxes, or band statistics, use Python scripts with `rasterio` or GDAL.

---

## 1. Project Overview & Objectives

* **Project Scope**: Drought Assessment, Meteorological & Agricultural Monitoring for **Latur District, Marathwada, Maharashtra, India**.
* **Analysis Period**: **January 2016 to 2026**.
* **Study Area**: Latur District (~7,000–7,157 km² across 10 tehsils / 954 villages).
* **Core Datasets**:
  1. **Optical Satellite Imagery**: Copernicus Sentinel-2 MSI (Multi-Spectral Instrument) monthly composites (10 m resolution) with 6 spectral bands: Blue, Green, Red, NIR, SWIR1, SWIR2.
  2. **Precipitation Data**: CHIRPS Daily & Monthly rainfall grids (~5.5 km resolution) calibrated with weather stations.
  3. **Vector Boundaries**: Official SOI / ORGI MDDS harmonized district, tehsil, and village boundaries with Local Government Directory (LGD) codes.
* **Key Analytical Goals**:
  - Calculate Standardized Precipitation Index (**SPI-1, SPI-3, SPI-6, SPI-12**).
  - Calculate zonal statistics at **District, Tehsil (10 zones), and Village (954 zones)** administrative scales.
  - Calculate spectral drought and vegetation condition indices (**NDVI, NDWI, NDMI, NMDI, VCI**).
  - Evaluate drought frequency, spatial severity, and agrarian vulnerability across Marathwada.

---

## 2. Directory & Path Structure

### Absolute Folder Reference

| Logical Name | Absolute Path | Description |
|---|---|---|
| **Workspace Root** | `D:\Droughtprj@2026\` | Project root containing main scripts, shapefiles, documentation |
| **Output Directory** | `D:\Droughtprj@2026\output\` | Root output folder for all processed rasters, charts, tables |
| **Sentinel Imagery** | `D:\Droughtprj@2026\output\sentinel\` | Sentinel-2 GeoTIFFs organized by year (`2016` to `2026`) |
| **CHIRPS Rainfall** | `D:\Droughtprj@2026\output\chirps\` | CHIRPS monthly rainfall rasters organized by year |
| **Precipitation Archive** | `D:\Droughtprj@2026\output\Latur_Precip\` | Unpacked Colab directory structure of CHIRPS rasters (2021–2025) |
| **Charts & Visuals** | `D:\Droughtprj@2026\output\charts\` | Time-series charts, drought area percentage plots, bar graphs |
| **Comprehensive SPI Output** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\` | Full production SPI deliverables (rasters, charts, zonal, tables) |
| **SPI Pixel Rasters** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\rasters\` | Monthly GeoTIFFs for SPI1, SPI3, SPI6, SPI12 (494 files total) |
| **SPI Pixel Tables & CSV** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\csv\` | Pixel-level CSVs per year and district monthly/yearly summaries |
| **SPI Pixel GeoJSONs** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\geojson\` | Spatial polygon meshes per year (`SPI_Latur_2016.geojson` ... `2026`) |
| **SPI Heatmaps & Maps** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\heatmaps\` & `maps\` | 12-month panel maps and Year × Month matrix heatmaps |
| **Tehsil Zonal Statistics** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\zonal\tehsil\` | Zonal Excel, CSV, GeoJSON, maps, and heatmaps for 10 tehsils |
| **Village Zonal Statistics**| `D:\Droughtprj@2026\output\spi\SPI_output (1)\zonal\village\` | Zonal Excel, CSV, GeoJSON, maps for 954 individual villages |

---

## 3. Remote Sensing Images & Locations

### A. Sentinel-2 Multispectral Composites

* **Location**: `D:\Droughtprj@2026\output\sentinel\<YEAR>\`
* **File Naming Pattern**: `S2_Latur_YYYY_MM.tif` or `Latur_S2_YYYY_MM.tif`
* **Coordinate Reference System (CRS)**: `EPSG:32643` (WGS 84 / UTM Zone 43N)
* **Spatial Resolution**: 10 meters (SWIR bands B11 and B12 resampled from 20 m to 10 m)
* **Pixel Data Type**: Signed 16-bit (`int16`) or Unsigned 16-bit (`uint16`), Cloud Optimized GeoTIFF (COG)
* **NoData Value**: `-9999` (or `0` in direct Colab tile downloads)
* **Spectral Bands**:
  | Band Name | Sentinel-2 Band ID | Central Wavelength | Spatial Resolution | Target Utility |
  |---|---|---|---|---|
  | **Blue** | `B2` | ~490 nm | 10 m | Aerosols, atmospheric correction, water |
  | **Green** | `B3` | ~560 nm | 10 m | Vegetation health, water bodies |
  | **Red** | `B4` | ~665 nm | 10 m | Chlorophyll absorption (used in NDVI) |
  | **NIR** | `B8` | ~842 nm | 10 m | Leaf cell structure, biomass (NDVI, NDWI) |
  | **SWIR1** | `B11` | ~1610 nm | 20 m $\to$ 10 m | Canopy moisture, soil wetness (NDWI, NDMI) |
  | **SWIR2** | `B12` | ~2190 nm | 20 m $\to$ 10 m | Soil mineral absorption, drought severity (NMDI) |
* **Cloud Masking**:
  - Primary: Google Cloud Score+ Harmonized (`cs_cdf >= 0.60`).
  - Secondary: Scene Classification Layer (SCL) where classes 1, 3, 8, 9, 10, 11 are excluded.
  - Composition: 4 weekly medians merged into 1 monthly composite to remove transient clouds.

### B. CHIRPS Precipitation Rasters

* **Location**: `D:\Droughtprj@2026\output\chirps\<YEAR>\`
* **File Naming Patterns**:
  - `CHIRPS_Latur_YYYY_MM_mm.tif` (Standard downloader output)
  - `Latur_precip_YYYY_MM.tif` (Secondary / archive convention)
* **Coordinate Reference System (CRS)**: `EPSG:4326` (Geographic WGS 84)
* **Spatial Resolution**: ~0.05° (~5,566 meters)
* **Units**: Accumulated monthly rainfall in millimeters (mm/month)
* **NoData Value**: `-9999.0`
* **Data Completeness Validation**: Requires all days of the month published in `UCSB-CHG/CHIRPS/DAILY` before summing.

---

## 4. Drought Indices & Calculated Products

### A. Meteorological Drought: SPI (Standardized Precipitation Index)

Implemented in [latur_chirps_spi.py](file:///d:/Droughtprj@2026/output/latur_chirps_spi.py) based on McKee et al. (1993) & Thom (1958) MLE gamma fitting:

| Scale | Accumulation Window | Primary Agricultural / Hydrological Meaning |
|---|---|---|
| **SPI-1** | 1 month | Short-term soil moisture changes, crop planting shocks |
| **SPI-3** | 3 months | Seasonal crop development; critical for Kharif (Jun–Sep) & Rabi (Oct–Dec) |
| **SPI-6** | 6 months | Medium-term seasonal water availability, streamflow levels |
| **SPI-12**| 12 months | Long-term hydrological drought, groundwater recharge, reservoir storage |

#### McKee Drought Classification Thresholds
* $\ge +2.00$: **Extremely Wet** (`#00441b`)
* $+1.50 \text{ to } +1.99$: **Very Wet** (`#1a9850`)
* $+1.00 \text{ to } +1.49$: **Moderately Wet** (`#a6d96a`)
* $-0.99 \text{ to } +0.99$: **Near Normal** (`#f7f7f7`)
* $-1.00 \text{ to } -1.49$: **Moderately Dry** (`#fdae61`)
* $-1.50 \text{ to } -1.99$: **Severely Dry** (`#d7301f`)
* $\le -2.00$: **Extremely Dry** (`#7f0000`)

#### Generated SPI Artifacts & Locations
1. **District-Level Outputs**:
   - Master Workbook: `output/spi/SPI_output (1)/SPI_Latur_2016_2026_combined.xlsx`
   - Monthly Summary: `output/spi/SPI_output (1)/csv/SPI_Latur_district_monthly.csv`
   - Yearly Summary: `output/spi/SPI_output (1)/csv/SPI_Latur_yearly_summary.csv`
   - Timeseries Chart: [SPI_timeseries_all_scales.png](file:///d:/Droughtprj@2026/output/charts/SPI_timeseries_all_scales.png)
   - Monthly Map Panels: `output/spi/SPI_output (1)/maps/SPI1_maps_<YEAR>.png` & `SPI3_maps_<YEAR>.png`
   - Heatmaps: `output/spi/SPI_output (1)/heatmaps/Heatmap_SPI<1|3|6|12>.png`
2. **Tehsil-Level Zonal Outputs** (`zonal/tehsil/`):
   - Excel: `SPI_Latur_tehsil_zonal_stats.xlsx`
   - CSV: `tehsil_monthly_zonal_stats.csv`, `tehsil_yearly_summary.csv`
   - GeoJSON: `tehsil_SPI_<YEAR>.geojson` (2016–2026)
   - Visuals: Heatmaps (`tehsil_Heatmap_SPI<1|3|6|12>.png`) & annual maps
3. **Village-Level Zonal Outputs** (`zonal/village/`):
   - Excel: `SPI_Latur_village_zonal_stats.xlsx`
   - CSV: `village_monthly_zonal_stats.csv`, `village_yearly_summary.csv` (10,494 records across 954 villages)
   - GeoJSON: `village_SPI_<YEAR>.geojson` (2016–2026)
   - Annual village drought classification maps

### B. Remote Sensing Spectral Indices (from Sentinel-2)

When computing optical drought indices from the 6-band Sentinel-2 GeoTIFFs:
1. **NDVI (Normalized Difference Vegetation Index)**:
   $$\text{NDVI} = \frac{\text{B8} - \text{B4}}{\text{B8} + \text{B4}}$$
2. **NDWI / NDMI (Normalized Difference Moisture Index)**:
   $$\text{NDMI} = \frac{\text{B8} - \text{B11}}{\text{B8} + \text{B11}}$$
3. **NMDI (Normalized Multi-band Drought Index)**:
   $$\text{NMDI} = \frac{\text{B8} - (\text{B11} - \text{B12})}{\text{B8} + (\text{B11} - \text{B12})}$$
4. **VCI (Vegetation Condition Index)**:
   $$\text{VCI} = 100 \times \frac{\text{NDVI} - \text{NDVI}_{\min}}{\text{NDVI}_{\max} - \text{NDVI}_{\min}}$$

---

## 5. Vector Boundaries & Shapefile Catalog

### A. District & Tehsil Boundary Shapefile
* **Files**: `D:\Droughtprj@2026\Latur.*` (`.shp`, `.dbf`, `.prj`, `.shx`, `.sbn`, `.sbx`, `.cpg`, `.shp.xml`)
* **CRS**: Lambert Conformal Conic (`LCC_WGS84`), Units: Meters
* **WGS84 Bounds**: Lon $[76.20349^\circ, 77.34220^\circ]$, Lat $[17.87058^\circ, 18.83917^\circ]$
* **Features**: 10 Tehsils of Latur District
  1. `AHMADPUR` (LGD: 4228, 754.28 km²)
  2. `AUSA` (LGD: 4232, 1,189.26 km²)
  3. `CHAKUR` (LGD: 4230, 667.06 km²)
  4. `DEONI` (LGD: 4234, 381.62 km²)
  5. `JALKOT` (LGD: 4229, 332.68 km²)
  6. `LATUR` (LGD: 4226, 974.14 km²)
  7. `NILANGA` (LGD: 4233, 1,075.27 km²)
  8. `RENAPUR` (LGD: 4227, 553.83 km²)
  9. `SHIRUR ANANTPAL` (LGD: 4231, 310.64 km²)
  10. `UDGIR` (LGD: 4235, 758.34 km² — MultiPolygon with 1 enclave)
* **Total Area**: 6,997.13 km² (LCC projection)

### B. Village Boundary Shapefile
* **Archive**: `D:\Droughtprj@2026\Latur_Tehsil_Villages.zip` (`Latur_Tehsil_Villages.shp`)
* **CRS**: Geographic WGS 84 (`EPSG:4326`)
* **Features**: 954 villages across all 10 tehsils
* **Attributes**: `VILLAGE`, `TEHSIL`, `DISTRICT`, `STATE`, `TYPE`, `CEN_2001` (18-digit Census code), `PARTS`, `AREA_SQKM`.

---

## 6. Detailed Scripts Catalog

### 1. `latur_s2_chirps_download.py`
* **Path**: [latur_s2_chirps_download.py](file:///d:/Droughtprj@2026/latur_s2_chirps_download.py)
* **Primary Function**: Automated dual-pipeline downloader for Sentinel-2 composites and CHIRPS monthly rainfall.
* **GEE Project**: `igneous-effort-511512-c8`
* **Google Drive Folder**: `Latur_Drought`
* **Operational Flow**:
  1. Initializes GEE and authenticates Google Drive REST API.
  2. Reads `Latur.shp` to construct the district Area of Interest (AOI).
  3. Queries Earth Engine tasks to prevent duplicate exports.
  4. Downloads CHIRPS directly to `output/chirps/<YEAR>/`.
  5. Dispatches Sentinel-2 monthly composites (10 m, 6 bands) to Google Drive.
  6. Continuously monitors Drive and automatically downloads completed GeoTIFFs into `output/sentinel/<YEAR>/`.
* **Execution Commands**:
  ```bash
  python latur_s2_chirps_download.py                  # Normal download loop
  python latur_s2_chirps_download.py --sync-drive     # Download all files currently on Drive
  python latur_s2_chirps_download.py --resume 2021 11 # Resume from Nov 2021
  python latur_s2_chirps_download.py --dry-run        # Preview planned tasks without submitting
  ```

### 2. `output/latur_chirps_spi.py`
* **Path**: [latur_chirps_spi.py](file:///d:/Droughtprj@2026/output/latur_chirps_spi.py)
* **Primary Function**: Full-scale multi-timescale SPI calculation and geospatial report generator.
* **Operational Flow**:
  1. Recursively identifies all CHIRPS `.tif` rasters.
  2. Resolves duplicate naming styles (`CHIRPS_` vs `Latur_precip_`), matching timestamps.
  3. Reprojects all rasters onto a single reference grid.
  4. Calculates rolling sums for $k \in [1, 3, 6, 12]$ months.
  5. Fits Gamma distributions per pixel and calendar month with zero-precipitation adjustment ($H(0) = q/2$).
  6. Produces multi-band GeoTIFFs, GeoJSONs, CSV summaries, multi-sheet Excel, and Matplotlib maps/charts.
* **Execution Command**:
  ```bash
  python output/latur_chirps_spi.py
  ```

### 3. `output/sentinel/2021/Latur_S2_2021_Mar_Oct.py`
* **Path**: [Latur_S2_2021_Mar_Oct.py](file:///d:/Droughtprj@2026/output/sentinel/2021/Latur_S2_2021_Mar_Oct.py)
* **Primary Function**: Interactive Google Colab notebook script for downloading Sentinel-2 monthly composites by subdividing into tiles.
* **GEE Project**: `ee-shital`
* **Operational Flow**:
  1. Decomposes the district boundary into $0.15^\circ \times 0.15^\circ$ bounding boxes (~16 km tiles, ~32 MB).
  2. Bypasses the 48 MB Earth Engine direct download limit without requiring Drive exports.
  3. Implements adaptive cloud thresholds starting at 15% and stepping up by +5% (up to 60%) if scenes are sparse.
  4. Multi-threads tile downloads with `ThreadPoolExecutor(4)` and merges them using `rasterio.merge`.
  5. Logs cloud limit statistics to `cloud_threshold_log.csv`.

---

## 7. Golden Rules for AI Agents Working in this Repository

1. **NO RAW TIFF VIEWING**: Under no circumstances should `view_file` or direct file-dump tools be called on `.tif` or `.tiff` files. Use lightweight python scripts (`rasterio`, `gdal`, or `geopandas`) to query metadata, resolutions, or pixel statistics.
2. **CRS INTEGRITY**:
   - Sentinel-2 is in **`EPSG:32643` (UTM Zone 43N)**.
   - CHIRPS is in **`EPSG:4326` (Geographic WGS 84)**.
   - `Latur.shp` is in **`LCC_WGS84` (Lambert Conformal Conic)**.
   - Always reproject before computing cross-dataset zonal statistics.
3. **PARTIAL DOWNLOADS**: Look out for temporary `.crdownload` files in `output/sentinel/<YEAR>/`. Do not parse these as valid GeoTIFFs until the download is finalized.
4. **CHIRPS DUPLICATE NAMING**: If both `CHIRPS_Latur_YYYY_MM_mm.tif` and `Latur_precip_YYYY_MM.tif` exist for a month, follow the `PREFERRED_PREFIX = 'CHIRPS_'` rule defined in `latur_chirps_spi.py`.
5. **CLOUD SCARCITY IN MONSOON**: June to September often contain significant cloud cover. Check `cloud_threshold_log.csv` before assuming a month is missing or failed.
