# Pipeline

One scheduled job (`scripts/realtime_update.py`, weekly) keeps the dashboard current. Every input is a monthly
product, so the dashboard changes when a new month becomes available, not weekly; the weekly schedule only checks.

```
fetch (Earth Engine)         Sentinel-2 NDVI/EVI   CHIRPS rain   [Landsat LST + Sentinel-1 VV]
        |
history tables               rain wide CSV, thermal CSV, village panel
        |
SPI 1/3/6/12                 recomputed for the whole record, self-checked first
VCI, PCI, [TCI, SMI, VHI]    against each village's own envelope for the calendar month
        |
CDI                          weights/thresholds from the active config; missing inputs dropped
        |
rebuild                      village_with_baseline.csv, village_timeseries.json, baselines, registry,
                             district_monthly.json, latest village GeoJSON
        |
status + manifests           latest_status.json (what actually happened), data/processed/manifests/*.json
        |
publish                      Supabase Storage + Postgres, run row in pipeline_runs
```

## Stages and where results land

| Stage | Code | Output |
|---|---|---|
| Sentinel-2 monthly median (SCL-masked), village mean | `realtime_update.fetch_s2` | panel row |
| CHIRPS daily sum per month, village mean (month must be complete) | `realtime_update.fetch_chirps` | `village_monthly_rainfall_wide.csv` |
| Landsat 8/9 LST, Sentinel-1 VV (thermal formula) | `common/gee.fetch_lst_sm` | `output/thermal/village_monthly_lst_sm.csv` |
| SPI | `realtime_update.compute_spi` | `output/spi/csv/SPI*_village_monthly.csv` |
| TCI, SMI, VHI | `common/thermal.add_thermal_indices` | panel columns |
| PCI, CDI | `common/village_cdi.score_new_period` | panel columns |
| Derived dashboard files | `build_*.py` | `frontend/public/data/*` |
| Status | `realtime_update.write_status` | `outputs/Dashboard/latest_status.json`, `frontend/public/data/latest_status.json` |
| Publish | `publish_supabase.py` | bucket `drought-data`, tables |

## Behaviour that matters

* **A month is used only if its sources cover it.** CHIRPS needs every daily image; Landsat/Sentinel-1 need the month to
  be over (plus a lag) and enough observations. Otherwise the month is skipped and stays "no data".
* **Out-of-order arrival is handled.** If Sentinel-2 arrived before CHIRPS (as for 2026-09/10), the month is
  re-scored when the rainfall lands.
* **History is not rewritten.** New months are scored against the existing record; SPI tables are recomputed (all
  months) because adding a year changes each calendar month's gamma fit slightly.
* **Failure is loud.** A failed step, a due month with no data, or a failed publish makes the run exit non-zero and
  the status "degraded". The workflow commits the status anyway, then fails.
* **Two formulas.** Default `cdi-v2026.10` (no thermal inputs) and opt-in `cdi-v2026.11-thermal`. The thermal formula
  also scores months without a Sentinel-2 image from SPI + PCI + SMI.

## History (how the record was produced)

The 2016-2026 record came from raster batches: `latur_chirps_spi.py` (SPI), `build_village_indices.py` (NDVI, EVI,
VCI, PCI, CDI from Sentinel-2 composites and CHIRPS rasters) and `build_baseline_drought.py`. The rasters are not
in the repository. The weekly job extends that record; it does not rebuild it. Known weaknesses of the
record (EVI, rainfall sampling, short calibration window) are listed in `docs/DATA_ACCURACY_AUDIT.md`.

## Rules

1. Never fill a missing input; leave it empty and let the composite drop it.
2. Never report success a run did not earn.
3. Never use synthetic data outside a scratch copy.
4. Edit weights and thresholds in YAML, not in code.
