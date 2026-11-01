# Incremental Processing & Manifest Ledgers

This document explains the manifest tracking system that powers incremental, idempotent data processing.

---

## 1. Why Manifest Ledgers Are Mandatory

Reprocessing a 10-year satellite archive (hundreds of gigabytes of Sentinel-2 and Landsat rasters across 954 village polygons) takes substantial compute time. 

To enable near real-time weekly updates within seconds:
- Every pipeline execution is **strictly incremental**.
- The system reads per-source manifest ledgers (`manifests/sentinel.json` and `manifests/chirps.json`).
- Only newly arrived or affected periods are processed.
- Results are idempotently appended to the master analytical tables.

---

## 2. Manifest Schema & Architecture

### 2.1 Sentinel-2 Manifest (`manifests/sentinel.json`)
Tracks the ingestion state, checksum, timestamp, and cloud coverage percentage for every Sentinel-2 raster:

```json
{
  "last_updated": "2026-10-18T14:32:00Z",
  "periods": {
    "2026-09": {
      "filename": "S2_Latur_2026_09.tif",
      "sha256": "4a7f8e...",
      "status": "ingested",
      "valid_pixels_pct": 84.2,
      "processed_at": "2026-10-02T10:15:30Z"
    },
    "2026-10": {
      "filename": "S2_Latur_2026_10.tif",
      "sha256": "8b2d1c...",
      "status": "ingested",
      "valid_pixels_pct": 91.5,
      "processed_at": "2026-10-18T14:30:12Z"
    }
  }
}
```

### 2.2 CHIRPS Precipitation Manifest (`manifests/chirps.json`)
Tracks ingested CHIRPS daily/monthly rainfall rasters. 

### 2.3 Rolling SPI Recalculation Dependency Rule
Because SPI is a rolling cumulative calculation, **a new CHIRPS monthly raster automatically triggers recalculation of all rolling windows that include it**:
- New month $M$ triggers:
  - $\text{SPI-1}$ for month $M$.
  - $\text{SPI-3}$ for months $M$, $M+1$, and $M+2$.
  - $\text{SPI-6}$ for months $M \dots M+5$.
  - $\text{SPI-12}$ for months $M \dots M+11$.

This dependency graph ensures that historical SPI indices remain mathematically consistent whenever late-arriving precipitation updates are registered.

