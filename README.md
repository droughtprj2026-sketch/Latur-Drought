# Real-Time Drought Monitoring — Latur District, Marathwada

A full-stack platform that turns Sentinel-2 and CHIRPS rasters (2016 – 2026)
into actionable drought information. Computes SPI, NDVI, EVI, PCI, VHI
and a composite CDI; serves them through a Go API; renders them on a
Leaflet map and Recharts time series in a Next.js dashboard.

## Stack

| Layer       | Technology                              |
| ----------- | --------------------------------------- |
| Processing  | Python 3.11 (rasterio, geopandas, scipy) |
| Backend     | **Go 1.22** (chi, pgx) + Node 20 gateway |
| Database    | **Supabase** (Postgres 15 + PostGIS 3.4) |
| Frontend    | Next.js 14 + Leaflet + Recharts + Tailwind |

## Quick start

```bash
cp .env.example .env         # fill in Supabase keys
docker compose up            # starts Go API, Node gateway, local Postgres
cd frontend && pnpm install && pnpm dev     # http://localhost:3000
```

To re-run processing (requires raw rasters under `data/raw/`):

```bash
cd scripts
pip install -r requirements.txt
python latur_chirps_spi.py
python latur_sentinel_indices.py
python latur_cdi.py
```

## Migration note (Oct 2026)

The Random Forest classifier has been **retired**. The final drought
class is now produced by a transparent weighted multi-index composite
(see `config/composite.yaml`). No learned model is loaded at runtime,
and the master table no longer carries `rf_*` columns.

## Documentation

- `AGENTS.md` — rules of the road for coding agents (Antigravity, OpenCode, …)
- `DEVELOPER.md` — full architecture, API reference, deployment
- `CODE_OF_CONDUCT.md` — community guidelines + scientific integrity clause
- `RUN.md` — end-to-end run guide + test matrix

## License

TBD. Data derived from CHIRPS (UCSB CHG), Sentinel-2 (Copernicus, ESA),
Google Earth Engine. Credit upstream providers in any publication.
