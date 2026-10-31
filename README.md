# Near Real-Time Drought Monitoring System: Latur District, Marathwada

Developed by the **Department of Geoinformatics, Shivaji University**.

**Project team (developers):** Rajnandini U. Kadam, Aishwarya B. Jagtap, Pavan S. Devkar, Shital B. Gurav,
Trupti U. Jadhav.
**Project guide:** Dr. Sachin S. Panhalkar, Head of Department, Department of Geography.

Village-level drought monitoring for the 954 revenue villages of Latur district (10 tehsils), 2016 to present.
Python ingests satellite data from Google Earth Engine, computes drought indices and a transparent composite
index (CDI), and publishes the results to Supabase. A Next.js dashboard reads them and shows maps, history,
baselines and an area-of-interest tool.

## Data and indices

| Quantity | Source | Resolution |
|---|---|---|
| NDVI, VCI | Copernicus Sentinel-2 L2A (monthly composite) | 10 m |
| Rainfall, SPI, PCI | UCSB CHIRPS (daily, summed per month) | ~5 km |
| LST, TCI | Landsat 8 + 9 Collection 2 L2 surface temperature (clear-sky) | 30 m |
| Soil moisture (relative), SMI | Sentinel-1 VV backscatter | 10 m |
| VHI | 0.5 VCI + 0.5 TCI (Kogan) | derived |
| CDI | weighted composite, `config/composite*.yaml` | derived |

Sentinel-2 has no thermal band, which is why LST comes from Landsat. CHIRPS is the rainfall reference.
Two composite formulas exist: `config/composite.yaml` (`cdi-v2026.10`, default, no thermal inputs) and
`config/composite_thermal.yaml` (`cdi-v2026.11-thermal`, opt-in). See
[docs/THERMAL_AND_SOIL_MOISTURE.md](docs/THERMAL_AND_SOIL_MOISTURE.md).

## Architecture

```
Earth Engine (S2, S1, Landsat, CHIRPS)
        |  scripts/realtime_update.py   (weekly GitHub Action, incremental)
        v
history tables (CSV) --> SPI, VCI/TCI/SMI, CDI --> JSON/GeoJSON artifacts
        |  scripts/publish_supabase.py
        v
Supabase: Storage bucket `drought-data` (public) + Postgres `village_monthly`, `pipeline_runs`
        |
        v
Next.js dashboard (API routes + Leaflet + Recharts) on Vercel
```

Every village is keyed by its polygon `id`. Village names are not unique (three pairs collide).

## Quick start

```bash
# dashboard against the bundled data snapshot (no credentials needed)
cd frontend && npm install && npm run dev          # http://localhost:3000

# tests for the Python pipeline
pip install -r scripts/requirements-realtime.txt pytest
python -m pytest scripts/tests -q
```

To read from Supabase instead of the snapshot, copy `.env.example` to `frontend/.env.local` and set the
`NEXT_PUBLIC_SUPABASE_*` variables. Running the pipeline and deploying: [RUN.md](RUN.md),
[DEPLOYMENT.md](DEPLOYMENT.md).

## Documentation

| File | Contents |
|---|---|
| [RUN.md](RUN.md) | commands for the pipeline, backfill, rescoring, publishing |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Supabase, Earth Engine, GitHub Actions, Vercel setup |
| [DEVELOPER.md](DEVELOPER.md) | code layout, data model, how to change things |
| [PIPELINE.md](PIPELINE.md) | what each pipeline stage does and where results land |
| [docs/THERMAL_AND_SOIL_MOISTURE.md](docs/THERMAL_AND_SOIL_MOISTURE.md) | LST, soil moisture, TCI, VHI method |
| [docs/DATA_ACCURACY_AUDIT.md](docs/DATA_ACCURACY_AUDIT.md) | verified findings, known data defects, open issues |
| [baseline_drought_architecture.md](baseline_drought_architecture.md) | baseline / anomaly definitions |
| [AGENTS.md](AGENTS.md) | rules for coding agents |
| [CHANGELOG.md](CHANGELOG.md) | what changed |

## Status and limits

Read [docs/DATA_ACCURACY_AUDIT.md](docs/DATA_ACCURACY_AUDIT.md) before using results. In short: the SPI/CDI
arithmetic is reproducible, but EVI is saturated at source, rainfall is sampled on a ~5 km grid, SPI is
calibrated on about 10 years, the thermal and soil-moisture indices have not yet been validated against ground
data, and the live Earth Engine fetch has not been run in this repository's CI.
