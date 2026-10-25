# AGENTS.md

Instructions for coding agents working on this repo (Antigravity, OpenCode,
Claude Code, Cursor, Aider, etc.). This file is deliberately short and
authoritative; see `DEVELOPER.md` for the long-form architecture.

---

## 1. What this project is

**Near Real-Time Drought Monitoring System — Latur District, Marathwada.**
Developed by the Department of Geoinformatics, Shivaji University.
Python ingests Sentinel-2, Sentinel-1 (soil moisture), Landsat 8/9 (LST) and CHIRPS from
Earth Engine, computes SPI, NDVI, VCI, TCI, SMI, VHI and the composite
**CDI**, and publishes to Supabase (Postgres rows + a public Storage
bucket). A Next.js app (API routes + Leaflet + Recharts) reads from
Supabase. There is no Go service in this repository and `backend-node/` is
unused; see `DEVELOPER.md` for the real layout.

**Data rules:** never hard-code data (months, tehsils, project ids, fallback
values); never run `--fixture` outside a scratch copy; an input that is not
published stays empty and the composite drops it. See
`docs/THERMAL_AND_SOIL_MOISTURE.md` and `docs/DATA_ACCURACY_AUDIT.md`.

Languages: **Python** (processing, pipeline), **TypeScript** (Next.js app).

---

## 2. Non-negotiable project rules

Agents MUST follow these without being reminded:

1. **Never commit `data/raw/**` or `.env`** — they are rasters and secrets.
2. **Never silently change CDI weights or SPI class thresholds** — they
   are documented in `scripts/common/classify.py`. If you change them,
   update `DEVELOPER.md` in the same commit.
3. **The Python → dashboard bridge is `outputs/Dashboard/` and the
   Supabase publish step** (`scripts/publish_supabase.py`). Any Go service
   would read `drought_monitoring_master.csv`, `latest_status.json`,
   `data_availability.json`, and `processing_manifest.json`. If you add
   a new column, add it to `scripts/dashboard_master.MASTER_COLUMNS` AND
   to the SQL migration.
4. **No learned classifier.** The Random Forest classifier has been
   retired. The final drought class is produced by
   `scripts/composite_cdi.py` from a transparent weighted multi-index
   composite. Weights, thresholds, and the formula version live in
   `config/composite.yaml` — edit the YAML, not the code.
   If fewer than `min_inputs` components are available for a
   polygon-period, mark it `pending`; never fill missing inputs.
5. **Incremental processing only.** Every pipeline run reads the
   per-source manifest (`manifests/sentinel.json`, `manifests/chirps.json`)
   and processes only the missing or affected periods. A new CHIRPS
   month retriggers EVERY rolling SPI window that includes it.
6. **Never claim real-time when source latency prevents it.** If the
   last successful period is older than today, the status chip is
   "degraded" and the dashboard shows the actual observation date.
7. **Leaflet must be dynamically imported** in Next.js (`ssr: false`).
8. **All Supabase writes use the `service_role` key**, server-side only.
9. **Preserve the dual-naming parser** in the Sentinel + CHIRPS scripts.
   Raw folders contain multiple filename styles and sidecar files —
   see §4 below.
10. **No emojis in source files** unless the owner asks.

---

## 3. Repository map

See `DEVELOPER.md` section 1 for the annotated layout. In short: `scripts/` (pipeline, `common/`, `tests/`),
`config/` (composite formulas), `supabase/` (schema + migrations), `frontend/` (Next.js app), `output/` `data/`
`outputs/` (history tables and processed files), `docs/`.

## 4. Raw data reality — read before touching processing scripts

The raw Sentinel-2 folder is **not clean**. The ingest + processing code
is written to tolerate this. Do not "tidy up" the regex or the file
scanner without preserving every one of these behaviors:

### 4.1 Three Sentinel-2 filename conventions coexist

```
S2_Latur_YYYY_MM.tif           ← most common
S2_L2A_Latur_YYYY_MM.tif       ← 2024 batch
Latur_S2_YYYY_MM.tif           ← 2017/2021/2024/2026 batches
```

### 4.2 CHIRPS has two conventions

```
CHIRPS_Latur_YYYY_MM_mm.tif
Latur_precip_YYYY_MM.tif
```

### 4.3 Files that must be SKIPPED

- `*.aux.xml` — GDAL sidecar
- `*.ovr` — overview pyramids
- `*.crdownload` — incomplete Chrome downloads
- `*.py` — stray Colab scripts (e.g. `Latur_S2_2021_Mar_Oct.py`)
- `*.zip` — Google Drive export archives (`drive-download-*.zip`)
- `*.csv` — logs like `cloud_threshold_log.csv`
- Any file starting with `._` (macOS metadata)

### 4.4 Duplicate months are expected

Some months exist under two names (e.g. 2021-11, 2021-12, all of 2022,
most of 2024). The scanner keeps **one** copy per `(year, month)` using
`PREFERRED_PREFIX` and logs the duplicate.

### 4.5 Missing years

2019 and 2025 have no Sentinel rasters at all. The pipeline must leave
those months as `NaN` and the frontend must render them as grey "no data"
cells — not zero.

---

## 5. How to run it

See `RUN.md`. Minimum before any commit:

```bash
pip install -r scripts/requirements-realtime.txt pytest && python -m pytest scripts/tests -q
cd frontend && npm install && npx tsc --noEmit && npm run build
```

## 6. Agent-specific hints

### Scientific scripts

- Raster batch scripts (`latur_*`, `build_village_indices.py`) may run standalone in Colab; keep them importable
  without Earth Engine. The weekly job code (`realtime_update.py`, `common/`) must not depend on rasters.
- Artifacts from Colab belong under `scripts/colab_artifacts/`, not in `data/`.

### Web app

- Add or change a map layer only in `frontend/lib/metrics.ts`. Run `npx tsc --noEmit` and `npm run build`.

### Shared conventions for all agents

- Branch names: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`.
- Conventional Commits. Co-author tag preserved on AI commits.
- Open a PR early with a 5-line summary; keep diffs under ~400 lines.
- Never run `rm -rf data/` or any destructive `git` command without
  confirmation.

---

## 7. "Done" definition

A change is done when **all** of these are true:

- [ ] `python -m pytest scripts/tests -q` passes.
- [ ] `cd frontend && npx tsc --noEmit && npm run build` passes.
- [ ] No hard-coded data, no synthetic data in committed outputs, no secrets.
- [ ] If a threshold, weight, palette or formula changed: YAML, `classify.py`, `classify.ts`, `metrics.ts` and the
      docs are updated together (a test checks parity).
- [ ] `DEVELOPER.md` / `RUN.md` reflect any new script, env var or workflow.

---

## 8. Contact

Project owner: **rajnandinikadam221@gmail.com**

Project team: Rajnandini U. Kadam, Aishwarya B. Jagtap, Pavan S. Devkar, Shital B. Gurav, Trupti U. Jadhav.
Guide: Dr. Sachin S. Panhalkar, Head of Department, Department of Geography.
