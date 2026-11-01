# frontend/public/data

What the dashboard reads. The weekly job (`scripts/realtime/realtime_update.py`) regenerates every derived file here;
with Supabase configured they are published to the `drought-data` Storage bucket and the site reads them from there
first, falling back to these copies.

| File | Written by |
| ---- | ---------- |
| `village_timeseries.json`, `villages_by_tehsil.json`, `village_baselines.json` | `analysis/build_village_timeseries.py`, `analysis/build_village_registry.py` |
| `district_monthly.json`, `latur_villages_latest.geojson`, `zonal_latest.json`, `latest_status.json` | `realtime/realtime_update.py` |
| `tehsil_analytics.json` | `analysis/build_tehsil_analytics.py` |
| `latur_district.geojson`, `latur_tehsils.geojson`, `latur_villages.geojson`, `latur_bbox.json` | static boundaries (Survey of India), not regenerated |

After changing `config/composite.yaml`: `python scripts/analysis/rescore_history.py --rebuild`.
