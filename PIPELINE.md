# Drought Monitoring Pipeline — Documentation

**Project:** Real-Time Drought Monitoring — Latur District, Marathwada, Maharashtra  
**Study period:** 2016 – 2026  
**Owner:** rajnandinikadam221@gmail.com

This document explains **how the pipeline works**, what each script does, how indices are calculated, how baseline + drought-month identification works, and how the frontend dashboard consumes the data.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────┐
│  SOURCE DATA (2016–2026)                    │
│  • Sentinel-2 L2A rasters  (GEE / Drive)    │
│  • CHIRPS monthly precipitation GeoTIFFs    │
│  • Image availability Excel                 │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│  PROCESSING LAYER (Python)                  │
│  latur_chirps_spi.py      → SPI-1/3/6/12    │
│  latur_sentinel_indices.py → NDVI/EVI/VCI/VHI│
│  build_baseline_drought.py → Baseline + drought flag│
│  Output: CSV + GeoJSON + SQLite              │
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│  STORAGE (SQLite + Dashboard files)         │
│  data/drought.db        → master_row, monthly_index, tehsils│
│  outputs/Dashboard/     → village_latest.geojson, status JSON│
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│  BACKEND (Node.js gateway :4000)            │
│  /api/v1/master, /latest, /timeseries, /indices│
└──────────────┬──────────────────────────────┘
               ▼
