# AGENTS.md

Instructions for coding agents working on this repo (Antigravity, OpenCode,
Claude Code, Cursor, Aider, etc.). This file is deliberately short and
authoritative; see `DEVELOPER.md` for the long-form architecture.

---

## 1. What this project is

**Real-Time Drought Monitoring — Latur District, Marathwada (2016–2026).**
A full-stack platform that ingests Sentinel-2 + CHIRPS rasters, computes
drought indices (SPI, NDVI, EVI, PCI, VHI → **CDI**) in Python, stores
them in Supabase (Postgres + PostGIS), serves them through a Go API, and
renders maps (Leaflet) and time-series charts (Recharts) in a Next.js
frontend.

Primary language ranking per the owner's standing preference:

1. **Go** — backend API, ingest CLI
2. **Python** — scientific processing, Colab scripts
3. **TypeScript** — Next.js frontend + Node.js gateway

---

## 2. Non-negotiable project rules

Agents MUST follow these without being reminded:

1. **Never commit `data/raw/**` or `.env`** — they are rasters and secrets.
2. **Never silently change CDI weights or SPI class thresholds** — they
   are documented in `scripts/common/classify.py`. If you change them,
   update `DEVELOPER.md` in the same commit.
3. **The Python → Go bridge is `outputs/Dashboard/`** — the Go service
   reads `drought_monitoring_master.csv`, `latest_status.json`,
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

```
drought-monitoring/
├── AGENTS.md           ← you are here
├── DEVELOPER.md        ← full architecture + API reference
├── CODE_OF_CONDUCT.md
├── README.md
├── docker-compose.yml  ← local Supabase + Go + Node
├── .env.example
│
├── scripts/            ← Python processing
│   ├── latur_chirps_spi.py       (CHIRPS → SPI, reference, do not break)
│   ├── latur_sentinel_indices.py (local-raster path: NDVI/EVI/NDMI/VCI from the raw folders)
│   ├── latur_cdi.py              (fuses SPI + NDVI + VHI + PCI → CDI)
│   ├── pipeline_gee.py           (near-real-time S2 from GEE for an AOI)
│   ├── chirps_gee.py             (near-real-time CHIRPS from GEE, UCSB-CHG/CHIRPS/monthly)
│   ├── composite_cdi.py          (transparent weighted multi-index composite)
│   ├── dashboard_master.py       (builds outputs/Dashboard/{master.csv,status,avail,manifest}.json)
│   ├── scheduler.py              (orchestrates incremental updates with manifests)
│   └── common/{raster.py, classify.py, manifest.py}
│
├── config/
│   ├── composite.yaml            (CDI weights, normalisation, thresholds, formula_version)
│   └── spi.yaml                  (SPI reference climatology + QC rules)
│
├── backend-go/         ← primary API (chi + pgx)
├── backend-node/       ← gateway: auth, uploads, static passthrough
└── frontend/           ← Next.js 14 App Router + Leaflet + Recharts
```

---

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

## 5. How to run it end-to-end

```bash
# 1. Python processing (populates data/processed/)
cd scripts
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python latur_chirps_spi.py
python latur_sentinel_indices.py
python latur_cdi.py

# 2. Backend
cd ../backend-go  && go run ./cmd/server   # → :8080
cd ../backend-node && pnpm install && pnpm dev   # → :4000

# 3. Frontend
cd ../frontend && pnpm install && pnpm dev        # → :3000
```

Or `docker compose up` from repo root.

---

## 6. Agent-specific hints

### Antigravity

- Primary agent for scientific scripting (Colab, GEE). When editing
  `scripts/*.py`, keep the script runnable **standalone in Colab**
  (upload prompt, Drive copy, inline previews).
- Antigravity's artifacts belong under `scripts/colab_artifacts/` — do
  not scatter PNGs into `data/`.

### OpenCode

- Primary agent for Go + TypeScript. Default to `go test ./...` and
  `pnpm test` after any change. Do not bypass CI.
- When adding a new endpoint, update **both** `DEVELOPER.md §7.2` and
  the typed client in `frontend/lib/api.ts`.

### Shared conventions for all agents

- Branch names: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`.
- Conventional Commits. Co-author tag preserved on AI commits.
- Open a PR early with a 5-line summary; keep diffs under ~400 lines.
- Never run `rm -rf data/` or any destructive `git` command without
  confirmation.

---

## 7. "Done" definition

A change is done when **all** of these are true:

- [ ] `go vet ./... && go test ./...` passes in `backend-go/`.
- [ ] `pnpm lint && pnpm test` passes in `backend-node/`.
- [ ] `pnpm lint && pnpm build` passes in `frontend/`.
- [ ] `ruff check . && pytest` passes in `scripts/`.
- [ ] If the output contract changed, `data/processed/json/manifest.json`
      is regenerated and committed.
- [ ] `DEVELOPER.md` reflects any new endpoint, env var, or script.

---

## 8. Contact

Project owner: **rajnandinikadam221@gmail.com**
