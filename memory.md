# Repository Memory & Knowledge Base: Near Real-Time Drought Monitoring System, Latur (Dept. of Geoinformatics, Shivaji University)

> Current architecture and commands: `README.md`, `DEVELOPER.md`, `RUN.md`. Verified data issues: `docs/DATA_ACCURACY_AUDIT.md`. The paths below are the original Windows workstation layout and are kept for provenance only.

> **MANDATORY INSTRUCTION FOR AI AGENTS**:
> Always reference this `memory.md` file before planning, modifying, or executing tasks in this repository.
> **STRICT CONSTRAINT**: NEVER read raw `.tif` or `.tiff` raster files directly into context. To inspect raster metadata, dimensions, bounding boxes, or band statistics, use Python scripts with `rasterio` or GDAL.

---

## 1. Project Overview & Objectives

* **Project Scope**: Drought Assessment, Meteorological & Agricultural Monitoring for **Latur District, Marathwada, Maharashtra, India**.
* **Analysis Period**: **January 2016 to 2026**.
* **Study Area**: Latur District (~7,000–7,157 km² across 10 tehsils / 954 villages).
* **Core Datasets**:
  1. **Optical Satellite Imagery**: Copernicus Sentinel-2 MSI monthly composites (10 m resolution) with 6 spectral bands: Blue (B2), Green (B3), Red (B4), NIR (B8), SWIR1 (B11), SWIR2 (B12).
  2. **Precipitation Data**: CHIRPS Daily & Monthly rainfall grids (~5.5 km resolution) calibrated with weather stations.
  3. **Vector Boundaries**: Official SOI / ORGI MDDS harmonized district, tehsil, and village boundaries with Local Government Directory (LGD) codes.
* **Target Drought Indices Workflow**:
  $$\text{Precipitation (CHIRPS)} \implies \text{SPI} + \text{PCI}$$
  $$\text{Optical Imagery (Sentinel-2)} \implies \text{NDVI} + \text{EVI} \implies \text{VCI}$$
  $$\text{VHI} = 0.5 \times \text{VCI} + 0.5 \times \text{TCI} \quad (\text{Kogan; TCI from Landsat 8/9 LST})$$
  Composite drought index (CDI): weights are **not** fixed here. They live in `config/composite.yaml`
  (`cdi-v2026.10`: SPI .30, VHI .20, VCI .15, NDVI .15, EVI .10, PCI .10) and `config/composite_thermal.yaml`
  (`cdi-v2026.11-thermal`: SPI .25, PCI .10, SMI .20, VHI .30, NDVI .15). Always read the YAML.

---

## 2. Directory & Path Structure (All Local)

