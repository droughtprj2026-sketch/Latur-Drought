# Latur Real-Time Drought Monitoring — Supabase & Vercel Deployment Guide

This guide details the complete deployment architecture for the **Latur Real-Time Drought Monitoring System (2016–2026)**, upgrading the database to **Supabase (PostgreSQL + PostGIS)** and deploying the web application on **Vercel** with **GitHub** as the source repository.

---

## 1. Current Project State & Data Verification

| Dataset / Index | Status | Scope | Details |
| :--- | :--- | :--- | :--- |
| **CHIRPS SPI (1, 3, 6, 12)** | **Verified & Computed** | District, 10 Tehsils, 954 Villages (2016–2026) | 121,728 tidy monthly observations loaded into SQLite (`drought.db`) and CSV. |
| **Precipitation (CHIRPS)** | **Verified & Computed** | All Tehsils & Villages | Real rainfall in mm per month across all 11 years. |
| **Sentinel-2 Indices (NDVI, EVI, NDMI)** | **Pending Execution** | 114 GeoTIFF scenes in `output/sentinel/` | Unverified mock data has been completely purged. Zonal pipeline ready in `scripts/process_sentinel_zonal.py`. |
| **Condition Indices (VCI, VHI, PCI)** | **Pending Sentinel Run** | All Tehsils & Villages | Calculated from climatological baseline once Sentinel zonal means are computed. |
| **Composite Drought Index (CDI)** | **Pending Inputs (min: 3)** | All Tehsils & Villages | Classified per `config/composite.yaml` once Sentinel indices are fused with SPI. |

> [!NOTE]
> All unverified synthetic numbers have been purged from `drought_monitoring_master.csv`, `drought.db`, and `latest_status.json`. The frontend displays **"Pending Sentinel Ingest"** with grey no-data cells for uncomputed layers, strictly following project integrity rules.

---

## 2. Upgrading Database to Supabase (PostgreSQL + PostGIS)

### Step 2.1: Create Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and log in.
2. Click **"New Project"**, select your region (e.g., `ap-south-1` Mumbai for low latency to Maharashtra).
3. Set your database password and wait ~1 minute for provisioning.

### Step 2.2: Run PostGIS Schema Migration
1. In the Supabase Dashboard, open the **SQL Editor** (terminal icon on left sidebar).
2. Open the file [`supabase_setup.sql`](file:///D:/Droughtprj@2026/supabase_setup.sql) located at the root of your workspace.
3. Paste the contents into the Supabase SQL Editor and click **"Run"**.
   - This activates the `postgis` extension.
   - Creates tables: `tehsils`, `villages`, `monthly_index`, `village_spi`, `master_row`, and `processing_manifest`.
   - Configures spatial `GIST` indexes on geometries and B-tree indexes for fast querying.
   - Configures Row Level Security (RLS) with public read access for the Next.js frontend.

### Step 2.3: Seed Verified Data into Supabase
1. In the SQL Editor, paste and run the contents of [`supabase/seed_data.sql`](file:///d:/Droughtprj@2026/drought-monitoring%20(1)/drought-monitoring/supabase/seed_data.sql).
   - This seeds the 10 Tehsil boundaries with PostGIS geometries.
   - Seeds the 954 revenue village boundaries with PostGIS geometries.
   - Seeds verified CHIRPS district and tehsil monthly SPI records.
2. To regenerate or export additional records from the local SQLite database at any time:
   ```bash
   python scripts/export_for_supabase.py
   ```

### Step 2.4: Retrieve API Keys
Go to **Project Settings** → **API**:
- **Project URL**: `https://<your-project-id>.supabase.co`
- **anon public key**: `eyJhbGciOi...` (Safe for frontend)
- **service_role secret key**: `eyJhbGciOi...` (For server/pipeline writes only)

---

## 3. GitHub Repository Setup

1. Check that `.gitignore` prevents rasters and credentials from being committed:
   - `data/raw/`
   - `output/sentinel/`
   - `.env` and `.env.local`
2. Initialize git and commit:
   ```bash
   git init
   git add .
   git commit -m "feat: verified SPI pipeline, clean database seeder, Supabase schema and Next.js frontend"
   ```
3. Create a repository on GitHub (e.g., `github.com/<your-username>/latur-drought-monitoring`).
4. Push code:
   ```bash
   git remote add origin https://github.com/<your-username>/latur-drought-monitoring.git
   git branch -M main
   git push -u origin main
   ```

---

## 4. Frontend Deployment on Vercel

The frontend is a **Next.js 14 App Router** application with dynamic Leaflet imports (`ssr: false`) and Recharts.

### Step 4.1: Import Project in Vercel
1. Go to [https://vercel.com](https://vercel.com) and log in with GitHub.
2. Click **"Add New..."** → **"Project"**.
3. Select your GitHub repository `latur-drought-monitoring`.
4. Set **Root Directory** to: `drought-monitoring (1)/drought-monitoring/frontend` (or `frontend` if organized as root).

### Step 4.2: Configure Environment Variables in Vercel
Add the following environment variables in the Vercel project settings:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase Project URL | `https://xyzproject.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Public Anonymous Key | `eyJhbGciOi...` |
| `NEXT_PUBLIC_API_BASE` | URL of backend API server | `https://api.yourserver.com` or empty |

### Step 4.3: Deploy
1. Click **"Deploy"**.
2. Vercel will run `npm run build` and provision the edge static assets and serverless functions.
3. Once deployed, your dashboard will be live at `https://<your-project>.vercel.app`.

---

## 5. Running the Sentinel-2 Zonal Processing Pipeline

When ready to compute Sentinel-2 vegetation and moisture indices (NDVI, EVI, NDMI, VCI, VHI, CDI), run either locally or on Google Colab:

### Option A: Local Execution (Batch Mode)
```bash
cd "drought-monitoring (1)/drought-monitoring"
python scripts/process_sentinel_zonal.py --sentinel-dir "D:/Droughtprj@2026/output/sentinel" --out-dir "D:/Droughtprj@2026/output/indices/zonal"
```
*Tip: Use `--max-scenes 5` to test run a subset of scenes first.*

### Option B: Google Colab Execution (Free High-RAM / GPU)
1. Upload your Sentinel rasters to Google Drive under a folder named `sentinel/`.
2. Open a new Google Colab notebook and mount Drive:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   !pip install rasterio shapely pyproj geopandas tqdm
   ```
3. Upload [`scripts/colab_sentinel_pipeline.py`](file:///d:/Droughtprj@2026/drought-monitoring%20%281%29/drought-monitoring/scripts/colab_sentinel_pipeline.py), `latur_tehsils.geojson`, and `latur_villages.geojson`.
4. Run:
   ```python
   !python colab_sentinel_pipeline.py --sentinel-dir "/content/drive/MyDrive/sentinel" --out-dir "/content/drive/MyDrive/output_zonal"
   ```
5. Once finished, run `python scripts/initialize_database.py` to ingest the computed indices into Supabase/SQLite.
