# Dashboard Architecture & Dissemination

The user-facing monitoring system is implemented as a modern full-stack web application built on **Next.js**, **Leaflet**, and **Supabase**.

```mermaid
graph TD
    subgraph Storage ["Cloud Infrastructure (Supabase)"]
        PG["PostgreSQL Database<br/>(Master drought rows & time series)"]
        Bucket["Public Storage Bucket<br/>(GeoJSON boundaries & status JSONs)"]
    end

    subgraph Pipeline ["Python Pipeline Engine"]
        WeeklyJob["Weekly Cron / Pipeline Ingest"] -->|outputs/Dashboard/| Bridge["publish_supabase.py"]
        Bridge -->|service_role Key| PG
        Bridge -->|Storage API| Bucket
    end

    subgraph Frontend ["Next.js App Router (frontend/)"]
        APIRoutes["Next.js API Routes<br/>(Edge & Server Runtime)"] --> PG
        APIRoutes --> Bucket
        
        Client["React Client Components"]
        Client -->|Dynamic Import (ssr: false)| LeafletMap["Leaflet Interactive Vector Map<br/>(954 Village Choropleth)"]
        Client --> Recharts["Recharts Time-Series Charts<br/>(11-Year Evolution)"]
    end
```

---

## 1. Key System Components

### 1.1 Python-to-Dashboard Bridge (`outputs/Dashboard/`)
The Python pipeline exports 4 canonical files to `outputs/Dashboard/`:
1. `drought_monitoring_master.csv`: Comprehensive master time series of all indices across 954 villages.
2. `latest_status.json`: High-level operational status, current period, degraded flag, and tehsil summary.
3. `data_availability.json`: Ingestion audit ledger.
4. `processing_manifest.json`: Execution run metadata.

### 1.2 Supabase Publishing (`scripts/realtime/publish_supabase.py`)
- **Server-Side Security:** All writes to Supabase execute server-side using the restricted `service_role` key. The browser client is strictly restricted to read-only access with an anonymous public key.
- **Transactional Row Upsert:** New village-months are upserted with conflict resolution on `(village_idx, period)`.

### 1.3 Next.js Frontend (`frontend/`)
- **Dynamic Leaflet Import:** In compliance with Next.js SSR architecture, Leaflet map components are loaded dynamically with `{ ssr: false }` to prevent `window is not defined` errors.
- **Sub-Second Village Highlighting:** Village polygons are rendered via GeoJSON vector tiles with hairline boundaries, interactive hover tooltips, and click-to-filter drilldowns.
- **Recharts Temporal Visualizer:** Synchronized charts plot multi-year trends, rainfall deviations, and drought class transitions for any selected village or tehsil.

