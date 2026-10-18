# Pipeline Documentation

## Pipeline Overview

The Latur Drought Monitoring pipeline processes Sentinel-2 and CHIRPS satellite data to compute drought indices and generate dashboard outputs.

## Pipeline Stages

### Stage 1: CHIRPS Rainfall → SPI (`latur_chirps_spi.py`)

**Input**: CHIRPS monthly precipitation GeoTIFFs  
**Output**: SPI-1/3/6/12 per pixel rasters + district monthly CSV

**Process**:
1. Scan CHIRPS rasters (supports `CHIRPS_Latur_YYYY_MM_mm.tif` and `Latur_precip_YYYY_MM.tif`)
2. Deduplicate by `(year, month)` using `PREFERRED_PREFIX`
3. Resample all rasters to common grid
4. Compute rolling k-month accumulations (k = 1, 3, 6, 12)
5. Fit gamma distribution per pixel per calendar month (Thom MLE)
6. Apply zero-rainfall correction (Stagge et al. 2015: H(0) = q/2)
7. Compute SPI via inverse normal of gamma CDF
8. Write GeoTIFFs, GeoJSON, CSV, Excel outputs

**Reference**: McKee et al. 1993, Thom 1958

### Stage 2: Sentinel-2 → Vegetation Indices (`build_village_indices.py`)

**Input**: Sentinel-2 L2A monthly composites  
**Output**: NDVI/EVI/VCI/VHI rasters + village zonal statistics

**Process**:
1. Scan Sentinel-2 rasters (supports `S2_Latur_YYYY_MM.tif`, `S2_L2A_Latur_YYYY_MM.tif`, `Latur_S2_YYYY_MM.tif`)
2. Deduplicate by `(year, month)` using `PREFERRED_PREFIX`
3. Read bands by description (supports short codes and full words)
4. Auto-detect GEE scale factor (0..10000 vs 0..1)
5. Compute NDVI, EVI per pixel
6. Compute per-batch radiometric offset (relative to largest batch)
7. Compute per-pixel VCI using 5th-95th percentile envelope per calendar month
8. VHI = VCI (no thermal band available)
9. Write per-pixel rasters + village zonal statistics

**Stage 1a**: NDVI/EVI rasters  
**Stage 1b**: VCI/VHI rasters  
**Stage 2**: Village zonal statistics + CDI fusion

### Stage 3: Composite CDI (`composite_cdi.py`)

**Input**: Village indices CSV  
**Output**: CDI score + class per village-period

**Process**:
1. Read village indices CSV
2. Normalize each component to 0..1 drought intensity
3. Fuse with weights from `config/composite.yaml`
4. Exclude missing inputs from numerator AND denominator
5. If fewer than `min_inputs` (3) available → mark `pending`
6. Classify CDI using thresholds from `config/composite.yaml`
7. Write district CSV + per-period GeoJSON + components JSON

### Stage 4: Dashboard Master (`dashboard_master.py`)

**Input**: All processed outputs  
**Output**: `data/dashboard/` + `frontend/public/data/`

**Process**:
1. Read SPI district CSV, sentinel CSV, CDI CSV
2. Build master CSV with all indices per tehsil-period
3. Compute drought area/percentage per tehsil-period
4. Write `drought_monitoring_master.csv`, `latest_status.json`, `data_availability.json`, `processing_manifest.json`
5. Write `village_latest.geojson` + `village_latest.json`
6. Mirror to `frontend/public/data/`
7. Call `build_baseline_drought.py` for SQLite + baseline

### Stage 5: Baseline + Anomaly (`build_baseline_drought.py`)

**Input**: Village indices CSV  
**Output**: SQLite `drought.db` + baselines

**Process**:
1. Fix EVI/NDVI/VCI/VHI out-of-range values
2. Compute per-village per-calendar-month baseline (mean/std)
3. Compute anomaly z-scores
4. Flag drought months (CDI ≥ 0.35 or composite anomaly < -1.0)
5. Write `village_with_baseline.csv`
6. Write village GeoJSON with centroids
7. Load into SQLite (`drought.db`)

## Data Directory Structure

