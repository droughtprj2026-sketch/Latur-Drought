# Running the pipeline

All commands run from the repository root. Python 3.11+.

```bash
pip install -r scripts/requirements-realtime.txt pytest
python -m pytest scripts/tests -q          # must pass before and after any change
```

## Credentials (environment variables, never committed)

| Variable | Use |
|---|---|
| `GEE_PROJECT` | Earth Engine Cloud project id |
| `GEE_SERVICE_ACCOUNT_KEY` | JSON text (or path) of a service-account key registered for Earth Engine |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | publishing (service role is server-side only) |
| `COMPOSITE_CONFIG` | optional, e.g. `config/composite_thermal.yaml` |

Locally, `GEE_PROJECT` plus a prior `earthengine authenticate` is enough.

## Monthly update (what the weekly Action runs)

```bash
python scripts/realtime_update.py                 # every month that is due
python scripts/realtime_update.py --period 2026-09   # force one month
```

Per month it fetches Sentinel-2 and CHIRPS (and Landsat + Sentinel-1 when the thermal formula is active),
recomputes SPI, scores the month, rebuilds the history files, writes `latest_status.json` and publishes to
Supabase when the Supabase variables are set. It exits non-zero if a due month produced nothing.
A month is used only when its sources fully cover it; otherwise it is skipped and shows as "no data".

## Switching on the thermal / soil-moisture formula

```bash
python scripts/backfill_thermal.py                                   # Earth Engine, resumable
COMPOSITE_CONFIG=config/composite_thermal.yaml python scripts/rescore_panel.py   # offline
```

then set `COMPOSITE_CONFIG` for the scheduled job. Details: `docs/THERMAL_AND_SOIL_MOISTURE.md`.

## Publishing to Supabase

```bash
python scripts/publish_supabase.py --full      # first load / repair: all files + all rows
python scripts/publish_supabase.py             # files only
python scripts/publish_supabase.py --period 2026-09 --period 2026-10
```

## Rebuilding derived files offline

```bash
python scripts/build_baseline_drought.py       # village_with_baseline.csv
python scripts/build_village_timeseries.py     # frontend/public/data/village_timeseries.json
python scripts/build_village_registry.py       # villages_by_tehsil.json, village_baselines.json
```

## Frontend

```bash
cd frontend && npm install
npm run dev        # development
npm run build      # production build (also type-checks)
```

## Tests

`scripts/tests/` covers: palette/threshold parity between Python, TypeScript and YAML, one history per polygon,
exact reproduction of stored CDI and SPI, rain-table gap protection, TCI/SMI/VHI maths, the publisher against a
fake Supabase server, the SQL migration's security rules, and the refusal to run synthetic fixtures.

## Testing the plumbing without Earth Engine

`--fixture file.json` feeds invented numbers. It is refused unless `ALLOW_SYNTHETIC_FIXTURE=1` and must only be
used on a scratch copy of the repository: the run rewrites data files and marks the status as synthetic.

## Raw-raster batch scripts (local, need rasters under `output/`)

`scripts/build_village_indices.py` builds the village panel from Sentinel-2 composites and CHIRPS rasters;
`scripts/latur_chirps_spi.py` computes SPI from rasters. These produced the historical record and are not part of
the weekly job.
