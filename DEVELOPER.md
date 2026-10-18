# Developer Documentation

## Architecture Overview

The Latur Drought Intelligence Platform is a full-stack system for real-time drought monitoring. It consists of:

1. **Python Processing Pipeline** (`scripts/`) - Ingests rasters, computes indices, fuses CDI
2. **Node.js API Gateway** (`backend-node/src/api/v1/[...slug]/route.ts`) - Serves processed data
3. **Next.js Frontend** (`frontend/`) - Leaflet maps, Recharts charts, village intelligence panels
4. **Supabase (Postgres + PostGIS)** - Database for production deployments

## Data Pipeline

### Processing Order

```
1. latur_chirps_spi.py       → CHIRPS rainfall → SPI-1/3/6/12 rasters
2. build_village_indices.py  → Sentinel-2 → NDVI/EVI/VCI/VHI rasters + village zonal stats
3. composite_cdi.py          → Weighted fusion → CDI score (0–1) + D-code class
4. dashboard_master.py       → Writes data/dashboard/ + frontend/public/data/
5. build_baseline_drought.py → SQLite drought.db + climatological baselines
```

### Output Directories

| Directory | Contents |
|-----------|----------|
| `data/dashboard/` | Master CSV, status JSON, availability, manifest, village GeoJSON |
| `data/dashboard/json/` | district_monthly.json, manifest.json, composite_components.json |
| `data/processed/` | Intermediate rasters, village indices CSV |
| `data/processed/csv/` | village_Latur_monthly_indices.csv, district_monthly CSVs |
| `data/processed/geojson/` | Per-period CDI GeoJSON files |
| `data/processed/manifests/` | Incremental processing manifests |
| `frontend/public/data/` | Synced copies for direct frontend access |

## CDI Composite Formula

### Weights (from `config/composite.yaml`)

| Index | Weight | Normalization |
|-------|--------|---------------|
| SPI   | 0.30   | neg_clip      |
| VHI   | 0.20   | inv_0_100     |
| VCI   | 0.15   | inv_0_100     |
| NDVI  | 0.15   | robust_z      |
| EVI   | 0.10   | robust_z      |
| PCI   | 0.10   | robust_z      |

### Normalization Methods

| Method | Formula | Applied To |
|--------|---------|------------|
| neg_clip | S = clip(-x/3, 0, 1) | SPI |
| inv_0_100 | S = clip(1 - x/100, 0, 1) | VCI, VHI |
| robust_z | S = clip(-z/3, 0, 1) where z = (x - median)/(1.4826 × MAD) | NDVI, EVI, PCI |

### Classification Thresholds

| Code | Label | Score Range | Color |
|------|-------|-------------|-------|
| None | No drought / Normal | 0.00 – 0.20 | #22c55e |
| D0   | Abnormally dry / Mild | 0.20 – 0.35 | #eab308 |
| D1   | Moderate drought | 0.35 – 0.50 | #f59e0b |
| D2   | Severe drought | 0.50 – 0.65 | #ea580c |
| D3   | Extreme drought | 0.65 – 0.80 | #dc2626 |
| D4   | Exceptional drought | 0.80 – 1.00 | #7f1d1d |

## API Endpoints

All endpoints are served from `frontend/app/api/v1/[...slug]/route.ts`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/status` | GET | Monitoring status + latest period |
| `GET /api/v1/district-timeseries` | GET | District monthly time series (98 periods) |
| `GET /api/v1/timeseries?tehsil=X&village=Y` | GET | Village monthly timeseries (98 periods) |
| `GET /api/v1/tehsil-analytics` | GET | Tehsil rankings + correlation matrix |
| `GET /api/v1/stats?period=YYYY-MM&tehsil=X` | GET | Village-level aggregate stats |
| `GET /api/v1/latest?tehsil=X&village=Y` | GET | Latest village observation |
| `GET /api/v1/master?tehsil=X&village=Y` | GET | Master CSV rows (filtered) |
| `GET /api/v1/indices/{name}/{year}/{month}` | GET | Index GeoJSON for period (CDI, SPI, NDVI, EVI, VCI, VHI, Rain) |
| `GET /api/v1/manifest` | GET | Processing manifest |
| `GET /api/v1/availability` | GET | Data availability |
| `GET /api/v1/animation?index=X&from=Y&to=Z` | GET | Animation frames |
| `GET /api/v1/compare?a=X&b=Y` | GET | Bi-temporal comparison |
| `GET /api/v1/health` | GET | Health check |

### Multi-Index Symbology Scales

| Metric Suite | Scale Classes | Color Ramp |
|--------------|---------------|------------|
| **CDI** (Composite Multi-Index) | None (<0.20), D0 (0.20-0.35), D1 (0.35-0.50), D2 (0.50-0.65), D3 (0.65-0.80), D4 (>=0.80) | Green (#22c55e) to Maroon (#7f1d1d) |
| **SPI** (1, 3, 6, 12 mo) | <= -2.0 (Extr. Dry), <= -1.5 (Sev. Dry), <= -1.0 (Mod. Dry), <= -0.5 (Abnorm. Dry), Normal, Wet, >= 2.0 (Extr. Wet) | Maroon (#7f1d1d) to Deep Blue (#1d4ed8) |
| **NDVI / EVI** (Canopy Greenness) | <0.15 (Bare/Dry Soil), 0.15-0.25 (Stress), 0.25-0.35 (Moderate), 0.35-0.45 (Normal), >0.45 (Lush Canopy) | Brown (#854d0e) to Lush Green (#15803d) |
| **VCI / VHI** (Condition %) | <10 (Extreme Deficit), 10-20 (Severe), 20-35 (Moderate), 35-50 (Mild), >=50 (Normal/Good) | Dark Red (#7f1d1d) to Emerald (#22c55e) |
| **Rainfall / PCI** (Precipitation mm) | <20 mm (Severe Deficit), 20-50 mm (Moderate), >50 mm (Adequate/Heavy) | Amber (#f59e0b) to Ocean Blue (#0284c7) |
| **Missing / Cloud Masked** | No Observation / Missing Satellite Pass | Slate Grey (#94a3b8) |

## Running Locally

### Prerequisites

- Python 3.11+
- Node.js 20+
- pnpm or npm
- PostgreSQL + PostGIS (optional, for production)
- Google Earth Engine credentials (optional, for near-real-time)

### Backend (Python)

```bash
cd E:\Drought\scripts
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python dashboard_master.py
```

### Frontend (Next.js)

```bash
cd E:\Drought\frontend
npm install
npm run dev      # Development server on localhost:3000
npm run build    # Production build
npm run lint     # ESLint check
```

### GitHub Actions

The `realtime_drought_sync.yml` workflow runs weekly on Mondays at 02:00 UTC:
1. Authenticates to GEE (service account)
2. Runs CHIRPS + Sentinel-2 ingestion
3. Runs CDI fusion + dashboard master
4. Syncs to Supabase + GitHub

Required secrets:
- `GEE_PROJECT`, `GEE_SERVICE_ACCOUNT_KEY`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`

## Credits

**Technical Development**: Satwik K Udupi  
**Project Owner**: rajnandinikadam221@gmail.com

