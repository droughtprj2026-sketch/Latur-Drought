# Running the Pipelines

The repository is organized into two dedicated pipelines:
- **`historical/`**: 10-year climatological baseline, raster calibration, and historical validation.
- **`realtime/`**: Near-real-time GEE satellite ingestion, pre-flight safety testing, and automated dashboard updates.

---

## 1. Near-Real-Time Pipeline (`realtime/`)

### Quick Run
```bash
# Run unit & pre-integration safety tests
python realtime/test_realtime_pipeline.py

# Run live end-to-end ingestion and atomic dashboard JSON update
python realtime/orchestrator.py

# Run for a specific period
python realtime/orchestrator.py --period 2026-10

# Test run without touching disk
python realtime/orchestrator.py --dry-run
```

### Background Daemon / Cron Scheduler
```bash
# Start background daemon running every 6 hours
python realtime/scheduler.py --daemon --interval-hours 6

# Or run one-shot scheduled cycle
python realtime/scheduler.py --once
```

---

## 2. Historical Baseline Pipeline (`historical/`)

```bash
# 1. Pull CHIRPS monthly & calculate SPI-1/3/6/12
python historical/latur_chirps_spi.py

# 2. Compute Sentinel-2 vegetation indices
python historical/latur_sentinel_indices.py

# 3. Transparent multi-index composite CDI fusion
python historical/composite_cdi.py

# 4. Generate master dataset and historical dashboard status
python historical/dashboard_master.py

# 5. Run historical validation against government disaster declarations
python historical/validate_historical_analysis.py
```

---

## 3. Web Dashboard

```bash
cd frontend && pnpm dev   # http://localhost:3000
```

---

## 4. Configuration

Edit `config/composite.yaml` to adjust CDI component weights or thresholds:

```yaml
weights:
  SPI:  0.30
  VHI:  0.20
  VCI:  0.15
  NDVI: 0.15
  EVI:  0.10
  PCI:  0.10
```
