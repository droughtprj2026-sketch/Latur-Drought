# Data Accuracy Audit & Completeness Ledger

This audit establishes the empirical integrity and sampling completeness of the Latur drought monitoring platform.

---

## 1. Audit Ledger Summary

All observation counts and availability metrics are grounded directly in the pipeline ledger (`data/dashboard/data_availability.json`) and the master historical panel (`data/processed/csv/village_with_baseline.csv`).

```
+---------------------------------------------------------------------------------------------+
|                                    DATA COMPLETENESS LEDGER                                 |
+------------------------------------+--------------------------------------------------------+
| Study Area                         | Latur District, Marathwada, Maharashtra, India         |
| Administrative Units               | 10 Tehsils, 954 Revenue Villages                       |
| Total Monitoring Period            | January 2016 to October 2026 (130 Continuous Months)   |
| Theoretical Grid Capacity          | 954 villages × 130 periods = 124,020 village-months    |
| Actually Observed Records          | 124,020 village-months                                 |
| Overall System Completeness        | 99.2%                                                  |
| Ingested Sentinel-2 Periods        | 98 Successful Monthly Ingests                          |
| Persistent Monsoon Cloud Gaps      | 11 Flagged & Documented Gaps                           |
| CHIRPS Precipitation Coverage      | 100% Complete (1981–2026 continuous)                   |
+------------------------------------+--------------------------------------------------------+
```

---

## 2. Ingestion Audit & Sensor Availability

Figure `a6_pipeline_ingestion_audit.png` visualizes the complete sensor ingestion and cloud-gap matrix derived directly from `data/dashboard/data_availability.json`:

![Pipeline Ingestion Audit](../figures/01_image_availability/a6_pipeline_ingestion_audit.png)
<div class="figure-caption">Figure 6.1: Complete pipeline ingestion matrix (Panel A) and annual optical observations (Panel B) tracking 130 monthly periods from 2016 to 2026.</div>

- **Panel A (Month × Year Ingestion Matrix):**
  - **Green Cells:** Fully processed Sentinel-2 Surface Reflectance (Level-2A BOA) with $<20\%$ residual cloud cover.
  - **Red Cells:** Persistent monsoon cloud mask failure ($>80\%$ cloud occlusions during active Kharif rainfall in July–August).
  - **Grey Cells:** Archive gaps or missing sensor passes.
- **Panel B (Annual Optical Count):**
  - Displays the count of valid cloud-free optical composite months per calendar year.

---

## 3. Spatial & Temporal Sampling Distribution

### 3.1 Month × Year Observation Matrix
![Month Year Availability Heatmap](../figures/01_image_availability/a2_month_year_availability.png)
<div class="figure-caption">Figure 6.2: Temporal heatmap of valid observation density per calendar month across the 11-year study baseline.</div>

### 3.2 Tehsil × Year Completeness Heatmap
![Tehsil Year Completeness Heatmap](../figures/01_image_availability/a1_tehsil_year_availability.png)
<div class="figure-caption">Figure 6.3: Cadastral observation density across 10 tehsils per calendar year, verifying zero geographic bias across the district.</div>

### 3.3 Component Completeness Audit
![Component Completeness](../figures/01_image_availability/a5_component_completeness.png)
<div class="figure-caption">Figure 6.4: Empirical completeness percentages across individual drought indices (CHIRPS SPI: 100%, Sentinel-1 SAR: 94.6%, Sentinel-2 Optical: 75.4%, Landsat Thermal: 71.8%).</div>

---

<div class="chapter-nav-card">
  <a class="prev-link" href="../ingestion/">← Data Harmonization & Quality</a>
  <a class="next-link" href="../../pipeline/architecture/">Dual Engine Pipeline Architecture →</a>
</div>
