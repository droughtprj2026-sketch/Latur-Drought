# Historical Analysis & Climatological Calibration Engine (2016–2026)

This directory contains the scientific and data-processing scripts used to construct, calibrate, and validate the 10-year historical drought baseline for Latur District, Maharashtra.

---

## 1. Pipeline Architecture

1. **CHIRPS Climatology & Multi-Scale SPI**:
   - `latur_chirps_spi.py`: Ingests UCSB CHIRPS precipitation rasters (1991–2026 calibration climatology), computes gamma-distributed Standardized Precipitation Index across 1, 3, 6, and 12-month rolling windows.
   - `process_spi_data.py`: Prepares historical precip tables and handles missing months.

2. **Sentinel-2 Multispectral Indices & Cloud Masking**:
   - `latur_sentinel_indices.py`: Extracts Top-of-Atmosphere (TOA) and Bottom-of-Atmosphere (BOA/L2A) surface reflectance, applying Scene Classification Layer (SCL) cloud masks.
   - `process_sentinel_zonal.py`: Computes NDVI, EVI, NDMI, VCI, and VHI over Latur district and tehsil polygons.

3. **Multi-Index Composite Drought Index (CDI)**:
   - `composite_cdi.py`: Transparent multi-index fusion combining SPI, VHI, VCI, NDVI, EVI, and PCI with statutory weights defined in `config/composite.yaml`.

4. **Village-Level Aggregation & Timeseries Synthesis**:
   - `build_village_indices.py`: Computes zonal statistics across all 954 revenue villages.
   - `build_village_timeseries.py`: Structures historical time series per village.
   - `build_baseline_drought.py`: Computes 10-year monthly empirical normal ($\mu$) and standard deviation ($\sigma$).

5. **Validation & Verification**:
   - `validate_historical_analysis.py`: Validates historical drought events ('16 Crisis, '18 Deficit, '20-21 Recovery, '23 Stress, '26 Current) and outputs accuracy metrics.

---

## 2. Usage

Run the historical validation suite:
```bash
python historical/validate_historical_analysis.py
```

Recompute 10-year village baselines:
```bash
python historical/build_baseline_drought.py
```
