# Near-Real-Time Ingestion, Testing & Dashboard Sync Engine

This directory contains the operational, near-real-time ingestion and update pipeline for the Latur Drought Monitoring Platform.

---

## 1. Directory Structure

```
realtime/
├── orchestrator.py            ← Pipeline coordinator (ingests, tests, updates JSONs)
├── scheduler.py               ← Cron scheduler daemon (--daemon or --once)
├── zonal_analyzer.py          ← 954-village zonal stats and CDI classifier
├── qc_validator.py            ← Pre-integration quality control test suite
├── gee_fetcher.py             ← Google Earth Engine interface (Sentinel-2 + CHIRPS)
├── json_updater.py            ← Authoritative atomic updater for dashboard JSON files
├── test_realtime_pipeline.py  ← Automated pre-integration test runner
└── README.md                  ← Pipeline documentation (this file)
```

---

## 2. Safety & Zero-Downtime Guarantee

Before any new observation is integrated into the dashboard, `qc_validator.py` executes **Pre-Integration Quality Control Tests**:
- **Physical Bounds**: Verifies $0.0 \le \text{CDI} \le 1.0$, $-0.2 \le \text{NDVI} \le 1.0$, $0 \le \text{VCI} \le 100$.
- **Class Validity**: Enforces strict statutory classes (`None`, `D0`, `D1`, `D2`, `D3`, `D4`).
- **Spatial Completeness**: Rejects partial data if village count $< 900$.
- **Atomic Swap**: Writes to temporary `.tmp` buffers first. If any test fails, the process aborts immediately, keeping existing dashboard JSONs intact.

---

## 3. Usage & CLI Commands

### Run Pre-Integration Tests
```bash
python realtime/test_realtime_pipeline.py
```

### Run a Single Real-Time Ingestion Pass
```bash
python realtime/orchestrator.py
# Or for a specific observation period:
python realtime/orchestrator.py --period 2026-10
```

### Dry Run (Validates tests and GEE connections without modifying dashboard JSONs)
```bash
python realtime/orchestrator.py --dry-run
```

### Launch as a Standing Cron Scheduler Daemon
```bash
# Runs every 6 hours in the background
python realtime/scheduler.py --daemon --interval-hours 6
```

---

## 4. Dashboard Artifacts Updated

When a cycle completes successfully, the following files are atomically refreshed:
- `frontend/public/data/latest_status.json`
- `frontend/public/data/village_latest.json`
- `frontend/public/data/village_timeseries.json`
- `frontend/public/data/district_monthly.json`
- `frontend/public/data/data_availability.json`
- `outputs/Dashboard/drought_monitoring_master.csv`
- `outputs/Dashboard/scheduler_status.json`
