# Near-Real-Time Ingestion, Testing & Dashboard Sync Engine

This directory contains the operational, near-real-time satellite ingestion, safety testing, and automated dashboard synchronization pipeline for the Latur Drought Monitoring Platform.

---

## 1. Directory Structure

```
realtime/
├── orchestrator.py            ← 5-step pipeline coordinator (ingest, zonal, QC, atomic update, verify)
├── scheduler.py               ← Cron scheduler daemon (--daemon, --once, or --overpass-info)
├── zonal_analyzer.py          ← 954-village zonal statistics and multi-index CDI classification
├── qc_validator.py            ← Pre-integration quality control test suite
├── gee_fetcher.py             ← Google Earth Engine interface (Sentinel-2 MSI + CHIRPS)
├── json_updater.py            ← Atomic updater and mirror for dashboard JSONs and master CSV
├── test_realtime_pipeline.py  ← Automated pre-integration test runner (6 unit/integration tests)
└── README.md                  ← Real-time documentation (this file)
```

---

## 2. Sentinel-2 Overpass Timetable & Synchronization Window

The near-real-time pipeline is calibrated to the precise orbital physics of the Copernicus Sentinel-2 constellation over Latur District, Maharashtra:

| Parameter | Value |
| :--- | :--- |
| **Target Region** | Latur District, Maharashtra ($17.8^\circ\text{N} - 18.8^\circ\text{N}, 76.4^\circ\text{E} - 77.3^\circ\text{E}$) |
| **Satellites** | Sentinel-2A & Sentinel-2B (phased 180° apart) |
| **Sensor** | MSI (Multi-Spectral Instrument, 10 m / 20 m resolution) |
| **Orbit Type** | Sun-synchronous orbit, descending node, 786 km altitude |
| **Equatorial Crossing** | 10:30 AM Mean Local Solar Time |
| **Latur Overpass Time** | **10:54 AM IST (05:24 UTC)** $\pm 10$ minutes (window: 10:45 AM – 11:05 AM IST) |
| **Relative Orbits (Tracks)**| **R062** (main overpass) & **R105** (western swath overlap) |
| **Revisit Cadence** | ~2.5 to 5 days over Latur (swath overlap provides high repeat frequency) |
| **Primary Overpass Days** | **Mondays & Thursdays** (highest coverage clusters) |
| **Downlink & GEE Lag** | 6 to 12 hours post-acquisition (available in Earth Engine by ~21:00 UTC / 02:30 AM IST) |
| **Optimal Ingestion Sync** | **03:00 UTC (08:30 AM IST)** on **Mondays & Thursdays** |

---

## 3. Safety & Pre-Integration Testing

To guarantee the dashboard **never breaks** or displays corrupt data during live ingestion, every execution must pass `qc_validator.py` and `test_realtime_pipeline.py`:

1. **Physical Bounds**:
   - Combined Drought Index: $0.0 \le \text{CDI} \le 1.0$
   - Normalized Difference Vegetation Index: $-0.2 \le \text{NDVI} \le 1.0$
   - Vegetation Condition Index: $0.0 \le \text{VCI} \le 100.0$
2. **Statutory Classification Taxonomy**:
   - Enforces strict statutory classes according to the Manual for Drought Management (2016): `None` (Normal), `D0` (Mild), `D1` (Moderate), `D2` (Severe), `D3` (Extreme), `D4` (Exceptional).
3. **Spatial Completeness**:
   - Rejects the entire run if village count falls below 900 (out of 954) or missing data exceeds 5%.
4. **Atomic Buffer Swaps**:
   - All files are staged in `.tmp` buffers first. If any step or test fails, the process aborts immediately, leaving live production files intact.

---

## 4. Usage & CLI Commands

### View Satellite Overpass Schedule
```bash
python realtime/scheduler.py --overpass-info
```

### Run Automated Pre-Integration Tests
```bash
python realtime/test_realtime_pipeline.py
```

### Execute a Live Real-Time Ingestion Pass
```bash
# Ingests current period, runs tests, and updates all dashboard feeds:
python realtime/orchestrator.py

# Or target a specific observation period (YYYY-MM):
python realtime/orchestrator.py --period 2026-10
```

### Dry Run (Test execution without writing to disk)
```bash
python realtime/orchestrator.py --dry-run
```

### Run Standing Cron Daemon
```bash
# Runs every 6 hours continuously in the background
python realtime/scheduler.py --daemon --interval-hours 6
```

---

## 5. Dashboard Data Feeds Updated

Every successful real-time run automatically updates and mirrors these feeds to both `frontend/public/data/` and `outputs/Dashboard/`:

| File | Purpose |
| :--- | :--- |
| **`latest_status.json`** | District-wide KPI header cards, status chip, and affected village counts |
| **`village_latest.json`** | Village choropleth map layer with latest CDI, VCI, NDVI, and drought class |
| **`village_timeseries.json`**| Village modal dialog multi-year time-series charts |
| **`district_monthly.json`** | District aggregate historical vs. real-time monthly trendlines |
| **`data_availability.json`**| Timeline scrubber registry of valid observation periods |
| **`drought_monitoring_master.csv`**| Append-only canonical observation table (31 standard columns) |
| **`scheduler_status.json`** | Daemon heartbeat status and next scheduled cycle timestamp |

---

## 6. GitHub Actions Automation

The workflow at `.github/workflows/realtime_drought_sync.yml` is scheduled:
```yaml
on:
  schedule:
    - cron: '0 3 * * 1,4'  # Mondays & Thursdays at 03:00 UTC (08:30 AM IST)
```
It automatically executes pre-integration tests, runs the orchestrator, and commits refreshed JSON files directly to GitHub.
