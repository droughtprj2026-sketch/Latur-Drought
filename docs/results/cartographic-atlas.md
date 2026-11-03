# Cartographic Atlas of 954 Villages

The Cartographic Atlas provides publication-grade, village-level spatial visualizations conforming strictly to peer-reviewed remote sensing journal standards.

---

## 1. Cartographic Design Specifications

To ensure scientific rigor and publication readiness:

```
+---------------------------------------------------------------------------------------------------------+
|                                    CARTOGRAPHIC DESIGN SPECIFICATIONS                                   |
+--------------------------+------------------------------------------------------------------------------+
| Typography               | Strict Times New Roman serif throughout (font.family: serif).                |
| Text Bounding Boxes      | No bounding boxes behind annotations or values (clean, unoccluded map).      |
| North Arrow              | Single authoritative North arrow in top-right corner (figure fraction).      |
| Scale Bar                | Authoritative georeferenced scale bar (0 to 40 km) with physical ticks.      |
| Village Neatlines        | Hairline polygon boundaries (0.05 to 0.08 pt, #CBD5E1).                      |
| Tehsil Neatlines         | Bold administrative boundaries (0.75 pt, #1E293B).                           |
| Zero-Value Masking       | Zero/missing periods rendered with #CBD5E1 ("No Data"); never blank.         |
| Colorbar                 | Shared horizontal colorbar centered at the bottom with physical units.       |
+--------------------------+------------------------------------------------------------------------------+
```

---

## 2. Climatological Baseline Atlases (The Reference Standards)

Drought is fundamentally defined as a **statistically significant negative departure from the climatological baseline**. Evaluating an observed absolute value (e.g., NDVI = 0.30 or Rainfall = 80 mm) without referencing the historical baseline for that specific village leads to spurious classifications. 

The baseline represents the 11-year empirical expected normal ($\mu$) across all 954 revenue villages from 2016 to 2026.

### 2.1 Master 8-Panel Climatological Baseline Atlas
![Master Baseline Atlas](../figures/07_spatial_analysis/baselines/atlas_all_indices_baseline_comparison.png)
<div class="figure-caption">Figure 3.1: Master 8-panel multi-index baseline atlas comparing 11-year climatological normals across all biophysical, meteorological, and composite drought indicators for 954 revenue villages. Click image to inspect at 500% magnification in lightbox.</div>

### 2.2 Kharif Crop Season Baseline Atlas (July–October)
![Kharif Seasonal Baseline Atlas](../figures/07_spatial_analysis/baselines/atlas_kharif_crop_season_baselines.png)
<div class="figure-caption">Figure 3.2: Kharif crop season baseline normals (July–October) capturing peak vegetative canopy, seasonal rainfall, and soil moisture against which agricultural drought declarations are legally evaluated.</div>

---

## 3. Individual Indicator Climatological Baseline Maps

=== "Baseline NDVI"
    ![Baseline NDVI Map](../figures/07_spatial_analysis/baselines/map_baseline_ndvi.png)
    <div class="figure-caption">Figure 3.3a: Decadal baseline Normalized Difference Vegetation Index (NDVI) across 954 villages. Shows highest natural biomass potential in the northern river basins (Renapur, Ahmadpur) and lowest baseline canopy in southern stony vertisols (Ausa, Nilanga).</div>

=== "Baseline CDI"
    ![Baseline CDI Map](../figures/07_spatial_analysis/baselines/map_baseline_cdi.png)
    <div class="figure-caption">Figure 3.3b: Decadal baseline Composite Drought Index (CDI) severity score. Establishes the structural climatological drought baseline, highlighting chronic vulnerability zones in south-western tehsils.</div>

=== "Baseline EVI"
    ![Baseline EVI Map](../figures/07_spatial_analysis/baselines/map_baseline_evi.png)
    <div class="figure-caption">Figure 3.3c: Decadal baseline Enhanced Vegetation Index (EVI). Adjusts for soil background vertisol reflectance and aerosol scattering, preserving sensitivity in dense crop patches.</div>

=== "Baseline NSMI"
    ![Baseline NSMI Map](../figures/07_spatial_analysis/baselines/map_baseline_nsmi.png)
    <div class="figure-caption">Figure 3.3d: Sentinel-1 C-band SAR Normalized Soil Moisture Index (NSMI) baseline. Establishes the all-weather dielectric permittivity reference for root-zone moisture across 954 villages.</div>

=== "Baseline SPI-1"
    ![Baseline SPI-1 Map](../figures/07_spatial_analysis/baselines/map_baseline_spi1.png)
    <div class="figure-caption">Figure 3.3e: Decadal baseline 1-month Standardized Precipitation Index (SPI-1). Establishes monthly meteorological moisture equilibrium and defines the negative departure threshold for empirical drought onset across all 954 revenue villages.</div>

=== "Baseline VHI"
    ![Baseline VHI Map](../figures/07_spatial_analysis/baselines/map_baseline_vhi.png)
    <div class="figure-caption">Figure 3.3f: Decadal baseline Vegetation Health Index (VHI). Blends vegetative condition (VCI) with thermal skin temperature condition (TCI).</div>

=== "Baseline VCI"
    ![Baseline VCI Map](../figures/07_spatial_analysis/baselines/map_baseline_vci.png)
    <div class="figure-caption">Figure 3.3g: Decadal baseline Vegetation Condition Index (VCI). Establishes historical phenological scaling relative to extreme maximum and minimum NDVI bounds.</div>

