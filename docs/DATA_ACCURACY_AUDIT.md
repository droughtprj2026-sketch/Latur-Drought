# Data accuracy audit and pipeline repair (October 2026)

What was checked, what was wrong, what was changed, and what is still open.
Every number below was measured on the files in this repository.

## 1. Village count: 954 vs 951

The polygons are 954. The dashboard served 951 histories because
`village_timeseries.json`, `village_baselines.json` and `villages_by_tehsil.json` were keyed by
`tehsil::village-name`, and three pairs of villages share a name inside one tehsil:

| Tehsil | Name | Polygon ids |
|---|---|---|
| Ahmadpur | Anandwadi | 4, 5 |
| Chakur | Hatkarwadi | 293, 294 |
| Nilanga | Kamshetwadi | 642, 643 |

One polygon of each pair was drawn with its namesake's numbers. Fixed by keying everything on the
polygon `id`: `scripts/build_village_timeseries.py`, `scripts/build_village_registry.py`, the map,
sidebar, drawer, timeseries page and `/api/v1/timeseries?id=`. The dropdown selects by id, so two
"Anandwadi" entries are two selectable villages. `scripts/tests/test_pipeline.py` fails if the
count ever drifts again.

## 2. Legends that did not match the map

* The map painted CDI with the US-DM palette (`None` = white), while the legend swatches were green /
  yellow / amber. SPI polygons used cut-offs (-0.5, -1.0, -1.5, -2.0) that disagree with
  `classify.py` (-0.5, -0.8, -1.3, -1.6, -2.0).
* NDVI, VCI, VHI and rainfall layers showed the CDI legend ("None, D0 ... D4").
* The compare and timelapse pages classified every index with the SPI function, so an NDVI of 0.3
  was coloured as "no drought".
* The sidebar re-derived the drought class from 0.2 / 0.4 / 0.6 / 0.8 instead of
  0.20 / 0.35 / 0.50 / 0.65 / 0.80, so the sidebar and the map could disagree on the same village.

Now `frontend/lib/metrics.ts` is the only place a layer's bins, colours and labels are defined; the
fill colour, legend, tooltip, compare/timelapse pages and sidebar all read it. The legend also
shows how many villages fall in each bin for the month on screen and says so when a layer has no
data. Tests compare the TypeScript palette and thresholds against `classify.py` and
`config/composite.yaml`. The "no drought" colour changed from white to sage because white was
invisible on a light basemap.

## 3. Baseline drought maps

`village_baselines.json` existed but nothing mapped it. New layers, group "Baseline":
normal NDVI for the month, normal rainfall for the month, NDVI departure (z-score), rainfall as a
percentage of normal. Definitions follow `baseline_drought_architecture.md` section 2
(per-village, per-calendar-month mean and standard deviation over 2016-2026). The legend's
"defn" button states each layer's definition.

## 4. Are the backend indices right for each village?

| Check | Result |
|---|---|
| SPI-1/3/6/12 recomputed from the village rain table (Thom gamma, Stagge zero-centre) vs stored SPI | correlation 0.9999 to 1.0000, mean abs. difference 0.002 to 0.006. **SPI arithmetic is correct.** |
| Village CDI recomputed from the stored inputs and `config/composite.yaml` | identical to the stored value (max diff 0.0) |
| Village PCI recomputed | identical |
| Class vs score in the served time series | 73 of 75,068 rows disagree, all within rounding of a threshold |

Problems that are real and **not** fixed here, because fixing them changes published numbers and
needs the team's decision (AGENTS.md rule 2):

1. **EVI is wrong at source.** The zonal EVI has median exactly 1.0; 20 % of village-months equal 1.0
   and 16 % exceed 1.0 (max 1.38). `build_baseline_drought.py` then silently clips to [-1, 1], hiding
   it. Its own comment says "DN not scaled by 10000". EVI carries weight 0.10 in the CDI. The
   dashboard no longer offers EVI as a map layer; the real-time job withholds EVI from new months.
   Rebuild EVI from the rasters with the reflectance scale fixed.
2. **VHI equals VCI in 100 % of rows** (no thermal band, documented in `build_village_indices.py`).
   With weights VHI 0.20 + VCI 0.15 the same signal carries 35 % of the composite, and it makes the
   `min_inputs: 3` rule easy to satisfy. Either drop VHI from the composite or build it as
   0.5 VCI + 0.5 PCI as `memory.md` defines.
3. **Rainfall is sampled at the village centroid on a ~5 km grid.** The rain used for PCI has about
   263 distinct values across 954 villages in a month (a village's rain is the value of the CHIRPS
   cell holding its centroid), and the rain used for SPI has about 700. They are two different
   samplings of the same data. Neighbouring villages therefore share one number and cliffs appear at
   cell edges. This is the main reason a village's rainfall can look wrong against ground
   knowledge. A polygon zonal mean computed once from the CHIRPS rasters for both PCI and SPI would
   fix the inconsistency (it cannot be rebuilt from this repository: the rasters are not committed).
4. **SPI is calibrated on 2016-2026 only** (about 10 values per calendar month). The status file used
   to claim "1991-2020". It now states the real reference. With so few values the gamma fit is
   rough; values beyond +/-2 deserve caution. Fetching CHIRPS 1991-2020 from Earth Engine and fitting
   on that is the standard remedy.
5. **The CDI class is sensitive to the short record.** Each village-month is judged against the
   median and MAD of about 7 values. Scoring a month against a reference that excludes the month
   itself reproduces the stored class for 89-100 % of villages in most months, but only 63 % for
   October 2026. Treat single-month class flips as uncertain.