```
data/
├── dashboard/              ← Central dashboard data (API reads from here)
│   ├── drought_monitoring_master.csv
│   ├── latest_status.json
│   ├── data_availability.json
│   ├── processing_manifest.json
│   ├── village_latest.geojson
│   ├── village_latest.json
│   └── json/
│       ├── district_monthly.json
│       ├── manifest.json
│       └── composite_components.json
├── processed/              ← Intermediate processing outputs
│   ├── csv/
│   │   ├── village_Latur_monthly_indices.csv
│   │   ├── village_with_baseline.csv
│   │   ├── district_monthly.csv
│   │   └── ...
│   ├── geojson/
│   │   ├── cdi/            ← Per-period CDI GeoJSON
│   │   └── village_latest.geojson
│   └── manifests/
│       ├── sentinel.json
│       └── chirps.json
└── drought.db              ← SQLite database
```

## Key Configuration Files

### `config/composite.yaml`

```yaml
formula_version: "cdi-v2026.10"
min_inputs: 3                       # Minimum components required
weights:
  SPI:  0.30
  VHI:  0.20
  VCI:  0.15
  NDVI: 0.15
  EVI:  0.10
  PCI:  0.10
normalisation:
  SPI:  { method: neg_clip }
  NDVI: { method: robust_z }
  EVI:  { method: robust_z }
  PCI:  { method: robust_z }
  VCI:  { method: robust_z }
  VHI:  { method: robust_z }
spi_accumulation: "SPI-3"
thresholds:
  - { max: 0.20, code: "None", label: "No drought / Normal" }
  - { max: 0.35, code: "D0",   label: "Abnormally dry / Mild" }
  - { max: 0.50, code: "D1",   label: "Moderate drought" }
  - { max: 0.65, code: "D2",   label: "Severe drought" }
  - { max: 0.80, code: "D3",   label: "Extreme drought" }
  - { max: 1.01, code: "D4",   label: "Exceptional drought" }
```

### `config/spi.yaml`

```yaml
reference_period:
  start: "1991-01"
  end:   "2020-20"
distribution:
  method: "gamma"
  zero_correction: "stagge"
  min_nonzero: 3
accumulations: [1, 3, 6, 12]
```

## GitHub Actions

### `realtime_drought_sync.yml`

Runs weekly on Mondays at 02:00 UTC:
1. Checkout repository
2. Setup Python 3.11
3. Install dependencies (earthengine-api, supabase, pandas, numpy, geopandas, shapely, requests)
4. Run `scripts/run_realtime_pipeline_sync.py`
5. Commit & push updated data to GitHub

Required secrets:
- `GEE_PROJECT`, `GEE_SERVICE_ACCOUNT_KEY`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

### `ci.yml`

Runs on push to main/operational:
1. Checkout repository
2. Setup Node.js 20 → Build backend-node
3. Setup Node.js 20 → Build frontend
4. Setup Python 3.11 → Compileall scripts/

### `deploy.yml`

Deploys frontend to Vercel on push to main/operational.

## Validation & Empirical Accuracy

The pipeline includes two dedicated validation suites:

1. **`scripts/verify_realtime_pipeline.py`**:
   - Tests Sentinel-2 SCL cloud masking logic.
   - Tests multi-spectral band mathematics (NDVI, EVI, CDI weights 0.50, 0.25, 0.25).
   - Validates 954 village timeseries continuity.

2. **`scripts/validate_historical_analysis.py`**:
   - Benchmarks 94,570 cadastral records against statutory disaster records (2016 Jaldoot, 2018 GR No. SCQ-2018/CR-334/M-3, 2020 recovery, 2023 August break, 2026 deficit).
   - Audits all 10 tehsils and 954 cadastral villages.
   - Computes Pearson bivariate correlation matrix ($p < 0.001$).
   - Verifies 19/19 cloud-obscured months comply with Anti-Fabrication Rule §2.4.
   - Outputs comprehensive audit report to `docs/HISTORICAL_VALIDATION_RUN_OUTPUT.json`.

## Data Quality Rules

1. **Missing data = NaN, never zero**: Missing inputs are never substituted with zeros
2. **Min inputs rule**: If fewer than `min_inputs` (3) components available → mark `pending`
3. **Atomic writes**: Manifests written via `.tmp` → `replace`
4. **Incremental processing**: Only process missing/affected periods
5. **Duplicate handling**: Keep one copy per `(year, month)` using `PREFERRED_PREFIX`
6. **Filename tolerance**: Multiple naming conventions supported (S2_Latur_, S2_L2A_Latur_, Latur_S2_)

## Project Owner

rajnandinikadam221@gmail.com