=== "Baseline Rainfall"
    ![Baseline Rainfall Map](../figures/07_spatial_analysis/baselines/map_baseline_rain_mm.png)
    <div class="figure-caption">Figure 3.3h: CHIRPS v2.0 decadal mean monthly precipitation depth (mm/month), illustrating the West-to-East orographic rainfall gradient across Latur district.</div>

---

## 4. Decadal Multi-Year Spatial Mean Atlases (2016–2026)

The multi-year atlases arrange all 11 years (2016 to 2026) alongside the 11-year mean baseline in a standardized $3 \times 4$ panel matrix across all 954 villages:

### 4.1 Composite Drought Index (CDI) Multi-Year Progression
![Annual Mean CDI Atlas](../figures/07_spatial_analysis/yearly_mean_atlases/atlas_yearly_mean_composite_drought_score.png)
<div class="figure-caption">Figure 3.4: 11-Year Annual Mean Composite Drought Index (CDI) Atlas across 954 revenue villages in Latur District (2016–2026). Click image to zoom in full-screen.</div>

### 4.2 Vegetation Canopy Greenness (NDVI) Decadal Progression
![Annual Mean NDVI Atlas](../figures/07_spatial_analysis/yearly_mean_atlases/atlas_yearly_mean_ndvi.png)
<div class="figure-caption">Figure 3.5: 11-Year Annual Mean Normalized Difference Vegetation Index (NDVI) across 954 villages. Shows the sharp contrast between drought years (2018) and high-biomass La Niña seasons (2020–2022).</div>

### 4.3 Surface Soil Moisture (NSMI)
![Annual Mean NSMI Atlas](../figures/07_spatial_analysis/yearly_mean_atlases/atlas_yearly_mean_nsmi.png)
<div class="figure-caption">Figure 3.6: 11-Year Annual Mean Normalized Soil Moisture Index (NSMI) derived from Sentinel-1 SAR backscatter.</div>

### 4.4 Seasonal Meteorological Moisture Balance (SPI-3)
![Annual Mean SPI-3 Atlas](../figures/07_spatial_analysis/yearly_mean_atlases/atlas_yearly_mean_spi3.png)
<div class="figure-caption">Figure 3.7: 11-Year Annual Mean 3-Month Standardized Precipitation Index (SPI-3) tracking seasonal rainfall surpluses and deficits.</div>

---

## 5. Vulnerability Rankings & Spatial Trend Analysis

Evaluating spatial risk and long-term decadal trends across 10 tehsils and 954 villages:

### 5.1 11-Year Mean Village CDI Map
![Village Mean CDI Map](../figures/07_spatial_analysis/overview_and_vulnerability/s1_village_mean_cdi.png)
<div class="figure-caption">Figure 3.8: Village-level decadal mean Composite Drought Index (CDI) across 954 revenue villages, highlighting chronic moisture deficit zones in southern tehsils.</div>

### 5.2 Tehsil Composite Vulnerability Ranking
![Tehsil Vulnerability Ranking](../figures/07_spatial_analysis/overview_and_vulnerability/s5_tehsil_vulnerability_ranking.png)
<div class="figure-caption">Figure 3.9: Integrated tehsil vulnerability ranking derived from multi-factor historical exposure, vegetative sensitivity, and soil moisture memory.</div>

### 5.3 Decadal Trend Analysis (Sen's Slope Estimator)
![Village Trend Map](../figures/07_spatial_analysis/overview_and_vulnerability/s3_village_trend.png)
<div class="figure-caption">Figure 3.10: Non-parametric Sen's slope spatial trend showing decadal rate of drought change across all 954 revenue villages.</div>

---

## 6. Landmark Historical Case Studies

### 6.1 Peak Emergency of the 2018 Drought (2018 Atlas)
In late Kharif 2018, widespread monsoon failure plunged over $80\%$ of Latur into D2–D4 drought:

![2018 Monthly Drought Atlas](../figures/07_spatial_analysis/2018/atlas_monthly_composite_drought_score_2018.png)
<div class="figure-caption">Figure 3.11: Complete 12-month cadastral drought progression for 2018 (Crisis Deep Dive), showing rapid escalation into exceptional drought by September 2018.</div>

### 6.2 Bumper Recovery Under La Niña (2020 Atlas)
In 2020, heavy monsoon rainfall restored soil reservoirs and led to record vegetative greening:

![2020 Monthly Drought Atlas](../figures/07_spatial_analysis/2020/atlas_monthly_composite_drought_score_2020.png)
<div class="figure-caption">Figure 3.12: 12-Month cadastral drought progression for 2020. Over 98% of villages registered None/Normal, demonstrating rapid Vertisol agro-ecological recovery.</div>

### 6.3 Current Operational Monitoring Horizon (2026 Atlas)
![2026 Monthly Drought Atlas](../figures/07_spatial_analysis/2026/atlas_monthly_composite_drought_score_2026.png)
<div class="figure-caption">Figure 3.13: Latest operational satellite observation atlas for 2026 displaying localized moisture stress in southeastern tehsils.</div>

---

<div class="chapter-nav-card">
  <a class="prev-link" href="../../pipeline/manifests/">← Incremental Processing Ledgers</a>
  <a class="next-link" href="../statistical-analysis/">Statistical Findings & Lag Dynamics →</a>
</div>
