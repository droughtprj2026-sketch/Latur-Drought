# Known Limitations & Error Recovery

This document transparently documents known scientific constraints, sensor latency boundaries, and error recovery protocols.

---

## 1. Scientific & Observational Limitations

### 1.1 Tropical Monsoon Cloud Occlusion
- **Constraint:** During the active southwest monsoon (July–August), dense stratiform and cumulonimbus cloud decks persistently occlude optical sensors.
- **Mitigation:** The system fuses Sentinel-1 SAR microwave backscatter (all-weather penetrative capability) and CHIRPS precipitation grids. When optical indices are masked, CDI dynamically drops VCI and re-weights to SPI and SAR soil moisture.

### 1.2 Missing Archive Years (2019 & 2025)
- **Constraint:** Historical raw Sentinel-2 raster batches for 2019 and 2025 were missing from the upstream GEE Colab archive export.
- **Handling Rule:** Rather than synthesizing or imputing data (which would introduce scientific fraud), the pipeline leaves these optical periods as `NaN`. CDI is computed from rainfall and soil moisture alone. The frontend renders them as grey "No Data" cells—never zero.

### 1.3 Sensor Revisit Latency vs Real-Time Claims
- **Rule:** **Never claim real-time when source latency prevents it.**
- **Policy:** Ingestion from Copernicus and UCSB CHIRPS typically incurs a 3- to 7-day latency. If the latest observation date is older than today, the dashboard status chip displays `"degraded"` and explicitly shows the actual observation timestamp.

### 1.4 Spatial Resolution Heterogeneity
- **Constraint:** Optical Sentinel-2 ($10\text{--}20\text{ m}$) and SAR Sentinel-1 ($10\text{ m}$) possess fine spatial granularity, whereas CHIRPS v2.0 precipitation operates at $0.05^\circ$ ($\approx 5.5\text{ km}$).
- **Impact:** Sub-village rainfall variability is smoothed by the $0.05^\circ$ precipitation grid. However, downstream vegetative and soil responses captured by Sentinel reflect true micro-topographic and vertisol moisture differences.

---

## 2. Pipeline Error Recovery Runbook

### 2.1 Handling Corrupted Downloads
If a raw raster download is interrupted (e.g., incomplete Chrome `.crdownload` or truncated GeoTIFF):
- The ingest scanner verifies GeoTIFF magic bytes and checksums.
- Corrupted rasters are flagged in `data/dashboard/data_availability.json` as `failed` and skipped.
- The pipeline proceeds with the remaining available periods without crashing.

### 2.2 Recovering from Pipeline Failures
If an unexpected crash occurs during weekly execution:
1. Inspect the processing manifest: `outputs/Dashboard/processing_manifest.json`.
2. Inspect the latest log in `scripts/logs/`.
3. Check Supabase connection and service role credentials in `.env`.
4. Re-run the safe incremental update:
   ```bash
   python scripts/realtime/realtime_update.py
   ```

