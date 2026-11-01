# Statistical Analysis & Findings

This document presents the core statistical findings, response-lag dynamics, and trend analyses derived across the 11-year empirical record (124,020 village-months).

---

## 1. Inter-Index Correlation & Coupling

The inter-index correlation matrices evaluate coupling between meteorological drivers and satellite biophysical responses across 954 villages:

### 1.1 Parametric Pearson Correlation Matrix
![Pearson Correlation Matrix](../figures/02_correlation/c1_pearson_matrix.png)
<div class="figure-caption">Figure 4.1: Parametric Pearson correlation matrix ($r$) across all biophysical and meteorological indicators over 124,020 observation rows.</div>

### 1.2 Non-Parametric Spearman Rank Correlation
![Spearman Rank Correlation Matrix](../figures/02_correlation/c2_spearman_matrix.png)
<div class="figure-caption">Figure 4.2: Non-parametric Spearman rank correlation ($\rho$) evaluating monotonic relationships resistant to non-normality and outliers.</div>

### 1.3 Pearson vs. Spearman Metric Concordance
![Pearson vs Spearman Agreement](../figures/02_correlation/c3_pearson_vs_spearman_agreement.png)
<div class="figure-caption">Figure 4.3: High concordance ($>96\%$ rank-order alignment) between Pearson and Spearman coefficients, confirming index linear stability.</div>

### 1.4 Statistical Significance & Confidence Intervals
![Statistical Significance Matrices](../figures/02_correlation/c4_significance_matrices.png)
<div class="figure-caption">Figure 4.4: p-value matrices ($p < 0.001$) confirming that all core index correlations are statistically significant across large-sample degrees of freedom.</div>

---

## 2. Multi-Scale Lag-Response Dynamics

Evaluating cross-correlation across temporal lags ($0\text{ to }6\text{ months}$) reveals the empirical hydrological memory of Marathwada agriculture:

![Response Lag Dynamics](../figures/04_index_relationships/r5_response_lag.png)
<div class="figure-caption">Figure 4.5: Response latency curve: Soil moisture (NSMI) responds near-instantaneously ($0\text{--}1\text{ month}$), whereas canopy greenness (NDVI/VCI) exhibits a $1\text{--}2\text{ month}$ delayed wilting response.</div>

### Key Physical Insights
- **Root-Zone Soil Moisture (NSMI):** Immediate response ($0\text{--}1\text{ month lag}$, peak correlation at $\text{Lag} = 0$).
- **Vegetation Canopy Greenness (NDVI & VCI):** Responds with a **$1\text{--}2\text{ month delay}$**. Crops draw upon deep vertisol capillary water before rapid canopy collapse occurs.
- **Hydrological Deficit (SPI-12):** Lags meteorological triggers by **$3\text{--}5\text{ months}$**, reflecting deep aquifer and surface reservoir recharge times.

---

## 3. Bivariate Regressions & Density Couplings

### 3.1 Indicator Scatter Regressions Against CDI Severity
![Bivariate Scatter Regressions](../figures/04_index_relationships/r1_core_scatter_regressions.png)
<div class="figure-caption">Figure 4.6: Bivariate scatter regressions of NDVI, SPI-3, and NSMI against Composite Drought Index (CDI) showing clear physical gradients.</div>

### 3.2 High-Density Bivariate Hexbin Matrix
![Hexbin Density Matrix](../figures/04_index_relationships/r3_hexbin_density.png)
<div class="figure-caption">Figure 4.7: 2D hexagonal binning density matrix illustrating joint distributions across all 124,020 observed village-months without overplotting.</div>

### 3.3 Multi-Index Pairplot Matrix
![Pairplot Matrix](../figures/04_index_relationships/r2_pairplot_matrix.png)
<div class="figure-caption">Figure 4.8: Multi-index pairplot displaying marginal kernel densities and pairwise scatter distributions across all satellite indicators.</div>

### 3.4 Tehsil Stratified Regressions
![Tehsil Regressions](../figures/04_index_relationships/r4_regression_by_tehsil.png)
<div class="figure-caption">Figure 4.9: Linear regressions stratified by administrative tehsil, demonstrating consistent slope coefficients across all 10 sub-districts.</div>

---

## 4. Spatio-Temporal Drought Propagation

### 4.1 West-to-East Spatio-Temporal Hovmöller Diagram
To track geographic propagation across Latur's 10 tehsils, the Hovmöller diagram arranges tehsils along the vertical axis ordered strictly **West-to-East** by their geographic centroid longitudes ($76.50^\circ\text{E} \to 77.16^\circ\text{E}$):

![Hovmoller Spatio-Temporal Diagram](../figures/06_temporal_analysis/t1_hovmoller_cdi_spi.png)
<div class="figure-caption">Figure 4.10: Hovmöller diagram showing the spatio-temporal propagation of drought shocks across 10 tehsils from West to East (2016–2026).</div>

### 4.2 Drought Affected Percentage (DAP) Stacked Area Dynamics
![DAP Stacked Area Dynamics](../figures/06_temporal_analysis/t7_drought_area_percentage_stacked.png)
<div class="figure-caption">Figure 4.11: 11-Year monthly Drought Affected Percentage (DAP) stacked area distribution tracking percentage of Latur villages in None, D0, D1, D2, D3, and D4 classes.</div>

### 4.3 Tehsil Longitudinal Time Series Trends
![Tehsil Longitudinal Trends](../figures/06_temporal_analysis/t6_tehsil_trends.png)
<div class="figure-caption">Figure 4.12: Longitudinal CDI time-series comparison across all 10 tehsils from 2016 to 2026, highlighting severe regional synchronization during drought crises.</div>

### 4.4 Multi-Season Hydrological Episodes (SPI-12)
![SPI-12 Multi-Season Episodes](../figures/06_temporal_analysis/t5_spi12_episodes.png)
<div class="figure-caption">Figure 4.13: 12-Month SPI timeline identifying protracted hydrological drought events in 2016, 2018–2019, and late 2023.</div>

---

<div class="chapter-nav-card">
  <a class="prev-link" href="../cartographic-atlas/">← Cartographic Atlas of 954 Villages</a>
  <a class="next-link" href="../ppt-animations/">PowerPoint Cartographic Animations →</a>
</div>
