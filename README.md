# Latur Drought Monitoring System

Real-time drought monitoring for Latur District, Marathwada (2016-2026).
Ingests Sentinel-2 and CHIRPS data via Google Earth Engine, computes
drought indices (SPI, NDVI, VCI, PCI, NSMI), fuses them into a
Composite Drought Index (CDI), and serves the results through a
web dashboard with maps and time-series charts.

## Architecture

```
GEE (Sentinel-2 + CHIRPS)
        |
   Python pipeline  -->  data/processed/  -->  outputs/Dashboard/
                                                       |
                                               Go API (:8080)
                                                       |
                                             Next.js dashboard (:3000)
```

## Stack

| Layer       | Technology                                |
| ----------- | ----------------------------------------- |
| Pipeline    | Python 3.11 (earthengine-api, geopandas)  |
| Backend     | Go 1.22 (chi, pgx) + Node.js 20 gateway  |
| Database    | Supabase (Postgres 15 + PostGIS 3.4)      |
| Frontend    | Next.js 14 + Leaflet + Recharts + Tailwind |

## Quick start

```bash
cp .env.example .env     # fill in GEE + Supabase credentials
```

### Run the pipeline

```bash
cd scripts && pip install -r requirements.txt

# One command runs everything (CHIRPS, Sentinel-2, SPI, CDI, dashboard):
python scheduler.py

# Or run steps individually:
python chirps_gee.py --from 2016-01 --to latest
python pipeline_gee.py --from 2026-01 --to 2026-10
python composite_cdi.py
python dashboard_master.py
```

### Start the stack

```bash
docker compose up                            # Go API + Node gateway + Postgres
cd frontend && pnpm install && pnpm dev      # http://localhost:3000
```

## Project structure

```
config/              CDI weights + SPI config (composite.yaml, spi.yaml)
scripts/             Python pipeline (GEE ingest, indices, CDI, dashboard)
data/vector/         AOI boundaries (district, tehsils, 954 villages)
data/processed/      Pipeline outputs (CSV, GeoJSON, JSON)
outputs/Dashboard/   Go backend reads these files directly
backend-go/          Primary REST API (chi + pgx)
backend-node/        Auth gateway (Express)
frontend/            Next.js 14 dashboard (Leaflet + Recharts)
```

## CDI formula (v2026.11)

```
CDI = 0.40*SPI + 0.25*VCI + 0.15*NDVI + 0.10*PCI + 0.10*NSMI
```

Weights and thresholds are in `config/composite.yaml`. Change the YAML
and re-run `python scripts/composite_cdi.py` — no code changes needed.

## Documentation

- **DEVELOPER.md** — full architecture, API reference, pipeline details, deployment
- **AGENTS.md** — rules for coding agents working on this repo

## Data sources

- Sentinel-2 L2A (Copernicus/ESA) via Google Earth Engine
- CHIRPS monthly precipitation (UCSB Climate Hazards Group)
- Village boundaries (Revenue Department, Government of Maharashtra)
