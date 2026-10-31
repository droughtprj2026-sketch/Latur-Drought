# DEVELOPER.md

**Project:** Real-Time Drought Monitoring — Latur District, Marathwada
**Study period:** 2016 – 2026
**Owner:** rajnandinikadam221@gmail.com

This document is for developers who will build, run, and extend the Latur
Drought Monitoring platform. It covers the full stack: data ingestion
(Sentinel-2 + CHIRPS), index processing (SPI, NDVI, VHI, PCI, EVI → CDI),
the Node.js backend, the Next.js + Leaflet frontend, and the
Supabase + SQLite data layer.

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
   │  • Node.js API (:4000)   — /api/v1/* index + CDI queries │
   │                           — auth, upload, static GeoJSON  │
   └───────────────────────────────────────────────────────────┘
                                   │
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  FRONTEND  (Next.js 14, App Router)                       │
   │  • Leaflet choropleth map (village / tehsil polygons)      │
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
| Backend               | **Node.js 20** (Express) — API, auth, uploads |
| Scripting / science   | **Python 3.11** — rasterio, geopandas, scipy  |
| Database              | SQLite (local) + **Supabase** (Postgres 15 + PostGIS 3.4) |
| Object storage        | Supabase Storage                              |
| Auth                  | Supabase Auth (JWT)                           |
| Deployment            | Vercel (frontend) · Fly.io / Render (Node) · Supabase cloud |

---

## 3. Repository Layout

```
drought-monitoring/
├── README.md
├── DEVELOPER.md           # this file
├── AGENTS.md              # rules for coding agents
├── docker-compose.yml
├── .env.example
│
├── config/
│   ├── composite.yaml     # CDI weights, thresholds, formula_version
│   └── spi.yaml           # SPI reference climatology + QC rules
│
├── scripts/               # Python pipeline
│   ├── chirps_gee.py      # real-time: CHIRPS from GEE
│   ├── pipeline_gee.py    # real-time: Sentinel-2 from GEE
│   ├── spi_from_chirps_csv.py    # real-time: SPI from GEE CHIRPS CSV
│   ├── latur_chirps_spi.py       # batch: SPI from local rasters
│   ├── latur_sentinel_indices.py # batch: indices from local rasters
│   ├── composite_cdi.py          # CDI composite computation
│   ├── build_village_indices.py  # village-level zonal stats + CDI
│   ├── build_baseline_drought.py # baseline anomalies + GeoJSON
│   ├── dashboard_master.py       # builds outputs/Dashboard/
│   ├── scheduler.py              # orchestrates pipeline runs
│   ├── common/
│   │   ├── raster.py      # file scanning, dedupe, read_stack
│   │   ├── classify.py    # SPI/CDI class thresholds
│   │   └── manifest.py    # incremental processing manifest
│   └── requirements.txt
│
├── data/
│   ├── raw/               # DO NOT COMMIT — large rasters
│   ├── vector/            # AOI boundaries
│   │   ├── latur_district.geojson
│   │   ├── latur_tehsils.geojson
│   │   └── latur_villages.geojson  (954 villages)
│   └── processed/         # pipeline outputs
│       ├── csv/           # village/district/tehsil time series
│       ├── geojson/       # per-period village GeoJSON
│       ├── json/          # manifest, district monthly, components
│       └── manifests/     # per-source processing state
│
├── outputs/Dashboard/     # Node API reads from here
│   ├── drought_monitoring_master.csv
│   ├── latest_status.json
│   ├── data_availability.json
│   └── processing_manifest.json
│
├── backend-node/          # API server (Express + SQLite)
└── frontend/              # Next.js 14 + Leaflet + Recharts
```

---

## 4. Prerequisites

Install locally:

- **Node.js 20+** and **pnpm** (`corepack enable`)
- **Python 3.11+** with `pip` and `virtualenv`
- **GDAL 3.6+** (required by `rasterio` / `geopandas`)
- **Docker** (optional, for running Postgres locally)
- A **Supabase project** (free tier is fine); keep the project URL and both
  the `anon` and `service_role` keys ready
- **Google Earth Engine account** (only if you plan to re-download Sentinel-2)

Create a project-root `.env` (never commit it) with:

```env
# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...          # server-side only

# Postgres (direct connection for Supabase writes)
DATABASE_URL=postgres://postgres:<pwd>@db.<project>.supabase.co:5432/postgres?sslmode=require

# Backend
PORT=4000
NEXT_PUBLIC_API_BASE=http://localhost:4000

# Processing
DATA_DIR=./data/raw
OUTPUT_DIR=./data/processed
```

Frontend reads only `NEXT_PUBLIC_*` keys. Service-role keys must stay on
the server (Node) side.

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
| SPI-k  | `latur_chirps_spi.py` (batch), `spi_from_chirps_csv.py` (real-time) | Gamma CDF fit per calendar month (McKee 1993). Zero-rain correction `H = q + (1 − q) · G`, with `H(0) = q/2` (Stagge 2015). SPI = Phi-inv(H). Computed for k = 1, 3, 6, 12. Batch: per-pixel from rasters. Real-time: district-mean from GEE CHIRPS CSV. |
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
python dashboard_master.py          # builds outputs/Dashboard/ files for Node API
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

# 2. Compute SPI from the GEE CHIRPS CSV (district-level, gamma CDF)
python scripts/spi_from_chirps_csv.py

# 3. Pull Sentinel-2 for the AOI (independent cadence)
python scripts/pipeline_gee.py \
    --aoi data/vector/latur_tehsils.geojson \
    --from 2016-01 --to 2026-10

# 4. Village-level zonal stats (builds the CSV composite_cdi reads)
python scripts/build_village_indices.py --stage zonal

# 5. Compute the transparent multi-index composite
python scripts/composite_cdi.py

# 6. Build dashboard master + status files
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
Python and the Node.js backend. The API does not re-read rasters.

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
  index_name  text not null,            -- 'SPI1','SPI3','NDVI','EVI','VCI','VHI','NSMI','PCI','CDI'
  year        int  not null,
  month       int  not null check (month between 1 and 12),
  value       double precision,
  class_label text,
  pct_area_dry double precision,
  unique (index_name, year, month)
);

-- Village-level monthly index values (real-time GEE zonal stats).
-- 954 villages x indices x months. Pushed by pipeline_gee.py and chirps_gee.py.
create table village_monthly_index (
  id          bigserial primary key,
  index_name  text not null,            -- 'ndvi','evi','ndmi','nsmi','rain_mm'
  year        int  not null,
  month       int  not null check (month between 1 and 12),
  village     text not null default '',
  tehsil      text not null default '',
  value       double precision,
  class_label text,
  unique (index_name, year, month, village)
);
create index on village_monthly_index (tehsil, year, month);

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
alter table tehsils                enable row level security;
alter table monthly_index          enable row level security;
alter table village_monthly_index  enable row level security;
alter table pixel_index            enable row level security;

create policy "public read" on monthly_index          for select using (true);
create policy "public read" on village_monthly_index   for select using (true);
create policy "public read" on tehsils                 for select using (true);
create policy "public read" on pixel_index             for select using (true);
-- writes are limited to the service_role key (used only by the ingest job).
```

### 6.3 Loading processed outputs

Use the Node.js API's `/api/v1/admin/ingest` endpoint (service-role JWT
required). The endpoint re-reads `data/processed/` and loads into SQLite.

---

## 7. Backend — Node.js API server

The Node.js API server (Express) exposes the versioned REST API that
the frontend uses. It is intentionally thin: all heavy computation
already happened in Python; the API reads from SQLite (`data/drought.db`)
and `outputs/Dashboard/` JSON files.

### 7.1 Run locally

```bash
cd backend-node
pnpm install
pnpm dev     # → listening on :4000
```

### 7.2 Endpoints

| Method | Path                                             | Returns                                    |
| ------ | ------------------------------------------------ | ------------------------------------------ |
| GET    | `/api/v1/health`                                 | `{"status":"ok"}`                          |
| GET    | `/api/v1/manifest`                               | years + indices available                  |
| GET    | `/api/v1/tehsils`                                | Tehsil polygons (static)                   |
| GET    | `/api/v1/villages`                               | Village list with centroids                |
| GET    | `/api/v1/indices/:name/:year/:month`             | GeoJSON FeatureCollection (choropleth)     |
| GET    | `/api/v1/village-indices/:name/:year/:month`     | Village-level index values                 |
| GET    | `/api/v1/timeseries/:name?from=YYYY-MM&to=YYYY-MM` | `[{date, value, class}]` district mean   |
| GET    | `/api/v1/cdi/:year/:month`                       | CDI GeoJSON + per-tehsil summary           |
| GET    | `/api/v1/status`                                 | `latest_status.json` (header chip)         |
| GET    | `/api/v1/availability`                           | `data_availability.json` (per-source periods) |
| GET    | `/api/v1/master?tehsil=&from=&to=`               | rows from `drought_monitoring_master.csv`  |
| GET    | `/api/v1/latest?tehsil=Latur`                    | most recent validated row for a tehsil     |
| GET    | `/api/v1/compare?index=&a=YYYY-MM&b=YYYY-MM`     | two periods side by side                   |
| GET    | `/api/v1/animation?index=&from=&to=`             | ordered frame list for the player          |
| POST   | `/api/v1/admin/ingest` (service-role JWT)        | triggers re-ingest of `data/processed`     |
| POST   | `/api/v1/admin/aoi`    (service-role JWT)        | upload shapefile/GeoJSON AOI               |

`:name` in {`spi1`, `spi3`, `spi6`, `spi12`, `ndvi`, `evi`, `pci`, `vci`, `vhi`, `nsmi`, `cdi`, `cdi_class`}

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

### 7.3 Example response — `/api/v1/timeseries/spi3?from=2024-01&to=2026-10`

```json
[
  { "date": "2024-01", "value": -0.42, "class": "Near normal",    "pct_area_dry": 12.3 },
  { "date": "2024-02", "value": -1.11, "class": "Moderately dry", "pct_area_dry": 54.7 },
  ...
]
```

### 7.4 Project conventions

- Route handlers in `src/routes/api.ts` are **thin**: parse → query DB → serialize.
- Error envelope: `{"error":{"code":"NOT_FOUND","message":"..."}}`.
- Auth routes in `src/routes/auth.ts`, upload routes in `src/routes/upload.ts`.
- Tests: `pnpm test` (vitest). CI must stay green.

### 7.5 Additional routes

```
POST  /auth/login       → Supabase email + password
POST  /auth/logout
POST  /upload/geojson   (admin) → Supabase Storage bucket `processed/`
```

---

## 8. Frontend — Next.js + Leaflet

```bash
cd frontend
pnpm install
pnpm dev     # → http://localhost:3000
```

### 8.1 Pages

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

### 8.2 Map component (`components/map/LaturMap.tsx`)

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

### 8.3 Charts

- `SPIChart.tsx` — multi-scale bar chart (SPI-1/3/6/12) on one shared
  x-axis; colors come from the same class scale as the map.
- `CDIHeatmap.tsx` — year × month heatmap, D3 color scale.

### 8.4 API wrapper (`lib/api.ts`)

```ts
export async function getManifest()                      { ... }
export async function getIndexGeoJSON(name, year, month) { ... }
export async function getTimeseries(name, from, to)      { ... }
```

All calls go through `NEXT_PUBLIC_API_BASE` so you can point the frontend
at the local Node API or production without rebuild.

---

## 9. Development Workflow

### 9.1 Branching

- `main` — protected, always deployable.
- `feat/<topic>` — feature branches, squash-merged.
- `fix/<topic>` — bug fixes.
- Open a PR early; keep it under ~400 lines of diff where possible.

### 9.2 Commits

Conventional Commits:

```
feat(map): add CDI layer toggle
fix(api): clamp SPI value when gamma fit fails
chore(deps): bump next to 14.2.5
```

### 9.3 Local verification before pushing

```bash
# Backend
cd backend-node && pnpm lint && pnpm test

# Frontend
cd frontend    && pnpm lint && pnpm build

# Python
cd scripts     && ruff check . && pytest
```

### 9.4 CI

GitHub Actions runs the three pipelines above on every PR. A PR cannot
merge until all three are green.

---

## 10. Deployment

| Component           | Host                     | Notes                                       |
| ------------------- | ------------------------ | ------------------------------------------- |
| Frontend            | Vercel                   | Project root `frontend/`                    |
| Node API            | Fly.io (or Render)       | Deploy from `backend-node/`                 |
| Supabase            | Supabase cloud           | Schema in DEVELOPER.md section 6            |
| Processed GeoJSON   | Supabase Storage         | Bucket `processed/`, public read            |

Secrets live in each host's env panel. Never commit `.env`.

### 10.1 Supabase setup

1. Create a Supabase project (ap-south-1 Mumbai for low latency).
2. Enable PostGIS: `create extension if not exists postgis;`
3. Run the schema migration from the SQL Editor (tables above in §6.1).
4. Copy `Project URL`, `anon key`, and `service_role key` into `.env`.

### 10.2 Vercel frontend

1. Import the GitHub repository in Vercel.
2. Set Root Directory to `frontend/`.
3. Add env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
   `NEXT_PUBLIC_API_BASE`.
4. Deploy — Vercel runs `pnpm build` automatically.

---

## 11. Troubleshooting

| Symptom                                                       | Likely cause / fix                                                  |
| ------------------------------------------------------------- | ------------------------------------------------------------------- |
| `rasterio.errors.RasterioIOError` on CHIRPS .tif              | GDAL missing or wrong version. Install GDAL 3.6+ before `rasterio`. |
| Map tiles blank, console: `window is not defined`             | Leaflet component imported without `ssr: false`.                    |
| SPI values clamp at ±3.72                                     | Expected — `Hx` is clipped to `[0.0001, 0.9999]`. See script.       |
| Supabase insert fails with `permission denied`                | You're using the `anon` key for writes. Use `service_role`.         |
| Frontend shows 2026 months with no data                       | Pipeline hasn't been re-run for the current month; re-ingest.       |
| CORS error from Next → API                                    | Set `ALLOWED_ORIGINS=http://localhost:3000` on the Node API.        |
| Record-length warning in SPI output                           | Only ~10 years of CHIRPS used. WMO recommends ≥ 30 years; extend `CALIB_START` once older rasters are added (CHIRPS goes back to 1981). |

---

## 12. Known Limitations

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

## 13. Roadmap (short)

- [ ] Replace static GeoJSON fetch with Mapbox Vector Tiles for pixel layer
- [ ] Nightly scheduled ingest (GitHub Actions → `scheduler.py`)
- [ ] User alerts: email when CDI < −1.5 for any tehsil
- [ ] Switch SPI calibration to 1981 – 2010 once older CHIRPS is loaded
- [ ] Mobile layout for the map + chart dashboard

---

## 14. Contact

Project owner: **rajnandinikadam221@gmail.com**
