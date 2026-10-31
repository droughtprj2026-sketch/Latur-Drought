# Runbook: run the pipeline, update the results, schedule it

For a local coding agent (Antigravity) that has the Earth Engine and Supabase credentials. Do the steps in order and
stop at the first failure; report the exact error. Do not edit the pipeline code to make a step pass, and do not
use `--fixture` or any invented data.

## 0. Preconditions

* `.env` in the repo root (not committed) containing:
  ```
  GEE_PROJECT=<earth engine cloud project id>
  GEE_SERVICE_ACCOUNT_KEY=<JSON text of the service-account key, or a path to the .json file>
  SUPABASE_URL=https://<project>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY=<service role key>
  DATABASE_URL=<postgres connection string>       # only for step 3
  ```
  If the key is a personal login rather than a service account, run `earthengine authenticate` once and leave
  `GEE_SERVICE_ACCOUNT_KEY` unset.
* Python 3.11+, Node 20+.
  ```
  pip install -r scripts/requirements-realtime.txt pytest
  python -m pytest scripts/tests -q            # must pass
  ```

## 1. Check Earth Engine access

```
python -c "import sys; sys.path.insert(0,'scripts'); from common.gee import init_ee; ee=init_ee(); print(ee.Number(1).add(1).getInfo())"
```
Expect `2`. If it fails, the service account is not registered for Earth Engine or lacks permission on the
project; report the error text.

## 2. Check Supabase access

```
python scripts/publish_supabase.py --files-only
```
If this reports 404 for the bucket or a missing table, do step 3 first and repeat.

## 3. One-time database setup

Run `supabase/schema.sql`, then `supabase/migrations/0002_polygon_ids_storage_publishing.sql`
(Supabase SQL editor, or `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f <file>`). Both are idempotent.

## 4. Update to the latest month with the default formula

```
python scripts/realtime_update.py
python scripts/check_outputs.py
```
Expected: a month is ingested only when its sources fully cover it, so a recent month can legitimately be skipped
("not fully published"). That is correct. Report which months were ingested, which were skipped and why, and the
final status line. Do not force a month that was skipped.

## 5. Thermal and soil-moisture history (Landsat LST, Sentinel-1 VV)

This calls Earth Engine once per month from 2016 and can take hours; it is resumable.

```
python scripts/backfill_thermal.py
COMPOSITE_CONFIG=config/composite_thermal.yaml python scripts/rescore_panel.py
python scripts/compare_formulas.py
```
Report the thermal coverage printed by `rescore_panel.py`, the output of `compare_formulas.py`, and any months the
backfill skipped. Then run `python scripts/check_outputs.py` with `COMPOSITE_CONFIG=config/composite_thermal.yaml`.

**Do not switch the scheduled job to the thermal formula.** Switching changes every published class and needs the
project team's review of the comparison first. Keep `COMPOSITE_CONFIG` unset until they approve.

## 6. Publish everything once

```
python scripts/publish_supabase.py --full
```
Then check `https://<SUPABASE_URL>/storage/v1/object/public/drought-data/latest_status.json` opens, and that
`select count(*) from village_monthly;` is about 954 x months.

## 7. Schedule it

The job is incremental and safe to repeat; weekly is enough (all sources are monthly).

**Linux / macOS / WSL (cron):**
```
crontab -e
17 3 * * 1  cd /path/to/repo && ./scripts/run_scheduled.sh >> logs/cron.log 2>&1
```
(Mondays 03:17.) The script reads `.env`, runs the tests, the update and the output checks, writes
`logs/pipeline_<timestamp>.log`, and exits non-zero on any failure.

**Windows (Task Scheduler), from an elevated PowerShell:**
```
$a = New-ScheduledTaskAction -Execute "powershell.exe" `
     -Argument "-NoProfile -ExecutionPolicy Bypass -File D:\path\to\repo\scripts\run_scheduled.ps1"
$t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 3:17am
Register-ScheduledTask -TaskName "DroughtPipeline" -Action $a -Trigger $t -StartWhenAvailable
```
Use `-StartWhenAvailable` so a missed run executes when the machine is next on.

**Instead of a local schedule:** `.github/workflows/realtime_drought_sync.yml` runs weekly in GitHub Actions once the
secrets `GEE_SERVICE_ACCOUNT_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` and the variable `GEE_PROJECT` are
set. Use one scheduler, not both.

## 8. After each scheduled run

* `logs/` has the run log; exit code 0 means update and checks passed.
* The dashboard status bar shows the last Sentinel-2 / CHIRPS month and the time of the last run; it turns red after
  10 days without a run.
* `select * from pipeline_runs order by started_at desc limit 5;` lists runs and their steps.

## Things that are expected, not bugs

* CHIRPS/Landsat/Sentinel-1 months not yet published are skipped and shown as "no data".
* TCI/VHI have gaps in the monsoon (cloud); SMI from Sentinel-1 does not.
* Status "Behind" or "degraded" simply reports that a source is more than a month behind.