6. **Three Sentinel-2 filename conventions are radiometrically inconsistent** (corrected with a
   per-batch additive offset, `estimate_offsets` in `build_village_indices.py`). New months come
   from Earth Engine `S2_SR_HARMONIZED`, a different processing chain; a bias check against the
   historic NDVI over an overlapping month should be run on the first live data.
7. **Monsoon gaps.** 22 of 98 Sentinel-2 months have a composite for fewer than half of the villages
   (June to September in most years). The map shows them as "no data" and the legend counts them.
8. **CHIRPS stops at 2026-08.** 2026-09 and 2026-10 have no rainfall, SPI or PCI, so their CDI uses
   only NDVI, VCI and VHI (which equals VCI). The home page shows input completeness for the month.

## 5. Real-time pipeline

Why it never worked on GitHub Actions, in the order it fails:

1. `chirps_gee.py` and `pipeline_gee.py` default to `data/vector/latur_tehsils.geojson`; the folder
   contains only `.gitkeep`, so both exit with "AOI not found".
2. `chirps_gee.py` called `ee.Initialize()` with no credentials and fell back to the interactive
   `ee.Authenticate()`, which hangs a CI job. It also read `UCSB-CHG/CHIRPS/monthly`, which Earth
   Engine does not publish (only DAILY and PENTAD), and tested `img is None` on a server-side object.
3. `build_village_indices.py` needs `rasterio` and local rasters, neither on the runner. The workflow
   treated that failure as "expected".
4. `run_realtime_pipeline_sync.py` ignored every failed step, never wrote the new month into
   `village_timeseries.json` or the village GeoJSON, overwrote `latest_status.json` with
   `monitoring_status: "operational"` and both sources "operational" regardless of outcome, and
   inserted a hard-coded Supabase row (village "Latur", cloud 5.2 %, SPI-1 copied from SPI-3).
5. The workflow did not install `pyyaml` (imported at module load), did not pass the `period`
   input, and always printed "SUCCESS".
6. `/api/v1/realtime` and `/api/v1/realtime/validate` returned constants: "operational",
   "latest period 2026-10", "96.25 % accuracy", "954 boundaries with 0 gaps".
7. The header showed a pulsing green "Live Sentinel-2 - GEE Operational" at all times.
8. `latest_status.json` was not in `frontend/public/data`, so the status route always fell back
   to a placeholder.

What replaced it: `scripts/realtime_update.py` (details in its docstring and
`.github/workflows/realtime_drought_sync.yml`).

* Village-level Sentinel-2 NDVI and CHIRPS rainfall from Earth Engine, month by month, oldest first;
  a CHIRPS month is used only when every daily image is published.
* SPI recomputed for all four scales; before writing, the job recomputes SPI on the stored history and
  aborts if it drifts from the stored values.
* VCI/VHI/PCI/CDI computed with `config/composite.yaml` against the existing record; history is not
  rewritten. Scoring an existing month reproduces its stored score exactly (tested).
* A month whose Sentinel-2 arrived before its rainfall is re-scored when the rainfall lands, which is
  exactly the 2026-09 / 2026-10 situation today.
* Rebuilds the history file, baselines, district series and latest GeoJSON.
* `latest_status.json` records what happened. The job exits non-zero when a due month produced
  nothing; the workflow still commits the status so the site shows "Behind" or "Incomplete" rather
  than a stale "operational", then fails the run.
* The status chip, `/api/v1/realtime` and `/api/v1/realtime/validate` now read the real files; the
  validator computes its checks from the served data.

**Not verified here:** no Earth Engine credentials were available in this environment, so the two
fetch functions (`fetch_s2`, `fetch_chirps`) have not been run against the live service. Everything
after them was exercised end to end with `--fixture` (rain for 2026-09 and 2026-10 plus a synthetic
2026-11): 954 villages scored, SPI tables extended, history left identical, status written. Run
`python scripts/realtime_update.py --period 2026-09` once with the service account to confirm.

## 6. Other fixes

* Upload page posted to `/upload/aoi`, a route that does not exist in the Next.js app. The AOI is now
  analysed in the browser (GeoJSON in EPSG:4326): drawn on the map, intersected with the 954 villages,
  area-weighted CDI, class split, village table, CSV download.
* Tehsil and district outlines were interactive polygons stacked above the villages and could swallow
  hover/click events; they are now inert panes. Cursor: open hand on the map, pointer only over a
  village. Tooltips no longer follow the cursor.
* Overlaps: basemap picker and control bar shared the same corner; the legend and timeline shared the
  bottom edge; the village drawer covered the page header. Legend and timeline now sit in one dock,
  controls in separate slots, the drawer inside the map frame.
* The Google tile URLs (`mt1.google.com`) are not an authorised tile API. The default basemap is now a
  plain CARTO light map; Google entries remain selectable, review before a public launch.
* Removed the sidebar "Official Government Drought Zone Notice" with fixed counts (490 / 228); it is
  now a sentence computed from the villages on screen.

## 7. Published accuracy figures that cannot be reproduced from this repository

`docs/README.md` and `docs/VALIDATION_AND_ACCURACY_REPORT.md` state a hit rate of 94.21 %, false-alarm
ratio 5.76 %, CSI 0.8906 and overall accuracy 96.25 %, from "28,450 of 30,200 actual drought crises"
matched to "government declarations / relief dispatches". The repository contains no ground-truth
dataset and no script that computes these metrics; the only code that mentioned them was the
hard-coded `/api/v1/realtime/validate` response, now removed. The same reports describe 951 villages,
a CDI of `0.50 PCI + 0.25 VCI + 0.25 TCI` and a TCI band that does not exist in the pipeline
(the real composite is in `config/composite.yaml`). Until the underlying declaration data and the
scoring script are added, do not quote these numbers externally.
