# Developer guide

Near Real-Time Drought Monitoring System, Department of Geoinformatics, Shivaji University.
This describes the code as it is. Older documents that mention a Go API or a Node gateway describe a plan that was
never built; `backend-node/` is unused.

## 1. Layout

```
config/
  composite.yaml           default composite (cdi-v2026.10): weights, normalisation, class thresholds
  composite_thermal.yaml   opt-in composite with LST + soil moisture (cdi-v2026.11-thermal)
  spi.yaml                 SPI reference settings
scripts/
  realtime_update.py       the scheduled job: ingest, score, rebuild, status, publish
  backfill_thermal.py      Landsat LST + Sentinel-1 VV history from Earth Engine (resumable)
  rescore_panel.py         offline: rebuild the village panel under the thermal formula
  publish_supabase.py      Storage + Postgres publishing (stdlib only)
  build_baseline_drought.py / build_village_timeseries.py / build_village_registry.py
                           derived files for the dashboard
  build_village_indices.py raster batch (needs local rasters): NDVI/VCI/PCI/CDI panel
  latur_chirps_spi.py      raster batch: SPI from CHIRPS (history)
  common/
    village_cdi.py         PCI + CDI fuse, plus scoring of new months against the existing record
    thermal.py             TCI, SMI, VHI (pure pandas)
    gee.py                 Earth Engine auth + fetchers (village polygons)
    classify.py            palette, class thresholds (mirrors frontend/lib/classify.ts)
    manifest.py, paths.py  processing manifests; which panel is active
  tests/                   pytest suite (see RUN.md)
  (legacy, not used by the weekly job: scheduler.py, dashboard_master.py, composite_cdi.py [district level],
   sync_dashboard_data.py, process_*.py, load_sqlite.py, initialize_database.py, export_for_supabase.py,
   chirps_gee.py / pipeline_gee.py [tehsil level], colab_sentinel_pipeline.py)
supabase/
  schema.sql, migrations/0002_*.sql   database + storage + security rules
frontend/
  app/                     pages: / (dashboard), /map, /timeseries, /compare, /animation, /upload (AOI), /sources
  app/api/v1/[...slug]/    API routes (read published files)
  components/              map (LaturMap, MapLegend), panels, aoi, dashboard
  lib/                     metrics.ts (layers, bins, colours), classify.ts, data.ts, dataSource.ts, aoi.ts
output/, data/, outputs/   history tables and processed files (pipeline state and inputs)
```

## 2. Data model

* **Village key:** polygon `id` (1..954) in `latur_villages_latest.geojson`. Names are not unique.
* **Panel** (`output/indices/zonal/village/village_monthly_indices*.csv`): one row per village and month with
  NDVI, EVI, VCI, VHI, Rain_mm, SPI1/3/6/12, PCI, (LST, VV, TCI, SMI), composite score and class.
* **History tables:** `output/spi/extra/csv/village_monthly_rainfall_wide.csv`, `output/spi/csv/SPI*_village_monthly.csv`,
  `output/thermal/village_monthly_lst_sm.csv`.
* **Published artifacts** (Storage bucket `drought-data`, also bundled in `frontend/public/data`):
  `village_timeseries.json` (id -> monthly points), `village_baselines.json`, `villages_by_tehsil.json`,
  `district_monthly.json`, `latest_status.json`, GeoJSON layers.
* **Postgres:** `villages`, `village_monthly` (village_id, period), `pipeline_runs`.

## 3. How a month is scored

1. SPI is recomputed from the village rain table (Thom gamma fit, Stagge zero handling) for all scales; before
   writing, the job recomputes SPI on the stored history and aborts if it disagrees with the stored values.
2. A new month's PCI and CDI are computed against the existing record (`score_new_period`); stored months are not
   rewritten. Scoring an existing month reproduces its stored score exactly (tested).
3. Missing inputs are dropped from the fuse, never replaced. Below `min_inputs`, the month is not scored.

## 4. Rules for changes

* Weights, thresholds and formula version live in YAML. Change classes or weights only deliberately and update the
  documentation in the same commit. The default formula must keep reproducing stored history.
* Palette and thresholds exist in `scripts/common/classify.py`, `frontend/lib/classify.ts`,
  `frontend/lib/metrics.ts` and the YAML files; a test fails if they drift.
* No hard-coded data: no typed-in months, tehsils, project ids, centroids or fallback values. Take them from the
  data or from configuration.
* An input that is not published stays empty. Do not extrapolate or fill.
* Synthetic fixtures only on a scratch copy with `ALLOW_SYNTHETIC_FIXTURE=1`.
* The Supabase service-role key is server-side only.
* Leaflet is loaded with `dynamic(..., { ssr: false })`.
* Add a test for every bug you fix in the pipeline.

## 5. Frontend notes

* All layer definitions (label, bins, colours, definition text, cadence) are in `lib/metrics.ts`; the map, legend,
  tooltips, compare and timelapse pages read from it. Add a layer there, nowhere else.
* Data is loaded through `lib/data.ts` (cached) and `lib/dataSource.ts` (Supabase Storage first, bundled snapshot as
  a flagged fallback). Server routes use `lib/serverData.ts`.
* The AOI tool (`lib/aoi.ts`) runs entirely in the browser.
* SPI-3/6/12 are "long-term" layers (they change only monthly) and are kept off the main dashboard.

## 6. Known open issues

See `docs/DATA_ACCURACY_AUDIT.md`: EVI saturated at source, rainfall sampled at the village centroid on a 5 km
grid, SPI calibrated on ~10 years, thermal/soil-moisture indices not yet validated, live Earth Engine fetch not yet
exercised in CI, pipeline state kept in committed CSVs.
