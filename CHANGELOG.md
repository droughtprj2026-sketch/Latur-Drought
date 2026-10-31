# Changelog

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
