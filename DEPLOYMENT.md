# Deployment

Pieces: Supabase (database + file storage), Google Earth Engine (data), GitHub Actions (schedule), Vercel (site).

## 1. Supabase

1. Create a project.
2. Run `supabase/schema.sql`, then `supabase/migrations/0002_polygon_ids_storage_publishing.sql` in the SQL
   editor (or add the `DATABASE_URL` secret and run the "Supabase migrations" workflow). Migration 0002 is
   idempotent. It adds polygon-id keys, `village_monthly`, `pipeline_runs`, the public `drought-data` bucket and the
   security rules (anon read only; writes need the service role).
3. Copy the project URL, anon key and service-role key.
4. Load the data once: `python scripts/publish_supabase.py --full` with `SUPABASE_URL` and
   `SUPABASE_SERVICE_ROLE_KEY` set.

`supabase/seed_data.sql` is an old name-keyed export (it drops 3 of 954 villages); use the publisher instead.

## 2. Earth Engine access for the scheduled job

The job authenticates with a service account, not a personal login.

1. In the Cloud project: IAM > Service Accounts > create one; grant "Service Usage Consumer" and
   "Earth Engine Resource Viewer".
2. Register the service account for Earth Engine (https://code.earthengine.google.com/register).
3. Create a JSON key and store its text in the GitHub secret `GEE_SERVICE_ACCOUNT_KEY`. Never commit or paste it
   (`*service_account*.json` and `igneous-*.json` are git-ignored).
4. Set the repository variable `GEE_PROJECT` to the project id.

## 3. GitHub

| Where | Name |
|---|---|
| Variables | `GEE_PROJECT`, optionally `COMPOSITE_CONFIG` |
| Secrets | `GEE_SERVICE_ACCOUNT_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` (migrations) |

Workflows:
* `ci.yml`: builds the site and runs the Python tests on every push and PR.
* `realtime_drought_sync.yml`: weekly, plus manual run (optional `period`). Runs tests, then the update, then
  commits the small status/manifest/state files. With Supabase configured the large derived files are published
  to Storage and not committed. A failed pipeline still commits `latest_status.json` (status "degraded") and then
  fails the job.
* `supabase_migrate.yml`: applies `supabase/migrations/*.sql`.

Run "Near-real-time drought update" once by hand after setup and read the log.

## 4. Vercel (site)

Either import the repo in Vercel (root directory `frontend`), or let `deploy.yml` deploy on push to `main` /
`operational` using the secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (the step is skipped when
`VERCEL_TOKEN` is not set). `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are also needed as
secrets for the CI build. Environment variables:

```
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
NEXT_PUBLIC_SUPABASE_BUCKET=drought-data
NEXT_PUBLIC_DATA_SOURCE=supabase        # "static" serves only the bundled snapshot
```

The service-role key must never be a `NEXT_PUBLIC_` variable.

If Supabase is unreachable the site falls back to the snapshot in `frontend/public/data` and shows a
"Bundled snapshot" chip. The snapshot is no longer refreshed by the weekly job once Supabase is configured, so it
ages; the status ribbon also turns red when no pipeline run has been recorded for more than 10 days.

## 5. Checks after deploying

* `/api/v1/realtime/validate` reports the real checks (polygon ids, coverage, source freshness).
* The status ribbon shows the last Sentinel-2 / CHIRPS month and when the pipeline last ran.
* `select * from pipeline_runs order by started_at desc limit 5;` shows the run log.