┌─────────────────────────────────────────────┐
│  FRONTEND (Next.js :3000)                   │
│  Leaflet map + Recharts charts              │
└─────────────────────────────────────────────┘
```

---

## 2. Repository Structure (relevant parts)

```
Droughtprj@2026/
├── scripts/                          # Python processing
│   ├── latur_chirps_spi.py           # CHIRPS → SPI-1/3/6/12
│   ├── latur_sentinel_indices.py     # Sentinel-2 → NDVI/EVI/VCI/VHI
│   ├── composite_cdi.py              # Weighted CDI composite
│   ├── build_village_indices.py      # Village-level zonal indices (batch)
│   ├── build_baseline_drought.py     # Baseline + drought month identification
│   ├── load_sqlite.py                # Load processed data into SQLite
│   ├── dashboard_master.py           # Dashboard master CSV + status JSONs
│   ├── scheduler.py                  # Orchestrates incremental updates
│   └── common/
│       ├── raster.py                 # File scanning, dedupe, read_stack
│       └── classify.py               # SPI/CDI class thresholds
├── config/
│   ├── composite.yaml                # CDI weights, thresholds, formula version
│   └── spi.yaml                      # SPI reference climatology
├── data/
│   ├── raw/                          # NEVER COMMIT — large rasters
│   ├── processed/
│   │   ├── csv/
│   │   │   └── village_Latur_monthly_indices.csv   (village-level indices)
│   │   ├── csv/
│   │   │   └── village_with_baseline.csv           (baseline + drought flags)
│   │   ├── geojson/
│   │   │   └── village_latest.geojson              (latest period village points)
│   │   └── json/
│   │       ├── manifest.json
│   │       └── composite_components.json
│   └── drought.db                    # SQLite — what the frontend reads
├── output/
│   ├── sentinel_Raw_Composites/{YYYY}/   # Sentinel-2 rasters (114 files)
│   ├── CHIRPS_Rainfall/{YYYY}/            # CHIRPS rainfall rasters
│   └── indices/rasters/{NDVI,EVI,VCI,VHI}/ # Pre-computed index rasters
├── outputs/
│   └── Dashboard/
│       ├── village_latest.geojson      # Frontend map data (centroid points)
│       ├── village_latest.json         # Latest period village data
│       ├── latest_status.json          # Status chip (operational/degraded)
│       ├── data_availability.json      # Per-source periods
│       └── processing_manifest.json
├── frontend/
│   ├── public/data/latur_villages.geojson  # Village polygons (954 villages)
│   └── lib/api.ts                      # Frontend API client
├── backend-node/                     # Node.js gateway (:4000)
│   └── src/routes/api.ts             # /api/v1/* handlers (SQLite-backed)
├── backend-go/                       # Go API (:8080, Postgres-backed)
├── README.md                         # Project overview
├── RUN.md                            # End-to-end run guide
├── DEVELOPER.md                      # Full architecture reference
├── AGENTS.md                         # Agent rules of the road
└── DEPLOYMENT.md                     # Deployment notes
```

---

## 3. The Data Pipeline (step by step)

### Step 1: CHIRPS → SPI (rainfall drought)

**Script:** `scripts/latur_chirps_spi.py`  
**Input:** CHIRPS monthly rainfall rasters (`output/CHIRPS_Rainfall/{YYYY}/`)  
**Output:** SPI-1, SPI-3, SPI-6, SPI-12 per village per month  
**Stored in:** `data/processed/csv/village_Latur_monthly_indices.csv` + SQLite `master_row.spi_1..spi_12`

SPI uses the McKee (1993) gamma distribution fit per calendar month. Negative values = drier than normal.

### Step 2: Sentinel-2 → Vegetation indices

**Script:** `scripts/latur_sentinel_indices.py`  
**Input:** Sentinel-2 L2A rasters (`output/sentinel_Raw_Composites/{YYYY}/`)  
**Output:** NDVI, EVI, VCI, VHI per village per month  
**Stored in:** `data/processed/csv/village_Latur_monthly_indices.csv` + SQLite

**Band handling (auto-detected from GeoTIFF band descriptions):**

| Band code | Meaning | Required for |
|-----------|---------|--------------|
| B2 / BLUE | Blue (490 nm) | EVI |
| B3 / GREEN | Green (560 nm) | optional |
| B4 / RED | Red (665 nm) | NDVI, EVI (strictly required) |
| B8 / NIR | Near-infrared (842 nm) | NDVI, EVI (strictly required) |
| B11 / SWIR1 | Short-wave IR 1 (1610 nm) | NDMI, VHI |
| B12 / SWIR2 | Short-wave IR 2 (2190 nm) | VHI |

**Two naming conventions on disk** are both supported:
- 6-band files: `B2, B3, B4, B8, B11, B12` (most files)
- 4-band files (`S2_L2A_*` from 2024): `B2, B4, B8, valid_weeks` (NDVI + EVI only; no SWIR → NDMI/VHI = NaN)

### Step 3: Baseline + Drought Month Identification (NEW)

**Script:** `scripts/build_baseline_drought.py`  
**Input:** `data/processed/csv/village_Latur_monthly_indices.csv`  
**Output:** `village_with_baseline.csv` + `village_latest.geojson` + SQLite load

For **each village × calendar month**, the pipeline:

1. **Computes baseline** = historical mean across all years for that calendar month  
   (e.g., October baseline = mean of all Octobers 2016–2026)

2. **Computes anomaly** = z-score: `(current − baseline) / std`  
   Negative anomaly = drier/greener-than-normal? Lower NDVI/VCI/SPI = drier

3. **Flags drought month** when:
   - CDI ≥ D0 (≥ 0.35 on composite score), OR
   - Composite anomaly < −1.0 (more than 1 standard deviation below baseline)

4. **Stores drought severity** based on anomaly magnitude:
   - `< -2.0` → Exceptional
   - `-2.0 to -1.5` → Extreme
   - `-1.5 to -1.0` → Severe
   - `-1.0 to -0.5` → Moderate
   - `-0.5 to 0.0` → Mild
   - `≥ 0.0` → Normal

### Step 4: Load into SQLite

**Script:** `scripts/load_sqlite.py`  
Loads all village-month data into `data/drought.db` tables:
- `master_row` — one row per village/tehsil per period (all index columns)
- `monthly_index` — district-mean timeseries for charts
- `tehsils` — 10 tehsil centroids (point geometries from village polygons)

---

## 4. Index Calculations

| Index | Formula | Range | Interpretation |
|-------|---------|-------|----------------|
| **NDVI** | `(NIR − RED) / (NIR + RED)` | −1 to 1 | Higher = more vegetation |
| **EVI** | `2.5·(NIR−RED) / (NIR + 6·RED − 7.5·BLUE + 1)` | −1 to 1 | Vegetation, less soil/atmosphere bias |
| **VCI** | `100·(NDVI − NDVI_min) / (NDVI_max − NDVI_min)` | 0 to 100 | Vegetation condition vs historical |
| **VHI** | `VCI` (placeholder; no LST yet) | 0 to 100 | Vegetation health |
| **SPI-k** | Gamma CDF fit per month | −3 to +3 | Rainfall drought (negative = dry) |
| **PCI** | Oliver's Precipitation Concentration Index | 0 to 100 | Rainfall concentration (higher = more uneven) |
| **CDI** | Weighted composite (see config/composite.yaml) | 0 to 1 | Final drought score |

**CDI weights** (from `config/composite.yaml`):
```
SPI:  0.30   VHI: 0.20   VCI: 0.15   NDVI: 0.15   EVI: 0.10   PCI: 0.10
```

**CDI classification** (D-codes):
| CDI score | Code | Label |
|-----------|------|-------|
| < 0.20 | None | No drought / Normal |
| < 0.35 | D0 | Abnormally dry |
| < 0.50 | D1 | Moderate drought |
| < 0.65 | D2 | Severe drought |
| < 0.80 | D3 | Extreme drought |
| ≥ 0.80 | D4 | Exceptional drought |

**Missing data rule:** If fewer than 3 components are available for a village-month, the row is marked `pending` and CDI is left empty. Missing values are **never filled with zero**.

---

## 5. Frontend Data Flow

The frontend (Next.js, `:3000`) talks to the Node.js gateway (`:4000`) at `/api/v1/*`. The gateway reads from **SQLite** (`data/drought.db`).

### Endpoints the frontend uses

| Endpoint | Source | What the frontend shows |
|----------|--------|------------------------|
| `GET /api/v1/master?tehsil=&village=` | SQLite `master_row` | Indicator cards (SPI, NDVI, CDI, etc.) |
| `GET /api/v1/latest?tehsil=&village=` | SQLite `master_row` | Drought status card (latest period) |
| `GET /api/v1/timeseries/:name` | SQLite `monthly_index` | Time-series charts |
| `GET /api/v1/indices/:name/:year/:month` | SQLite `master_row` | Map points (centroid-based) |
| `GET /api/v1/status` | `outputs/Dashboard/latest_status.json` | Status chip (operational/degraded) |
| `GET /api/v1/availability` | `outputs/Dashboard/data_availability.json` | Data coverage |
| `GET /api/v1/manifest` | `data/processed/json/manifest.json` | Available years/indices |

### Map data

The map shows **village centroid points** (not polygons) loaded from `outputs/Dashboard/village_latest.geojson`. Each point carries:
- `CDI` score and `CDI_class` (None/D0–D4)
- `drought_month` (true/false)
- `drought_severity` (Normal/Mild/Severe/Extreme/Exceptional)
- All individual indices (NDVI, EVI, VCI, VHI, PCI, SPI1-12)
- `lon`, `lat` coordinates

---

## 6. Running the Pipeline

### One-time setup

```bash
cd scripts
pip install -r requirements.txt
```

### Full pipeline (run whenever new data arrives)

```bash
# Step 1: SPI from rainfall
python latur_chirps_spi.py

# Step 2: Vegetation indices from Sentinel-2
python latur_sentinel_indices.py

# Step 3: Baseline + drought identification (NEW)
python build_baseline_drought.py

# Step 4: Load into SQLite for frontend
python load_sqlite.py

# Step 5: Dashboard files (optional, for Go API)
python dashboard_master.py
```

### Start the frontend

```bash
cd frontend
pnpm install
pnpm dev          # → http://localhost:3000
```

### Start the backend (optional, for Go API)

```bash
cd backend-node  && pnpm dev     # → :4000 (Node gateway, what frontend uses)
cd backend-go    && go run ./cmd/server   # → :8080 (Go API, Postgres-backed)
```

---

## 7. Current Data State (verified)

| Metric | Value |
|--------|-------|
| Village-month records | 93,492 |
| Periods covered | 2016-01 to 2026-10 (98 periods) |
| Villages | 954 |
| Tehsils | 10 |
| Drought months flagged (all time) | 15,465 (16.5%) |
| EVI range (fixed) | −1.0 to 1.0 |
| Timeseries indices available | CDI, NDVI, EVI, VCI, VHI, PCI, SPI1/3/6/12 |

**2026-10 (latest period) CDI distribution:**
- None: 463 villages
- D0 (Abnormally dry): 138
- D1 (Moderate): 122
- D2 (Severe): 98
- D3 (Extreme): 53
- D4 (Exceptional): 77

---

## 8. Important Rules (do not break)

1. **Never commit `data/raw/` or `.env`** — rasters and secrets.
2. **Never silently change CDI weights or SPI thresholds** — they live in `config/composite.yaml` and `config/spi.yaml`. If you change them, update `DEVELOPER.md`.
3. **Missing inputs → pending, never zero** — if fewer than 3 components available, CDI is empty and class is `pending`.
4. **EVI must be rescaled by 10,000** — raw DN values (0–10,000) must be divided by 10,000 before the EVI formula, or results exceed valid range (> 1.0).
5. **Band mapping is description-based** — do not assume band position; read GeoTIFF band descriptions (`B2`, `B4`, `B8`, etc. or `Blue`, `Red`, `NIR`).
6. **4-band files (2024 S2_L2A_*)** — missing SWIR bands; NDVI/EVI work, NDMI/VHI = NaN.

---

## 9. Known Limitations

- **SPI/PCI for 2026-09 and 2026-10** are empty (no CHIRPS rainfall ingested for those months yet). Villages show `pending` for those components.
- **VHI = VCI placeholder** — no real LST (Land Surface Temperature) data yet. Replace with Landsat/MODIS LST when available.
- **Map uses centroid points** — not full village polygons. Polygon boundaries exist in `frontend/public/data/latur_villages.geojson` but the map currently renders points for performance.
- **Baseline uses all available years** (2016–2026), not a fixed WMO reference period (1981–2010). SPI reference is configurable via `config/spi.yaml`.

---

## 10. Contact

Project owner: **rajnandinikadam221@gmail.com**

See also: `README.md` (overview), `RUN.md` (run guide), `DEVELOPER.md` (full architecture), `AGENTS.md` (agent rules).
