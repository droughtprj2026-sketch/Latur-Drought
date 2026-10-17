# Running the near-real-time pipeline

```bash
# 0. One-time setup
earthengine authenticate                              # once per machine
cp .env.example .env                                  # fill in Supabase keys

# 1. Pull CHIRPS monthly (incremental)
python scripts/chirps_gee.py --from 2016-01 --to latest

# 2. Recompute SPI only for the months CHIRPS marked stale
python scripts/latur_chirps_spi.py

# 3. Pull Sentinel-2 for the chosen AOI (independent cadence)
python scripts/pipeline_gee.py \
    --aoi data/vector/latur_tehsils.geojson \
    --from 2016-01 --to 2026-10

# 4. Compute the transparent multi-index composite (replaces the old RF step)
python scripts/composite_cdi.py

# 5. Build the dashboard master + status files
python scripts/dashboard_master.py

# Or do steps 1–5 incrementally in one tick:
python scripts/scheduler.py
```

Start the stack:

```bash
docker compose up                 # Postgres + Go API + Node gateway
cd frontend && pnpm install && pnpm dev          # http://localhost:3000
```

## Changing the composite without touching code

Edit `config/composite.yaml`:

```yaml
weights:
  SPI:  0.30
  VHI:  0.20
  VCI:  0.15
  NDVI: 0.15
  EVI:  0.10
  PCI:  0.10
```

Then re-run `python scripts/composite_cdi.py && python scripts/dashboard_master.py`.
`composite_formula_version` is stamped on every row so classifications
remain traceable to the config that produced them.

## Testing matrix

| Scenario                                     | Expected behavior                                      |
| -------------------------------------------- | ------------------------------------------------------ |
| New CHIRPS daily rainfall observation        | Affected month + its SPI windows recomputed            |
| New Sentinel-2 scene                         | Only that period's NDVI/EVI/VCI/VHI recomputed         |
| CHIRPS updates, Sentinel-2 does not          | SPI refreshes; vegetation indices unchanged            |
| Sentinel-2 updates, CHIRPS does not          | Vegetation indices refresh; SPI stays as last valid    |
| Incomplete month gets more rainfall          | Month + all affected rolling SPI recomputed            |
| SPI cannot be calculated (insufficient data) | Row written with empty `SPI_*`; composite re-weights   |
| < `min_inputs` composite components available| Row written; class = `pending`; CDI empty              |
| Processing fails mid-run                     | Last validated master stays published                  |
| Historical request (year=2020)               | Stored results returned; no recomputation              |
| Latest request                               | Returns most recent `data_quality_status=success` row  |
| Composite weights changed in YAML            | Next run produces new rows stamped with new formula_version |
| User-uploaded AOI                            | Pipeline runs against the uploaded polygons            |
