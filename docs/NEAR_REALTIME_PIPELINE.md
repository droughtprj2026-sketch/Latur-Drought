# Near-Real-Time Pipeline Architecture
**Google Earth Engine (GEE) + PostGIS + Vercel Serverless**  
**Sensors:** Copernicus Sentinel-2 L2A (10 m) + UCSB CHIRPS v2.0 (~5 km) + MODIS Terra LST (1 km)  
**Execution Runtime:** Python 3.11 / GitHub Actions / Vercel Edge  

---

## 1. Pipeline Architecture Overview

```
 ┌──────────────────────────────────────────────────────────────┐
 │         EARTH OBSERVATION DATA INGESTION (CLOUD)             │
 │  • Sentinel-2 MSI L2A: COPERNICUS/S2_SR_HARMONIZED (10 m)    │
 │  • UCSB CHIRPS Precip: UCSB-CHG/CHIRPS/monthly     (~5 km)   │
 │  • MODIS Terra LST:    MODIS/061/MOD11A1           (1 km)    │
 └──────────────────────────────────────────────────────────────┘
                               │
                               ▼
 ┌──────────────────────────────────────────────────────────────┐
 │             GOOGLE EARTH ENGINE CLOUD COMPUTATION            │
 │  • Cloud Masking: SCL scene classification + s2cloudless     │
 │  • Spectral Indices: NDVI, EVI, NDMI, VCI, VHI, PCI          │
 │  • Gamma Distribution SPI Fitting: SPI-1, 3, 6, 12           │
 │  • Multi-Index CDI Fusion: 0.30·SPI + 0.20·VHI + 0.15·VCI... │
 │  • Zonal Statistics: reduceRegions() over 951 Village Polygons│
 └──────────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
 ┌─────────────────────────────┐ ┌──────────────────────────────┐
 │   GEE TILE SERVICE (CDN)    │ │   SUPABASE POSTGIS STORAGE   │
 │  img.getMapId() tile URLs   │ │   Outputs: Master CSV & JSON │
 │  Rendered directly on       │ │   PostGIS monthly_index table│
 │  Leaflet without custom GIS │ │   Public frontend assets in  │
 │  servers                    │ │   frontend/public/data/      │
 └─────────────────────────────┘ └──────────────────────────────┘
                               │
                               ▼
 ┌──────────────────────────────────────────────────────────────┐
 │         VERCEL HOSTING & NEXT.JS APP ROUTER FRONTEND         │
 │  • Standalone Next.js API Routes: app/api/v1/[...slug]/      │
 │  • Google Terrain Basemaps & Leaflet Vector Polygons         │
 │  • Real-Time Interactive Timeline Scrubber (2016–2026)      │
 │  • Permanent Sidebar, Comparison Curtain & Animation Player  │
 └──────────────────────────────────────────────────────────────┘
```

---

## 2. Decoupled Cloud Credentials & GitHub Secrets

In compliance with enterprise security requirements, **zero secrets or project identifiers are hardcoded into scripts**:

### Required Environment Variables:
- `GEE_PROJECT`: Google Earth Engine Cloud Project ID (e.g. your Google Cloud project identifier).
- `GEE_PROJECT_NUMBER`: Numeric project identifier for service account bindings.
- `DATABASE_URL`: Direct PostgreSQL connection string to Supabase PostGIS.
- `SUPABASE_URL`: Supabase project URL (`https://<project-id>.supabase.co`).
- `SUPABASE_SERVICE_ROLE_KEY`: Server-side service key for database and storage writes.

### Adding as GitHub Secrets:
1. Navigate to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Add `GEE_PROJECT`, `DATABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`.
3. GitHub Actions automated workflow (`.github/workflows/drought_pipeline.yml`) runs the ingestion on a scheduled cron or on-demand without exposing credentials.

---

## 3. Band Processing & Index Calculations

### 3.1 Sentinel-2 Cloud Masking
Cloud and shadow contamination is masked using the 10 m Scene Classification Layer (SCL):
- **Masked Pixel Codes**: `3` (Cloud Shadow), `8` (Cloud Medium Probability), `9` (Cloud High Probability), `10` (Cirrus), `11` (Snow/Ice).
- **Composite Method**: Monthly medoid / median reducer across cloud-free pixels.

### 3.2 Spectral Formulas
- **NDVI** (Normalized Difference Vegetation Index):
  $$\text{NDVI} = \frac{B_8 - B_4}{B_8 + B_4}$$
- **EVI** (Enhanced Vegetation Index — atmospheric blue correction):
  $$\text{EVI} = 2.5 \times \frac{B_8 - B_4}{B_8 + 6.0 \cdot B_4 - 7.5 \cdot B_2 + 1.0}$$
- **NDMI** (Normalized Difference Moisture Index — canopy water content):
  $$\text{NDMI} = \frac{B_8 - B_{11}}{B_8 + B_{11}}$$
- **VCI** (Vegetation Condition Index — Kogan 1995):
  $$\text{VCI} = 100 \times \frac{\text{NDVI} - \text{NDVI}_{\min}}{\text{NDVI}_{\max} - \text{NDVI}_{\min}}$$
- **VHI** (Vegetation Health Index):
  $$\text{VHI} = 0.5 \times \text{VCI} + 0.5 \times \text{TCI}$$

---

## 4. Serverless Vector & Tile Rendering on Vercel

Because the platform is deployed on **Vercel**, traditional heavy spatial servers (such as GeoServer or standalone GIS daemons) are not needed:
1. **Cadastral Vector Polygons**: Verified Survey of India village polygons are stored as optimized GeoJSON in `public/data/latur_villages_latest.geojson`.
2. **Dynamic In-Browser Styling**: Leaflet applies WMO SPI and CDI color scales client-side in sub-milliseconds based on the active timeline scrubber period.
3. **GEE Live Tiles**: When full-resolution raster layers are requested, GEE returns a signed tile URL template (`https://earthengine.googleapis.com/v1/{mapid}/tiles/{z}/{x}/{y}`) which Leaflet mounts directly as a raster `TileLayer`.
4. **Edge API Route**: Next.js App Router route handler at `app/api/v1/[...slug]/route.ts` handles all `/api/v1` calls serverlessly on Vercel with zero cold-start delay.
