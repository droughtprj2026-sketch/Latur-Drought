# Machine-Readable Statistics Tables (Data Dictionary)

Every figure in the scientific suite is backed by an authoritative, machine-readable CSV table generated in `output/figures/scientific_suite/08_statistics_tables/`.

---

## 1. Primary Research Data Tables

```
+---------------------------------------------------------------------------------------------------------+
|                                    STATISTICAL TABLES MASTER DIRECTORY                                  |
+-----------------------------------+----------+----------------------------------------------------------+
| File Name                         | Rows     | Primary Contents & Analytical Scope                      |
+-----------------------------------+----------+----------------------------------------------------------+
| `annual_summary.csv`              | 11       | District-wide annual means, rainfall, SPI, CDI, and DAP  |
| `tehsil_summary.csv`              | 10       | Tehsil-level village counts, drought frequencies, trends |
| `tehsil_vulnerability.csv`        | 10       | Multi-factor vulnerability score, ranks, and drivers     |
| `correlation_pearson_matrix.csv`  | 9 × 9    | Full Pearson correlation matrix for all core indices     |
| `correlation_spearman_matrix.csv` | 9 × 9    | Full Spearman rank correlation matrix for core indices   |
| `correlation_pearson_pvalues.csv` | 9 × 9    | Exact two-tailed p-values for Pearson correlations       |
| `lag_correlations.csv`            | 28       | Multi-scale response lag correlations (0 to 6 months)    |
| `annual_trends_tehsil.csv`        | 10       | Sen's slope and Mann-Kendall trend statistics by tehsil  |
| `annual_trends_district.csv`      | 1        | District-wide long-term Sen's slope and MK p-values      |
| `spi12_episodes.csv`              | 6        | Historical hydrological drought episodes (duration/peak) |
| `drought_area_percentage.csv`     | 130      | Monthly % area in USDM drought categories (None to D4)   |
| `class_separation.csv`            | 24       | Interquartile ranges, medians, and class separability    |
| `availability_summary.csv`        | 4        | Optical, SAR, Thermal, and CHIRPS observation counts     |
| `village_summary.csv`             | 954      | Decadal summary metrics for every individual village     |
| `village_mean_cdi.csv`            | 954      | 11-year mean Composite Drought Index per village         |
| `village_trend.csv`               | 954      | Sen's slope and Mann-Kendall p-value for every village    |
+-----------------------------------+----------+----------------------------------------------------------+
```

---

## 2. Table Schemas & Column Definitions

### 2.1 `annual_summary.csv`
- `year` (int): Calendar year (2016 to 2026).
- `Rain_mm` (float): District mean annual precipitation depth in millimeters.
- `mean_SPI3` (float): Mean seasonal Standardized Precipitation Index.
- `mean_NDVI` (float): Mean Normalized Difference Vegetation Index.
- `mean_NSMI` (float): Mean Normalized Soil Moisture Index.
- `mean_CDI` (float): Mean Composite Drought Index ($0.0 \text{ to } 1.0$).
- `drought_area_pct` (float): Mean percentage of villages in drought status ($\text{D0--D4}$).
- `severe_area_pct` (float): Mean percentage of villages in severe drought ($\text{D2--D4}$).

### 2.2 `tehsil_summary.csv`
- `tehsil` (str): Name of administrative tehsil (10 units).
- `villages` (int): Number of revenue villages within the tehsil.
- `village_months` (int): Total observation records.
- `mean_cdi` (float): 11-year mean Composite Drought Index.
- `max_cdi` (float): Peak observed CDI value.
- `mean_spi3` (float): Mean 3-month precipitation anomaly.
- `drought_frequency_pct` (float): % of periods in drought status ($\text{D0--D4}$).
- `severe_frequency_pct` (float): % of periods in severe drought ($\text{D2--D4}$).
- `cdi_sens_slope` (float): Long-term Sen's slope trend ($+\text{ drying}, -\text{ wetting}$).
- `mk_p` (float): Mann-Kendall trend test significance level.

### 2.3 `tehsil_vulnerability.csv`
- `tehsil` (str): Name of administrative tehsil.
- `vulnerability_score` (float): Composite multi-index vulnerability rating ($0.0 \text{ to } 1.0$).
- `vulnerability_rank` (int): Rank ordering from most vulnerable ($1$) to least vulnerable ($10$).
- `primary_driver` (str): Dominant physical factor driving vulnerability (e.g., rainfall deficiency, low soil moisture retention, vegetative sensitivity).


---

<div class="chapter-nav-card">
  <a class="prev-link" href="../ppt-animations/">← PowerPoint Cartographic Animations</a>
  <a class="next-link" href="../../system/dashboard/">Interactive Next.js Dashboard →</a>
</div>
