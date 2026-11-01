# Changelog

## November 2026

### Changed
- Formula `cdi-v2026.12`: PCI removed (it was meant to be a Plant Chlorophyll Index but had been built as a
  Precipitation Condition Index that duplicated SPI). Weights SPI 0.50, VCI 0.25, NDVI 0.15, NSMI 0.10 (PCI's 0.10 went to
  SPI); `min_inputs` 3 -> 1. Whole record re-scored with `scripts/analysis/rescore_history.py --rebuild`.
- Monsoon: a month with CHIRPS rain but no Sentinel-2 is now scored from rainfall (SPI) instead of being left "no data"
  (18,100 village-months, mostly June-September), and is re-scored when Sentinel-2 arrives. 82 village-months with no
  rainfall at all stay empty.
- Scripts reorganised into `scripts/realtime/`, `scripts/historical/`, `scripts/analysis/`; `scripts/common/` unchanged.
- Freshness check: a month that ended less than `FRESHNESS_GRACE_DAYS` (10) ago no longer turns the weekly job red; the
  status chip follows CHIRPS and reports what the newest CDI rests on (`composite.basis`).
- Supabase `village_monthly` gets `nsmi` (run `supabase/migrations/0003_village_monthly_nsmi.sql` once); `pci` is no longer sent.

### Fixed
- 61,076 village-months with CDI < 0.20 lost their class ("None" was parsed as missing by `pd.read_csv`) and showed as
  "no data". Every reader now uses `keep_default_na=False`.
- Village drawer showed a hard-coded formula (PCI 50 %, VCI 25 %, TCI 25 %); it now reads the weights from the status file.
- `dashboard_master.py` copied district values into tehsil rows with a static area table and invented percentages; it now
  aggregates the village panel. `latest_status.json` is written only by the weekly job.

### Removed
- `scheduler.py`, `pipeline_gee.py`, `run_realtime_pipeline_sync.py`, `verify_realtime_pipeline.py`,
  `sync_dashboard_data.py` (wrote a fabricated "operational" status) and the stale top-level `historical/` and `realtime/`
  folders (old formula, unused orchestrator).

## October 2026

### Fixed
- 954 villages, not 951: histories, baselines and selectors are keyed by polygon id (three same-name pairs collided).
- Legends match the map: one metric table (`frontend/lib/metrics.ts`) drives colours, legend, tooltip, compare and
  timelapse; sidebar no longer uses different class thresholds; compare/timelapse no longer classify every index as SPI.
- Real-time pipeline: AOI path, Earth Engine auth, non-existent CHIRPS monthly collection, swallowed failures, fake
  "operational" status, hard-coded Supabase row, missing dependencies, deploy workflow condition.
- `/api/v1/realtime` and `/realtime/validate` return real values instead of constants.
- Upload page posted to a route that did not exist; the AOI is now analysed in the browser.
- Overlapping controls, legend and timeline; outline polygons swallowing mouse events; cursors.

### Added
- `scripts/realtime_update.py`, `backfill_thermal.py`, `rescore_panel.py`, `publish_supabase.py`.
- Landsat 8/9 LST and Sentinel-1 VV soil-moisture index; TCI, SMI, VHI = 0.5 VCI + 0.5 TCI; opt-in formula
  `cdi-v2026.11-thermal`.
- Supabase migration 0002 (polygon ids, `village_monthly`, `pipeline_runs`, public `drought-data` bucket, RLS).
- Baseline layers (normal NDVI/rain, NDVI z-score, rain % of normal), client-side AOI analysis, pipeline-age warning.
- pytest suite and CI step; `docs/DATA_ACCURACY_AUDIT.md`, `docs/THERMAL_AND_SOIL_MOISTURE.md`.

### Changed
- "Not in drought" is a neutral stone colour (no green). SPI-3/6/12 moved off the main dashboard into a labelled
  long-term group. Project title and department in header, footer and docs.
- No typed-in data: months, tehsils, presets, baseline table, project id, centroid and fallbacks come from the data or
  configuration. Synthetic fixtures need `ALLOW_SYNTHETIC_FIXTURE=1`.
- Documentation rewritten to match the build (README, RUN, DEPLOYMENT, DEVELOPER, PIPELINE, AGENTS); older reports
  carry an "unverified" banner.

### Known open issues
See `docs/DATA_ACCURACY_AUDIT.md` (EVI saturated at source, rainfall sampling, short SPI calibration, thermal/SMI not
yet validated, live Earth Engine fetch not yet exercised, pipeline state in committed CSVs).