| Logical Name | Absolute Path | Description |
|---|---|---|
| **Workspace Root** | `D:\Droughtprj@2026\` | Project root containing scripts, shapefiles, documentation |
| **Output Directory** | `D:\Droughtprj@2026\output\` | Root output folder for all processed rasters, charts, tables |
| **Sentinel Imagery** | `D:\Droughtprj@2026\output\sentinel\` | Sentinel-2 GeoTIFFs organized by year (`2016` to `2026`) |
| **CHIRPS Rainfall** | `D:\Droughtprj@2026\output\chirps\` | CHIRPS monthly rainfall rasters organized by year |
| **Precipitation Archive** | `D:\Droughtprj@2026\output\Latur_Precip\` | Unpacked Colab directory structure of CHIRPS rasters (2021–2025) |
| **Comprehensive SPI Output** | `D:\Droughtprj@2026\output\spi\SPI_output (1)\` | Full production SPI deliverables (rasters, charts, zonal, tables) |
| **CDI & Indices Deliverables**| `D:\Droughtprj@2026\output\indices\` | Root folder for complete CDI, VCI, VHI, NDVI, EVI pipeline |
| **Tehsil Indices & CDI** | `D:\Droughtprj@2026\output\indices\zonal\tehsil\` | Master Excel, monthly CSV, yearly CDI summary, annual GeoJSONs |
| **Village Indices & CDI** | `D:\Droughtprj@2026\output\indices\zonal\village\` | Master Excel, monthly CSV, yearly CDI summary for all 954 villages |
| **CDI Charts & Visuals** | `D:\Droughtprj@2026\output\indices\charts\` | Time series, severity area %, and Tehsil CDI heatmaps |
| **Generated Index Rasters** | `D:\Droughtprj@2026\output\indices\rasters\` | Optional 10 m GeoTIFFs for NDVI, EVI, VCI, CDI |

---

## 3. Remote Sensing Images & Locations

### A. Sentinel-2 Multispectral Composites
* **Location**: `D:\Droughtprj@2026\output\sentinel\<YEAR>\`
* **File Naming Pattern**: `S2_Latur_YYYY_MM.tif` or `Latur_S2_YYYY_MM.tif`
* **Coordinate Reference System (CRS)**: `EPSG:32643` (WGS 84 / UTM Zone 43N)
* **Spatial Resolution**: 10 meters (SWIR bands B11 and B12 resampled from 20 m to 10 m)
* **Pixel Data Type**: Signed 16-bit (`int16`) or Unsigned 16-bit (`uint16`), Cloud Optimized GeoTIFF (COG)
* **Spectral Band Mapping**:
  - Band 1: **Blue** (`B2`, ~490 nm) — Used in EVI atmospheric resistance
  - Band 2: **Green** (`B3`, ~560 nm)
  - Band 3: **Red** (`B4`, ~665 nm) — Used in NDVI and EVI
  - Band 4: **NIR** (`B8`, ~842 nm) — Used in NDVI, EVI, NDMI
  - Band 5: **SWIR1** (`B11`, ~1610 nm) — Canopy water content
  - Band 6: **SWIR2** (`B12`, ~2190 nm) — Soil moisture / mineral absorption

### B. CHIRPS Precipitation Rasters
* **Location**: `D:\Droughtprj@2026\output\chirps\<YEAR>\`
* **CRS**: `EPSG:4326` (Geographic WGS 84), Resolution: ~5,566 meters (~0.05°)
* **Units**: Accumulated monthly rainfall in millimeters (mm/month)

---

## 4. Complete Drought Indices Specifications

### 1. NDVI (Normalized Difference Vegetation Index)
$$\text{NDVI} = \frac{\text{NIR} - \text{Red}}{\text{NIR} + \text{Red}} = \frac{\text{B8} - \text{B4}}{\text{B8} + \text{B4}}$$
* **Range**: $[-1.0, 1.0]$. Values $> 0.3$ indicate healthy vegetative cover; values $< 0.15$ indicate barren soil or severe vegetation stress.

### 2. EVI (Enhanced Vegetation Index)
$$\text{EVI} = 2.5 \times \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + 6.0 \times \rho_{\text{Red}} - 7.5 \times \rho_{\text{Blue}} + 1.0}$$
* Where $\rho = \text{DN} / 10000.0$ (reflectance).
* Optimized for high biomass areas, decoupled from canopy background and atmospheric haze.

### 3. SPI (Standardized Precipitation Index)
* Calculated from CHIRPS precipitation using Thom (1958) MLE Gamma distribution per pixel/zone.
* Primary timescales: **SPI-1, SPI-3, SPI-6, SPI-12**.
* **SPI-3** represents agricultural drought and is normalized to a 0–100 scale:
  $$\text{SPI}_{\text{scaled}} = \text{clip}\left(\frac{\text{SPI-3} - (-2.0)}{2.0 - (-2.0)} \times 100,\; 0,\; 100\right)$$

### 4. VCI (Vegetation Condition Index)
$$\text{VCI} = 100 \times \frac{\text{NDVI} - \text{NDVI}_{\min}}{\text{NDVI}_{\max} - \text{NDVI}_{\min}}$$
* Calculated against the multi-year minimum and maximum NDVI for that specific calendar month.
* **Kogan (1995) Classes**: $<10$ Extreme Drought, $10-20$ Severe, $20-30$ Moderate, $30-40$ Mild, $\ge 40$ Normal.

### 5. PCI (Precipitation Condition Index)
$$\text{PCI} = 100 \times \frac{\text{Rain} - \text{Rain}_{\min}}{\text{Rain}_{\max} - \text{Rain}_{\min}}$$
* Evaluates the relative precipitation deficit compared to the multi-year range for that calendar month.

### 6. VHI (Vegetation Health Index)
$$\text{VHI} = 0.5 \times \text{VCI} + 0.5 \times \text{PCI}$$
* Synthesizes vegetative vitality with moisture availability.

### 7. CDI (Combined Drought Index)
Integrates meteorological and agricultural signals into a unified drought metric:
$$\text{CDI} = 0.35 \times \text{SPI}_{\text{scaled}} + 0.35 \times \text{VCI} + 0.30 \times \text{PCI}$$

#### CDI Drought Severity Classification
| CDI Score | Severity Level | Alert Level | Primary Agrarian Impact |
|---|---|---|---|
| **$\ge 50$** | **No Drought / Normal** | None | Normal crop growth and moisture conditions |
| **$40 \le \text{CDI} < 50$** | **Watch** | Yellow | Mild meteorological deficit; early warning |
| **$30 \le \text{CDI} < 40$** | **Warning** | Orange | Moderate drought; vegetation stress apparent |
| **$20 \le \text{CDI} < 30$** | **Alert** | Red | Severe drought; significant agricultural losses |
| **$< 20$** | **Emergency** | Dark Red | Extreme drought; critical crop failure / water shortage |

---

## 5. Vector Boundaries & Shapefile Catalog

### A. District & Tehsil Boundary Shapefile
* **Path**: `D:\Droughtprj@2026\Latur.shp`
* **CRS**: Lambert Conformal Conic (`LCC_WGS84`), Units: Meters
* **10 Tehsils**: Ahmadpur, Ausa, Chakur, Deoni, Jalkot, Latur, Nilanga, Renapur, Shirur Anantpal, Udgir.

### B. Village Boundary Shapefile
* **Archive**: `D:\Droughtprj@2026\Latur_Tehsil_Villages.zip` (`Latur_Tehsil_Villages.shp`)
* **CRS**: Geographic WGS 84 (`EPSG:4326`)
* **Features**: 954 villages across all 10 tehsils with 2001 Census codes.

---

## 6. Scripts Catalog

### 1. `latur_drought_indices_cdi.py`
* **Path**: [latur_drought_indices_cdi.py](file:///d:/Droughtprj@2026/latur_drought_indices_cdi.py)
* **Function**: Comprehensive pipeline calculating **NDVI, EVI, VCI, PCI, VHI, and CDI**.
* **Features**:
  - Automatically indexes all available Sentinel-2 scenes (2016–2026).
  - High-performance zone rasterization cache for 10 tehsils and 954 villages.
  - Merges optical metrics with CHIRPS precipitation & SPI series.
  - Outputs master formatted Excel workbooks, monthly CSVs, yearly summaries, annual GeoJSON layers, and time-series charts.
* **CLI Arguments**:
  - `python latur_drought_indices_cdi.py`: Standard run (zonal stats, Excel, CSVs, GeoJSONs, charts).
  - `python latur_drought_indices_cdi.py --save-rasters`: Also exports 10 m GeoTIFF rasters for NDVI and EVI.

### 2. `latur_s2_chirps_download.py`
* **Path**: [latur_s2_chirps_download.py](file:///d:/Droughtprj@2026/latur_s2_chirps_download.py)
* **Function**: Automated dual-pipeline downloader for Sentinel-2 composites and CHIRPS monthly rainfall.

### 3. `output/latur_chirps_spi.py`
* **Path**: [output/latur_chirps_spi.py](file:///d:/Droughtprj@2026/output/latur_chirps_spi.py)
* **Function**: SPI computation engine for CHIRPS precipitation across 1, 3, 6, and 12-month scales.

---

## 7. Golden Rules for AI Agents Working in this Repository

1. **ALL LOCAL EXECUTION**: All scripts, rasters, tables, and deliverables must reside on the user's local PC (`D:\Droughtprj@2026\`).
2. **NO RAW TIFF VIEWING**: Under no circumstances should `view_file` or direct file-dump tools be called on `.tif` or `.tiff` files. Use Python with `rasterio` or GDAL.
3. **CRS INTEGRITY**:
   - Sentinel-2: `EPSG:32643` (UTM Zone 43N)
   - CHIRPS: `EPSG:4326` (Geographic WGS 84)
   - Shapefiles: `LCC_WGS84` (Tehsils) and `EPSG:4326` (Villages)
