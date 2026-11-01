# Multi-Index Composite Drought Index (CDI) Methodology

This document details the configuration, weighting theory, and dynamic re-weighting mechanics of the Composite Drought Index (CDI).

---

## 1. Ground Truth Configuration (`config/composite.yaml`)

In accordance with core project rules, **CDI weights, thresholds, and formula version are strictly maintained in `config/composite.yaml`**—never hard-coded into processing scripts.

```yaml
version: "2.1.0"
min_inputs: 1

weights:
  SPI3: 0.35      # 3-Month Meteorological Precipitation Deficit
  VCI: 0.30       # Sentinel-2 Vegetation Condition Anomaly
  NSMI: 0.20      # Sentinel-1 SAR Root-Zone Soil Moisture
  TCI: 0.15       # Landsat 8/9 Thermal Condition Index

thresholds:
  D0: 0.15        # Abnormally Dry
  D1: 0.25        # Moderate Drought
  D2: 0.35        # Severe Drought
  D3: 0.50        # Extreme Drought
  D4: 0.70        # Exceptional Drought
```

---

## 2. Mathematical Formulations

### 2.1 Nominal Full-Sensor Formulation
When all four satellite inputs are valid and unmasked:

$$\text{CDI}_{\text{nominal}} = 0.35 \cdot S(\text{SPI3}) + 0.30 \cdot S(\text{VCI}) + 0.20 \cdot S(\text{NSMI}) + 0.15 \cdot S(\text{TCI})$$

where $S(I)$ converts each index into a standardized severity score ($0.0 \le S \le 1.0$, where $1.0$ corresponds to exceptional drought):

$$S(\text{SPI3}) = \min \left( 1.0, \max \left( 0.0, \frac{-\text{SPI3} - (-0.5)}{2.5 - (-0.5)} \right) \right)$$

$$S(\text{VCI}) = 1.0 - \left( \frac{\text{VCI}}{100} \right)$$

$$S(\text{NSMI}) = 1.0 - \text{NSMI}$$

$$S(\text{TCI}) = 1.0 - \left( \frac{\text{TCI}}{100} \right)$$

### 2.2 Dynamic Component Re-Weighting Under Missing Inputs
Semi-arid tropical remote sensing faces persistent sensor occlusions:
- **Monsoon Cloud Cover (June–August):** Optical Sentinel-2 is frequently masked by thick cloud cover.
- **SAR & Thermal Revisit Stagger:** Sentinel-1 operates on a 6–12 day cycle, and Landsat on a 16-day cycle.

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
