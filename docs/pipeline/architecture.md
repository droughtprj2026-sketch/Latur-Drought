# Dual Engine Pipeline Architecture

The platform architecture decouples long-term historical baseline synthesis from weekly operational near real-time updates.

```
+-------------------------------------------------------------------------------------------------+
|                                 DUAL ENGINE ARCHITECTURE OVERVIEW                                |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   HISTORICAL BASELINE ENGINE (11-Year Calibration)       REAL-TIME WEEKLY ENGINE (Automation)   |
|   -------------------------------------------------       -----------------------------------    |
|   * Period: 2016-01 to 2026-10                            * Schedule: Weekly Cron / Automation   |
|   * Computes multi-year min, max, mean, std               * Scans manifests/sentinel.json        |
|   * Generates baseline_NDVI, baseline_VCI, etc.           * Processes only new / affected periods|
|   * Produces village_with_baseline.csv (124k rows)        * Triggers rolling SPI recalculation   |
|   * Backs all scientific atlas figures & animations       * Updates outputs/Dashboard/ & Supabase|
|                                                                                                 |
+-------------------------------------------------------------------------------------------------+
```

---

## 1. Engine 1: Historical Baseline Engine

The historical engine (`scripts/historical/build_village_indices.py` and `scripts/historical/composite_cdi.py`):
1. **Zonal Statistics Extraction:** Iterates through all historical monthly rasters (Sentinel-2, Sentinel-1, Landsat, CHIRPS) and computes exact zonal means across 954 village boundary polygons.
2. **Climatological Baseline Calibration:** For each village $v$ and calendar month $m \in \{1, \dots, 12\}$, computes:
   - $\text{NDVI}_{\min}(v, m)$, $\text{NDVI}_{\max}(v, m)$, $\overline{\text{NDVI}}(v, m)$, $\sigma_{\text{NDVI}}(v, m)$
   - $\text{Rain}_{\min}(v, m)$, $\text{Rain}_{\max}(v, m)$, $\overline{\text{Rain}}(v, m)$
   - Multi-year VCI, NSMI, and SPI distributions.
3. **Master Analytical Panel:** Writes the unified panel dataset `data/processed/csv/village_with_baseline.csv` (124,020 rows × 39 columns).

---

## 2. Engine 2: Operational Real-Time Weekly Pipeline

The operational weekly engine (`scripts/realtime/realtime_update.py`):
1. **Incremental Manifest Check:** Reads `manifests/sentinel.json` and `manifests/chirps.json`.
2. **Targeted Ingestion:** Identifies newly arrived periods without reprocessing historical years.
3. **Rolling SPI Window Retriggering:** When a new monthly CHIRPS rainfall raster is registered, the pipeline automatically retriggers every rolling SPI window that encompasses it (SPI-1, SPI-3, SPI-6, SPI-12).
4. **Dashboard Data Bridge:** Exports the latest monitoring payload to `outputs/Dashboard/`:
   - `latest_status.json`: Real-time system health, latest valid observation period, and tehsil status.
   - `drought_monitoring_master.csv`: Updated master time series for the web app.
   - `data_availability.json`: System audit ledger.
   - `processing_manifest.json`: Step execution audit log.
5. **Supabase Publishing Step:** Publishes updated rows to Supabase PostgreSQL using the server-side `service_role` key and updates the public storage bucket.

---

## 3. Strict Incremental Processing Rules

1. **No Cold Restarts:** Pipeline runs never wipe or reprocess historical years unless explicitly instructed with `--rebuild-all`.
2. **Degraded Status Flagging:** If the latest available observation date is older than today, the status chip is set to `"degraded"` and the dashboard displays the actual observation date. Real-time is never falsely claimed when sensor latency causes delay.
3. **Immutability of Historical Outputs:** Committed historical tables under `output/` and `data/` remain untouched during weekly runs.
