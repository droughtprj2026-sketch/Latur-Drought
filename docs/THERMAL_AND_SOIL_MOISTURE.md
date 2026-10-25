# Land-surface temperature, soil moisture, TCI and VHI

Near Real-Time Drought Monitoring System, Department of Geoinformatics, Shivaji University.

## Why

The first version had no thermal band: VHI was set equal to VCI, so one vegetation signal carried 35 % of the
composite and nothing measured heat stress or soil water. Kogan's VHI needs both halves:

    VHI = 0.5 * VCI + 0.5 * TCI          TCI = 100 * (LSTmax - LST) / (LSTmax - LSTmin)

and agricultural drought is better described by soil moisture than by rainfall alone.

## Inputs (Earth Engine, village polygon mean, monthly)

Sentinel-2 has no thermal band, so land-surface temperature cannot be derived from it. The closest sources that
keep the analysis at field scale are:

| Index | Source | Resolution | Notes |
|---|---|---|---|
| LST | Landsat 8 + 9 Collection 2 Level 2, `ST_B10` (DN x 0.00341802 + 149.0 K -> deg C) | 30 m (100 m thermal) | daytime ~10:30, clear pixels only (QA_PIXEL), monthly mean of the clear observations |
| Soil moisture (relative) | Sentinel-1 IW GRD, VV backscatter | 10 m | incidence-angle normalised to 40 deg, averaged in linear power, back to dB |
| Rainfall | CHIRPS (daily, summed per month) | ~5 km | the rainfall reference for SPI and PCI |

A month is used only when it is over (plus `publish_lag_days`) and has enough observations (Landsat >= 1 clear
image over the district, Sentinel-1 >= 2). A village that is cloud-covered in every Landsat image of the month
gets no LST: empty, not filled. A partial month is skipped, never extrapolated.

**What SMI is.** Radar backscatter rises with soil wetness, so SMI is the village's own min-max position of VV for
that calendar month (the change-detection principle), 0 = driest, 100 = wettest it has been in that month. It is
a *relative* index, not volumetric soil moisture, and backscatter is also affected by crop cover and surface
roughness. Comparing the same calendar month across years removes most of the seasonal crop signal but not all.
Before relying on single months, check SMI against an independent soil-moisture product or field data (SMAP L4
`NASA/SMAP/SPL4SMGP/007` is a convenient independent reference; it is not used as an input).

**What TCI is.** Landsat revisits every 8 days (L8 + L9) and only clear-sky days count, so a month's LST is the
mean of a few clear days: fewer in the monsoon, and biased toward clear (warmer) days. TCI/VHI therefore have
gaps from June to September, and the envelope has the same sampling bias, which largely cancels in the index.

TCI, SMI and VCI each compare a month with the village's own 5th-95th percentile envelope for that calendar
month. An index is issued only after 5 years of that calendar month exist; before that it is empty and the
composite drops the input (nothing is filled).

## The composite (config/composite_thermal.yaml, formula `cdi-v2026.11-thermal`)

    SPI 0.25 | PCI 0.10 | SMI 0.20 | VHI 0.30 | NDVI 0.15

VCI and TCI are not weighted separately (they are the two halves of VHI; weighting them again would count the
same pixels three times). EVI is excluded because the stored series is saturated. Thresholds are the same as
`config/composite.yaml`. Months with no Sentinel-2 composite are now scored from SPI + PCI + SMI (Sentinel-1 sees through cloud), which closes
most of the June-September gap.

This formula is selected with `COMPOSITE_CONFIG=config/composite_thermal.yaml`. The default
(`config/composite.yaml`, `cdi-v2026.10`) is unchanged, because switching rewrites every published class.
`config/composite_thermal.yaml` weights are a proposal for the project team to review and calibrate against
reference drought declarations.

## Switching on, in order

1. Backfill 2016 to the last complete month (resumable, one Earth Engine call set per month):

       python scripts/backfill_thermal.py

2. Rebuild the panel offline (no Earth Engine):

       COMPOSITE_CONFIG=config/composite_thermal.yaml python scripts/rescore_panel.py
       COMPOSITE_CONFIG=config/composite_thermal.yaml python scripts/realtime_update.py --skip-self-check --period <latest>

   `rescore_panel.py` writes `village_monthly_indices_thermal.csv` next to the original panel; the original is
   left as it was. If the thermal config is selected before this file exists the pipeline stops with an error
   instead of publishing old numbers under the new label.

3. Review the maps (layers: TCI, SMI, LST, VHI, CDI), then set the repository variable
   `COMPOSITE_CONFIG=config/composite_thermal.yaml` so the scheduled job keeps using it.

From then on every monthly run also fetches LST and soil moisture for the new month, appends them to
`output/thermal/village_monthly_lst_sm.csv`, and scores the month.

## No invented data

* The pipeline never uses fixtures unless `ALLOW_SYNTHETIC_FIXTURE=1` is set (tests on a scratch copy only); a run
  with that flag marks `latest_status.json` as `synthetic_input` and the site shows "Synthetic test data".
* No Earth Engine project, centroid, district name, tehsil area, month list, tehsil list or event is typed into
  the code: they come from environment/repository variables or from the data itself.
* If an input is not published for a month, that month's value stays empty and the legend counts it as "no data".
* The dashboard shows when the pipeline last ran and turns red after 10 days (the job is weekly).

## Earth Engine access for the scheduled job

The Cloud project is owned by a different Google account than the GitHub repository, so the job authenticates
with a service account of that project, not with a person's login:

1. In the Cloud project (console.cloud.google.com, project id from `GEE_PROJECT`): IAM > Service Accounts >
   create `drought-pipeline`; grant "Service Usage Consumer" and "Earth Engine Resource Viewer".
2. Register the service account for Earth Engine: https://code.earthengine.google.com/register (use the
   project, then add the account under "Service accounts").
3. Keys > Add key > JSON. **Do not paste the key into chat or commit it** (`*service_account*.json` and
   `igneous-*.json` are git-ignored). Copy its text into the GitHub secret `GEE_SERVICE_ACCOUNT_KEY`.
4. Set the repository variable `GEE_PROJECT` to the project id.
5. Run the "Near-real-time drought update" workflow once with `period` empty and read the log.

## Supabase

Run `supabase/migrations/0002_polygon_ids_storage_publishing.sql` once (SQL editor, or the "Supabase migrations"
workflow with the `DATABASE_URL` secret). Add the secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, then
`python scripts/publish_supabase.py --full` loads the whole history. After that every pipeline run publishes the
data files to the public `drought-data` bucket and the monthly rows to `public.village_monthly`; the site reads
the bucket and shows "Bundled snapshot" if it ever has to fall back to the copy shipped in the repository.
