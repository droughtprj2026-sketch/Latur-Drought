# DEVELOPER.md

**Project:** Real-Time Drought Monitoring — Latur District, Marathwada
**Study period:** 2016 – 2026
**Owner:** rajnandinikadam221@gmail.com

This document is for developers who will build, run, and extend the Latur
Drought Monitoring platform. It covers the full stack: data ingestion
(Sentinel-2 + CHIRPS), index processing (SPI, NDVI, VHI, PCI, EVI → CDI),
the Go + Node.js backend, the Next.js + Leaflet frontend, and the
Supabase data layer.

---

## 1. System Overview

```
                 ┌──────────────────────────────────────────┐
                 │  SOURCE DATA  (downloaded, 2016 – 2026)  │
                 │  • Sentinel-2 L2A rasters  (GEE / Drive) │
                 │  • CHIRPS monthly precipitation GeoTIFFs │
                 │  • Latur district / tehsil shapefile     │
                 └──────────────────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  PROCESSING LAYER  (Python, Colab / local)                │
   │  scripts/latur_chirps_spi.py        → SPI-1/3/6/12        │
   │  scripts/latur_sentinel_indices.py  → NDVI, EVI, PCI, VHI │
   │  scripts/latur_cdi.py               → CDI composite        │
   │  Outputs: GeoTIFF + GeoJSON + CSV + JSON  → data/processed │
   └───────────────────────────────────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  STORAGE LAYER  (Supabase)                                │
   │  • Postgres (PostGIS)     — monthly index values, metadata│
   │  • Storage buckets        — raw GeoJSON / PNG map tiles   │
   │  • Row-level security     — public read, admin write      │
   └───────────────────────────────────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  BACKEND                                                  │
   │  • Go service (primary)   — /api/v1/*  index + CDI queries│
   │  • Node.js gateway        — auth, upload, static GeoJSON  │
   └───────────────────────────────────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  FRONTEND  (Next.js 14, App Router)                       │
   │  • Leaflet choropleth map (pixel / tehsil polygons)       │
   │  • Recharts time-series panels (SPI, NDVI, CDI)           │
   │  • Year / month / index selector                          │
   └───────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Layer                 | Technology                                   |
| --------------------- | -------------------------------------------- |
| Frontend              | Next.js 14 (App Router), React 18, TypeScript |
| Map rendering         | Leaflet 1.9 + react-leaflet                   |
| Charts                | Recharts (time-series), D3 (heatmaps)         |
| Styling               | Tailwind CSS                                  |
| Backend (primary)     | **Go 1.22** — chi router, pgx, GeoJSON       |
| Backend (gateway)     | **Node.js 20** (Express) — auth + file upload |
| Scripting / science   | **Python 3.11** — rasterio, geopandas, scipy  |
| Database              | **Supabase** (Postgres 15 + PostGIS 3.4)      |
| Object storage        | Supabase Storage                              |
| Auth                  | Supabase Auth (JWT)                           |
| Deployment            | Vercel (frontend) · Fly.io / Render (Go) · Supabase cloud |

---

## 3. Repository Layout

```
drought-monitoring/
├── DEVELOPER.md
├── CODE_OF_CONDUCT.md
├── README.md
│
├── scripts/                      # Python processing (one-off / Colab)
│   ├── latur_chirps_spi.py       # SPI-1/3/6/12 from CHIRPS rainfall
│   ├── latur_sentinel_indices.py # NDVI, EVI, PCI, VHI from Sentinel-2
│   ├── latur_cdi.py              # Composite Drought Index
│   ├── common/
│   │   ├── raster.py             # read_stack / reproject helpers
│   │   └── classify.py           # drought-class thresholds
│   └── requirements.txt
│
├── data/
│   ├── raw/                      # DO NOT COMMIT — large rasters
│   │   ├── sentinel/{YYYY}/
│   │   └── chirps/{YYYY}/
│   ├── vector/
│   │   ├── latur_district.geojson
│   │   └── latur_tehsils.geojson
│   └── processed/                # outputs the frontend consumes
│       ├── spi/SPI_Latur_{YYYY}.geojson
│       ├── ndvi/NDVI_Latur_{YYYY}.geojson
│       ├── cdi/CDI_Latur_{YYYY}.geojson
│       ├── csv/*.csv
│       └── json/district_monthly.json
│
├── backend-go/                   # primary API
│   ├── cmd/server/main.go
│   ├── internal/
│   │   ├── api/                  # chi handlers
│   │   ├── db/                   # pgx + sqlc queries
│   │   ├── indices/              # SPI/NDVI/CDI domain logic
│   │   └── geojson/              # polygon encoders
│   ├── migrations/               # SQL files applied to Supabase
│   ├── go.mod
│   └── Dockerfile
│
├── backend-node/                 # gateway: auth, uploads, static
│   ├── src/
│   │   ├── index.ts
│   │   ├── routes/
│   │   │   ├── auth.ts
│   │   │   ├── upload.ts         # upload processed GeoJSON
│   │   │   └── proxy.ts          # proxies /api/v1 to Go service
│   │   └── middleware/supabase.ts
│   ├── package.json
│   └── tsconfig.json
│
└── frontend/                     # Next.js app
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx              # dashboard shell
    │   ├── map/page.tsx
    │   └── timeseries/page.tsx
    ├── components/
    │   ├── map/LaturMap.tsx      # Leaflet choropleth
    │   ├── map/LegendBar.tsx
    │   ├── charts/SPIChart.tsx
    │   ├── charts/CDIHeatmap.tsx
    │   └── ui/IndexSelector.tsx
    ├── lib/
    │   ├── api.ts                # typed fetch wrapper
    │   └── supabase.ts
    ├── public/data/              # small bootstrap GeoJSON
    ├── package.json
    └── next.config.mjs
```

---

## 4. Prerequisites

Install locally:

- **Node.js 20+** and **pnpm** (`corepack enable`)
- **Go 1.22+**
- **Python 3.11+** with `pip` and `virtualenv`
- **GDAL 3.6+** (required by `rasterio` / `geopandas`)
- **Docker** (for running Go backend container during integration tests)
- A **Supabase project** (free tier is fine); keep the project URL and both
  the `anon` and `service_role` keys ready
- **Google Earth Engine account** (only if you plan to re-download Sentinel-2)

Create a project-root `.env` (never commit it) with:

```env
# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...          # server-side only

# Postgres (same project, direct connection for Go)
DATABASE_URL=postgres://postgres:<pwd>@db.<project>.supabase.co:5432/postgres?sslmode=require

# Backend
GO_API_PORT=8080
NODE_GATEWAY_PORT=4000
NEXT_PUBLIC_API_BASE=http://localhost:4000

# Processing
DATA_DIR=./data/raw
OUTPUT_DIR=./data/processed
```

Frontend reads only `NEXT_PUBLIC_*` keys. Service-role keys must stay on
the server (Go + Node) side.

---

## 5. Data Pipeline

### 5.1 Inputs

| Source       | Variable        | Resolution        | Years        | Where it lives            |
| ------------ | --------------- | ----------------- | ------------ | ------------------------- |
| Sentinel-2   | B2–B12 reflectance | 10 m           | 2016 – 2026  | `data/raw/sentinel/{YYYY}/` |
| CHIRPS       | Monthly rainfall (mm) | ~5 km       | 2016 – 2026  | `data/raw/chirps/{YYYY}/`   |
| Shapefile    | Latur district + tehsils | vector  | static       | `data/vector/`              |

CHIRPS GeoTIFFs follow one of two naming conventions
(both are handled by `scripts/latur_chirps_spi.py`):

```
CHIRPS_Latur_YYYY_MM_mm.tif
Latur_precip_YYYY_MM.tif
```

### 5.2 Index computations

| Index  | Script                                      | Formula (summary)                                           |
| ------ | ------------------------------------------- | ----------------------------------------------------------- |
| SPI-k  | `latur_chirps_spi.py`                       | Gamma CDF fit per pixel per calendar month (McKee 1993). Zero-rain correction `H = q + (1 − q) · G`, with `H(0) = q/2` (Stagge 2015). SPI = Φ⁻¹(H). Computed for k = 1, 3, 6, 12 months. |
| NDVI   | `latur_sentinel_indices.py`                 | `(NIR − RED) / (NIR + RED)` on Sentinel-2 B8, B4            |
| EVI    | `latur_sentinel_indices.py`                 | `2.5 · (NIR − RED) / (NIR + 6·RED − 7.5·BLUE + 1)`          |
| PCI    | `latur_sentinel_indices.py`                 | `(P − P_min) / (P_max − P_min)` using CHIRPS monthly        |
| VHI    | `latur_sentinel_indices.py`                 | `α·VCI + (1 − α)·TCI`, α = 0.5                              |
| NSMI   | `export_ndmi_nsmi_rasters.py`               | `(SWIR1 − SWIR2) / (SWIR1 + SWIR2)` — Normalised Soil Moisture Index (Boles 2020) |
| NDMI   | `export_ndmi_nsmi_rasters.py`               | `(NIR − SWIR1) / (NIR + SWIR1)` — Normalised Difference Moisture Index (Gao 1996)  |
| **CDI** | `build_village_indices.py`                 | Transparent weighted multi-index composite (cdi-v2026.11). Weights from `config/composite.yaml`: `0.40·SPI + 0.25·VCI + 0.15·NDVI + 0.10·PCI + 0.10·NSMI`. Aligned with Marathwada PCA-CDI evidence (Pawar 2022) and NDMA 2016 framework. Missing inputs excluded; fewer than `min_inputs` → `pending`. References: WMO (2012), McKee (1993), Kogan (1995), NDMA (2016), Pawar (2022). **Replaces the retired Random Forest classifier.** |

### 5.3 Running the historical pipeline (local batch)

```bash
cd scripts
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python latur_chirps_spi.py          # writes SPI GeoTIFFs + GeoJSON + CSV
python latur_sentinel_indices.py    # writes NDVI/EVI/PCI/VHI GeoJSON
python build_village_indices.py     # village-level zonal stats + CDI composite
python build_baseline_drought.py    # baseline anomalies + GeoJSON export
python dashboard_master.py          # builds outputs/Dashboard/ files for Go API
```

### 5.4 Running the near-real-time pipeline (GEE)

The incremental pipeline fetches new Sentinel-2 and CHIRPS data from
Google Earth Engine using a service account. Set these env vars in `.env`:

```env
GEE_PROJECT=<your-gee-project-id>
GEE_SERVICE_ACCOUNT_KEY=<path-to-service-account-key.json>
PIPELINE_SINCE=2026-01          # start month for incremental runs
```

Run each step independently or use the scheduler:

```bash
# 1. Pull CHIRPS monthly (incremental — only missing months)
python scripts/chirps_gee.py --from 2016-01 --to latest

# 2. Recompute SPI only for the months CHIRPS marked stale
python scripts/latur_chirps_spi.py

# 3. Pull Sentinel-2 for the AOI (independent cadence)
python scripts/pipeline_gee.py \
    --aoi data/vector/latur_tehsils.geojson \
    --from 2016-01 --to 2026-10

# 4. Compute the transparent multi-index composite
python scripts/composite_cdi.py

# 5. Build dashboard master + status files
python scripts/dashboard_master.py

# Or do steps 1-5 in one tick:
python scripts/scheduler.py
```

### 5.5 Changing composite weights without touching code

Edit `config/composite.yaml`, then re-run:

```bash
python scripts/composite_cdi.py && python scripts/dashboard_master.py
```

`composite_formula_version` is stamped on every row so classifications
remain traceable to the config that produced them.

### 5.6 Testing matrix

| Scenario                                     | Expected behavior                                      |
| -------------------------------------------- | ------------------------------------------------------ |
| New CHIRPS monthly observation               | Affected month + its SPI windows recomputed            |
| New Sentinel-2 scene                         | Only that period's NDVI/EVI/VCI/VHI recomputed         |
| CHIRPS updates, Sentinel-2 does not          | SPI refreshes; vegetation indices unchanged            |
| Sentinel-2 updates, CHIRPS does not          | Vegetation indices refresh; SPI stays as last valid    |
| SPI cannot be calculated (insufficient data) | Row written with empty `SPI_*`; composite re-weights   |
| < `min_inputs` composite components available| Row written; class = `pending`; CDI empty              |
| Processing fails mid-run                     | Last validated master stays published                  |
| Composite weights changed in YAML            | Next run produces rows stamped with new formula_version |

### 5.7 Running the pipeline (Colab)

The CHIRPS → SPI script is also designed for Colab. See its docstring
header: zip the raw folder, upload or point `ZIP_PATH` at Drive, then
`%run latur_chirps_spi.py`. Outputs are copied back to Drive at
`/content/drive/MyDrive/Droughtprj2026/SPI_output`.

### 5.5 Processed outputs — the frontend contract

Everything the frontend reads is written under `data/processed/`:

```
data/processed/
├── spi/
│   ├── SPI_Latur_2016.geojson         # 1 polygon per pixel; columns SPI1_01..SPI12_12
│   └── SPI_Latur_2017.geojson ...
├── ndvi/NDVI_Latur_YYYY.geojson
├── cdi/CDI_Latur_YYYY.geojson
├── csv/
│   ├── SPI_Latur_district_monthly.csv
│   └── CDI_Latur_district_monthly.csv
└── json/
    ├── district_monthly.json          # time-series feed for charts
    └── manifest.json                  # years + indices currently available
```

`manifest.json` is the discovery file. The frontend hits it first on
load, then requests only the GeoJSON it needs.

**Important:** the processed files are the _only_ bridge between
Python and the Go backend. The Go service does not re-read rasters.

---

## 6. Database (Supabase)

Enable the `postgis` extension once:

```sql
create extension if not exists postgis;
```

### 6.1 Core tables

```sql
-- Tehsil polygons for Latur (loaded once from shapefile).
create table tehsils (
  id          serial primary key,
  name        text not null,
  geom        geometry(MultiPolygon, 4326) not null
);
create index on tehsils using gist (geom);

-- District-mean monthly index time series (feeds charts).
create table monthly_index (
  id          bigserial primary key,
  index_name  text not null,            -- 'SPI1','SPI3','NDVI','VHI','PCI','EVI','CDI'
  year        int  not null,
  month       int  not null check (month between 1 and 12),
  value       double precision,
  class_label text,
  pct_area_dry double precision,
  unique (index_name, year, month)
);

-- Per-pixel index values (loaded from processed GeoJSON).
create table pixel_index (
  id          bigserial primary key,
  index_name  text not null,
  year        int  not null,
  month       int  not null,
  pixel_id    int  not null,
  lon         double precision,
  lat         double precision,
  value       double precision,
  geom        geometry(Polygon, 4326)
);
create index on pixel_index (index_name, year, month);
create index on pixel_index using gist (geom);
```

### 6.2 Row-level security

```sql
alter table tehsils         enable row level security;
alter table monthly_index   enable row level security;
alter table pixel_index     enable row level security;

create policy "public read" on monthly_index  for select using (true);
create policy "public read" on tehsils        for select using (true);
create policy "public read" on pixel_index    for select using (true);
-- writes are limited to the service_role key (used only by the ingest job).
```

### 6.3 Loading processed outputs

Use the Node.js gateway's `/api/ingest` endpoint (admin JWT required),
or run `backend-go/cmd/ingest` as a one-off CLI:

```bash
cd backend-go
go run ./cmd/ingest -input ../data/processed -year 2026
```

---

## 7. Backend — Go service (primary)

The Go service exposes the versioned REST API that the frontend uses.
It is intentionally thin: all heavy computation already happened in
Python; Go only queries Supabase and emits GeoJSON / JSON.

### 7.1 Run locally

```bash
cd backend-go
go mod download
go run ./cmd/server
# → listening on :8080
```

### 7.2 Endpoints

| Method | Path                                             | Returns                                    |
| ------ | ------------------------------------------------ | ------------------------------------------ |
| GET    | `/api/v1/health`                                 | `{"status":"ok"}`                          |
| GET    | `/api/v1/manifest`                               | years + indices available                  |
| GET    | `/api/v1/indices/:name/:year/:month`             | GeoJSON FeatureCollection (choropleth)     |
| GET    | `/api/v1/timeseries/:name?from=YYYY-MM&to=YYYY-MM` | `[{date, value, class}]` district mean   |
| GET    | `/api/v1/cdi/:year/:month`                       | CDI GeoJSON + per-tehsil summary           |
| GET    | `/api/v1/tehsils`                                | Tehsil polygons (static)                   |
| GET    | `/api/v1/status`                                 | `latest_status.json` (header chip)         |
| GET    | `/api/v1/availability`                           | `data_availability.json` (per-source periods) |
| GET    | `/api/v1/master?tehsil=&from=&to=`               | rows from `drought_monitoring_master.csv`  |
| GET    | `/api/v1/latest?tehsil=Latur`                    | most recent validated row for a tehsil     |
| GET    | `/api/v1/compare?index=&a=YYYY-MM&b=YYYY-MM`     | two periods side by side                   |
| GET    | `/api/v1/animation?index=&from=&to=`             | ordered frame list for the player          |
| POST   | `/api/v1/admin/ingest` (service-role JWT)        | triggers re-ingest of `data/processed`     |
| POST   | `/api/v1/admin/aoi`    (service-role JWT)        | upload shapefile/GeoJSON AOI → `pipeline_gee.py` |

### Dashboard data contract

Every endpoint above that is not raster-derived reads directly from
`outputs/Dashboard/`:

```
outputs/Dashboard/
├── drought_monitoring_master.csv   (one row per tehsil per period; 29 columns)
├── latest_status.json              (status chip + latest Sentinel-2 / CHIRPS dates)
├── data_availability.json          (per-source list of successful period_ids)
├── processing_manifest.json        (consolidated view of per-source manifests)
└── scheduler_last_run.json         (log of the last scheduler tick)
```

The per-source authoritative manifests live under
`data/processed/manifests/{sentinel.json, chirps.json}`. Everything in
`outputs/Dashboard/` is regenerated by `scripts/dashboard_master.py`.

`:name` ∈ `spi1 | spi3 | spi6 | spi12 | ndvi | evi | pci | vhi | cdi`

### 7.3 Example response — `/api/v1/timeseries/spi3?from=2024-01&to=2026-10`

```json
[
  { "date": "2024-01", "value": -0.42, "class": "Near normal",    "pct_area_dry": 12.3 },
  { "date": "2024-02", "value": -1.11, "class": "Moderately dry", "pct_area_dry": 54.7 },
  ...
]
```

### 7.4 Project conventions

- Handlers under `internal/api/` are **thin**: parse → call `internal/db`
  → marshal.
- Error envelope: `{"error":{"code":"NOT_FOUND","message":"..."}}`.
- All responses are gzip-encoded by default.
- Tests live next to the code (`foo.go` / `foo_test.go`). Run with
  `go test ./...`. CI must stay green.

---

## 8. Backend — Node.js gateway

Thin Express gateway. Its only jobs:

1. **Auth** — exchanges Supabase session JWTs; stamps them onto outgoing
   requests to the Go service.
2. **Uploads** — accepts processed GeoJSON / CSV files from the admin UI
   and writes them to Supabase Storage.
3. **Static passthrough** — serves `data/processed/*` as a CDN fallback
   when the Go service is cold.

```bash
cd backend-node
pnpm install
pnpm dev     # → :4000
```

Routes:

```
POST  /auth/login       → Supabase email + password
POST  /auth/logout
POST  /upload/geojson   (admin) → Supabase Storage bucket `processed/`
GET   /api/v1/*         → proxied to Go service
```

---

## 9. Frontend — Next.js + Leaflet

```bash
cd frontend
pnpm install
pnpm dev     # → http://localhost:3000
```

### 9.1 Pages

- `/` — **dashboard**. Title bar at the top; controls strip with an
  **index dropdown** (NDVI / SPI / VCI / VHI / EVI / PCI / CDI) + **year
  slider** + month selector; map on the left, drought-condition info
  panel on the right; time-series chart below.
- `/map` — full-screen Leaflet view with the same controls and the
  **basemap switcher** (OSM, Carto Light/Dark, Esri Satellite, Esri
  Topographic, OpenTopoMap) and the layers control for district / tehsil
  / villages overlays.
- `/timeseries` — Recharts bar chart for the chosen index plus the CDI
  year × month heatmap.
- `/about` — who built the dashboard, under which organization, why
  Latur, limitations, roadmap.
- `/sources` — every satellite, rainfall and vector dataset the
  dashboard draws on, with full citations and the index formulas.

### 9.2 Map component (`components/map/LaturMap.tsx`)

- Loads `latur_tehsils.geojson` from `/public/data/` for the base boundary.
- Pulls the active index as GeoJSON from
  `GET /api/v1/indices/:name/:year/:month`.
- Colors each pixel polygon via the standard SPI/NDVI/CDI scale
  (see `components/map/LegendBar.tsx`):

| Class            | Color     |
| ---------------- | --------- |
| Extremely dry    | `#7f0000` |
| Severely dry     | `#d7301f` |
| Moderately dry   | `#fdae61` |
| Near normal      | `#f7f7f7` |
| Moderately wet   | `#a6d96a` |
| Very wet         | `#1a9850` |
| Extremely wet    | `#00441b` |

- Leaflet must be dynamically imported — it touches `window`:
  ```tsx
  const LaturMap = dynamic(() => import('@/components/map/LaturMap'), { ssr: false });
  ```

### 9.3 Charts

- `SPIChart.tsx` — multi-scale bar chart (SPI-1/3/6/12) on one shared
  x-axis; colors come from the same class scale as the map.
- `CDIHeatmap.tsx` — year × month heatmap, D3 color scale.

### 9.4 API wrapper (`lib/api.ts`)

```ts
export async function getManifest()                      { ... }
export async function getIndexGeoJSON(name, year, month) { ... }
export async function getTimeseries(name, from, to)      { ... }
```

All calls go through `NEXT_PUBLIC_API_BASE` so you can point the frontend
at a local Go service, the Node gateway, or production without rebuild.

---

## 10. Development Workflow

### 10.1 Branching

- `main` — protected, always deployable.
- `feat/<topic>` — feature branches, squash-merged.
- `fix/<topic>` — bug fixes.
- Open a PR early; keep it under ~400 lines of diff where possible.

### 10.2 Commits

Conventional Commits:

```
feat(map): add CDI layer toggle
fix(go): clamp SPI value when gamma fit fails
chore(deps): bump next to 14.2.5
```

### 10.3 Local verification before pushing

```bash
# Go
cd backend-go  && go vet ./... && go test ./...

# Node
cd backend-node && pnpm lint && pnpm test

# Frontend
cd frontend    && pnpm lint && pnpm build

# Python
cd scripts     && ruff check . && pytest
```

### 10.4 CI

GitHub Actions runs the four pipelines above on every PR. A PR cannot
merge until all four are green.

---

## 11. Deployment

| Component           | Host                     | Notes                                       |
| ------------------- | ------------------------ | ------------------------------------------- |
| Frontend            | Vercel                   | Project root `frontend/`                    |
| Go API              | Fly.io (or Render)       | Dockerfile at `backend-go/Dockerfile`       |
| Node gateway        | Fly.io (or Render)       | Deploy from `backend-node/`                 |
| Supabase            | Supabase cloud           | Migrations in `backend-go/migrations/*.sql` |
| Processed GeoJSON   | Supabase Storage         | Bucket `processed/`, public read            |

Secrets live in each host's env panel. Never commit `.env`.

### 11.1 Supabase setup

1. Create a Supabase project (ap-south-1 Mumbai for low latency).
2. Enable PostGIS: `create extension if not exists postgis;`
3. Run the schema migration from the SQL Editor (tables above in §6.1).
4. Copy `Project URL`, `anon key`, and `service_role key` into `.env`.

### 11.2 Vercel frontend

1. Import the GitHub repository in Vercel.
2. Set Root Directory to `frontend/`.
3. Add env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
   `NEXT_PUBLIC_API_BASE`.
4. Deploy — Vercel runs `pnpm build` automatically.

---

## 12. Troubleshooting

| Symptom                                                       | Likely cause / fix                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------------- |
| `rasterio.errors.RasterioIOError` on CHIRPS .tif              | GDAL missing or wrong version. Install GDAL 3.6+ before `rasterio`. |
| Map tiles blank, console: `window is not defined`             | Leaflet component imported without `ssr: false`.                    |
| SPI values clamp at ±3.72                                     | Expected — `Hx` is clipped to `[0.0001, 0.9999]`. See script.       |
| Supabase insert fails with `permission denied`                | You're using the `anon` key for writes. Use `service_role`.         |
| Frontend shows 2026 months with no data                       | Pipeline hasn't been re-run for the current month; re-ingest.       |
| CORS error from Next → Go                                     | Set `ALLOWED_ORIGINS=http://localhost:3000` on the Go service.      |
| Record-length warning in SPI output                           | Only ~10 years of CHIRPS used. WMO recommends ≥ 30 years; extend `CALIB_START` once older rasters are added (CHIRPS goes back to 1981). |

---

## 13. Known Limitations

- **SPI uses ~10-year record** (2016-2026), not the WMO-recommended 30 years.
  Extend `CALIB_START` in `config/spi.yaml` once older CHIRPS data is loaded
  (CHIRPS goes back to 1981).
- **NSMI-NDVI collinearity** (r=0.858) — both derive from Sentinel-2 spectral
  bands. The vegetation-only CDI (no rain data) is not fully independent.
  Months with only vegetation inputs are marked `degraded`.
- **VHI = VCI placeholder** — no real LST (Land Surface Temperature) data yet.
  Replace with Landsat/MODIS LST when available.
- **PCI edge values** — ~11% at both 0 and 100 due to the short 10-year record
  for min-max normalization. Will improve as years accumulate.
- **Map uses centroid points**, not full village polygons, for performance.
  Polygon boundaries exist in `frontend/public/data/latur_villages.geojson`.
- **Missing Sentinel years**: 2019 and 2025 have no rasters. The pipeline
  leaves those months as `NaN` and the frontend renders grey "no data" cells.

---

## 14. Roadmap (short)

- [ ] Replace static GeoJSON fetch with Mapbox Vector Tiles for pixel layer
- [ ] Nightly scheduled ingest (GitHub Actions → Go `ingest` CLI)
- [ ] User alerts: email when CDI < −1.5 for any tehsil
- [ ] Switch SPI calibration to 1981 – 2010 once older CHIRPS is loaded
- [ ] Mobile layout for the map + chart dashboard

---

## 15. Contact

Project owner: **rajnandinikadam221@gmail.com**
See `CODE_OF_CONDUCT.md` for community guidelines.
