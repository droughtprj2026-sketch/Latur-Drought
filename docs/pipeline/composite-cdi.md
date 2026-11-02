# Multi-Index Composite Drought Index (CDI) Methodology

This document details the configuration, weighting theory, and dynamic re-weighting mechanics of the Composite Drought Index (CDI).

---

## 1. Ground Truth Configuration (`config/composite.yaml`)

In accordance with core project rules, **CDI weights, thresholds, and formula version are strictly maintained in `config/composite.yaml`**—never hard-coded into processing scripts.

```yaml
formula_version: "cdi-v2026.12"
min_inputs: 1

weights:
  SPI:  0.50      # 3-Month Standardized Precipitation Index (CHIRPS)
  VCI:  0.25      # Sentinel-2 Vegetation Condition Index
  NDVI: 0.15      # Sentinel-2 Normalized Difference Vegetation Index
  NSMI: 0.10      # Sentinel-2 SWIR Normalized Soil Moisture Index

thresholds:
  - { max: 0.20, code: "None", label: "Not in drought" }
  - { max: 0.35, code: "D0",   label: "Abnormally dry / Mild" }
  - { max: 0.50, code: "D1",   label: "Moderate drought" }
  - { max: 0.65, code: "D2",   label: "Severe drought" }
  - { max: 0.80, code: "D3",   label: "Extreme drought" }
  - { max: 1.01, code: "D4",   label: "Exceptional drought" }
```

---

## 2. Mathematical Formulations

### 2.1 Nominal Full-Sensor Formulation
When all four inputs are valid and unmasked:

$$\text{CDI}_{\text{nominal}} = 0.50 \cdot S(\text{SPI}) + 0.25 \cdot S(\text{VCI}) + 0.15 \cdot S(\text{NDVI}) + 0.10 \cdot S(\text{NSMI})$$

where $S(I)$ converts each index into a standardized severity score ($0.0 \le S \le 1.0$, where $1.0$ corresponds to exceptional drought):

- **SPI (neg_clip):** $S(\text{SPI}) = \text{clip}(-\text{SPI} / 3,\ 0,\ 1)$
- **NDVI, VCI, NSMI (robust_z):** Per (village, calendar month) robust standardised anomaly: $z = (x - \text{median}) / (1.4826 \cdot \text{MAD})$; $S = \text{clip}(-z / 3,\ 0,\ 1)$. A normal month ($z \approx 0$) scores near 0 (None/D0); only deficits score.

### 2.2 Dynamic Component Re-Weighting Under Missing Inputs
Semi-arid tropical remote sensing faces persistent sensor occlusions:
- **Monsoon Cloud Cover (June–September):** Optical Sentinel-2 is frequently masked by thick cloud cover, so NDVI, VCI and NSMI are unavailable.

When an input indicator is unavailable (unobserved or cloud-masked), it is **dropped** from the summation. The remaining available indicators are dynamically re-weighted such that their operational weights sum to exactly $1.0$:

$$\text{CDI}_{v, t} = \frac{\sum_{i \in \mathcal{V}_{v, t}} w_i \cdot S(I_{i, v, t})}{\sum_{i \in \mathcal{V}_{v, t}} w_i}$$

where $\mathcal{V}_{v, t}$ is the set of available indicators for polygon $v$ at time $t$. If $|\mathcal{V}_{v, t}| < \text{min\_inputs}$, the observation is marked `pending / No Data`; it is **never synthetic or imputed**.

---

## 3. Empirical Component Contributions

![Component Contributions Across Years](../figures/05_distributions/d5_component_contributions.png)
<div class="figure-caption">Figure 7.1: Component contributions to the Composite Drought Index across calendar years, showing the high influence of SPI-3 and NSMI during monsoon cloud periods.</div>

![Index Agreement Matrix](../figures/04_index_relationships/r6_index_agreement.png)
<div class="figure-caption">Figure 7.2: Inter-index agreement across drought classes, demonstrating that multi-sensor fusion substantially suppresses single-sensor false alarms.</div>

---

## 4. Why the Random Forest Classifier Was Retired

In earlier iterations of the system, a Random Forest machine learning classifier was evaluated to predict drought classes from spectral features. While machine learning is effective for land cover classification, **it was explicitly retired for operational drought classification** based on fundamental scientific and policy constraints:

1. **Non-Monotonic Predictions:** Random Forest decision boundaries can exhibit non-monotonic behavior—where an increase in rainfall or canopy greenness in high-dimensional feature space counterintuitively triggers an elevated drought class.
2. **Black-Box Opacity:** Agricultural relief distribution and crop insurance claims require transparent, legally defensible, and physically traceable metrics. Stakeholders and government agronomists cannot audit the weighted votes of 500 decision trees.
3. **Out-of-Distribution Vulnerability:** Extreme climate events (such as the unprecedented 2018 drought) fall outside training distribution clusters, causing decision trees to default to unpredictable leaf nodes.
4. **Transparent Linear Composite:** The multi-index weighted composite provides 100% mathematical transparency: any researcher or farmer can manually verify their village's CDI from the component indices.

---

<div class="chapter-nav-card">
  <a class="prev-link" href="../architecture/">← Dual Engine Pipeline Architecture</a>
  <a class="next-link" href="../classification/">Drought Classification & Parity →</a>
</div>
