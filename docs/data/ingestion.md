# Satellite Ingestion Pipeline & Data Harmonization

This document details the raw Earth Engine ingest mechanisms, cloud-masking algorithms, naming conventions, and data harmonization reality.

---

## 1. Raw Ingestion Reality & Naming Conventions

The ingestion engine in `scripts/historical/` and `scripts/realtime/` is designed to ingest multi-source satellite rasters exported from Google Earth Engine (GEE). Because historical batches were extracted across multiple Colab and GEE batch jobs, the scanner tolerates coexisting naming styles:

### 1.1 Coexisting Sentinel-2 Filename Conventions
```
S2_Latur_YYYY_MM.tif        <-- Primary naming style (most common)
S2_L2A_Latur_YYYY_MM.tif    <-- 2024 Level-2A batch
Latur_S2_YYYY_MM.tif        <-- 2017, 2021, 2024, 2026 batches
```

### 1.2 Coexisting CHIRPS Filename Conventions
```
CHIRPS_Latur_YYYY_MM_mm.tif <-- Precipitation grid with millimeter sum in filename
Latur_precip_YYYY_MM.tif    <-- Monthly cumulative precipitation raster
```

### 1.3 Strict File Exclusion Patterns
The scanner automatically filters out sidecar, temp, and metadata files:
- `*.aux.xml`: GDAL raster georeferencing sidecars
- `*.ovr`: Overview pyramid rasters
- `*.crdownload`: Incomplete browser or drive downloads
- `*.py`: Stray scripts in raw folders (e.g., `Latur_S2_2021_Mar_Oct.py`)
- `*.zip`: Google Drive export archives
- `*.csv`: Ingest logs (e.g., `cloud_threshold_log.csv`)
- `._*`: macOS HFS+ hidden metadata files

### 1.4 Duplicate Month Resolution
Certain months exist under two filenames (e.g. 2021-11, 2021-12, all of 2022, and most of 2024). The scanner retains exactly **one** copy per `(year, month)` pair using the `PREFERRED_PREFIX` hierarchy and logs duplicate occurrences for auditing.

---

## 2. Cloud Masking & Quality Filtering

### 2.1 Scene Classification Layer (SCL)
For Sentinel-2 Level-2A (Bottom-of-Atmosphere), Sen2Cor generates an automated 12-class scene classification mask. Pixels falling into the following classes are strictly masked out before village zonal aggregation:
- `Class 3`: Cloud shadows
- `Class 8`: Cloud medium probability
- `Class 9`: Cloud high probability
- `Class 10`: Thin cirrus clouds
- `Class 11`: Snow / ice

### 2.2 Strict Zero-Value Rule for Mapping
A critical lesson learned in empirical cartography: **dates with zero or missing observations must NEVER be rendered as blank white maps.**
- The function `is_valid_date_for_mapping()` evaluates each period.
- If all values are zero or $\ge 90\%$ of village values are zero, the date is marked `No Data / Cloud Masked`.
- The village borders and administrative boundaries remain visible with a distinct grey fill (`#CBD5E1`), preserving cartographic integrity.

### 2.3 Handling Missing Years (2019 & 2025 Optical Gaps)
In the raw Sentinel archive, 2019 and 2025 do not have optical rasters in the historical storage folder.
- The pipeline maintains these periods as `NaN`.
- The composite engine dynamically drops the optical component (NDVI/VCI) and classifies these months using CHIRPS rainfall (SPI-3) and SAR soil moisture (NSMI).
- Neither synthetic data nor zero-fill is ever injected into committed records.
