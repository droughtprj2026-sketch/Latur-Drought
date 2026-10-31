# Scientific Baseline & Multi-Scale Drought Architecture
**Real-Time & Historical Drought Monitoring — Latur District, Marathwada (2016–2026)**

---

## 1. Executive Summary & Data Understanding

The Latur drought observatory monitors **954 revenue villages** across all **10 tehsils** spanning **98 monthly observation periods** from January 2016 through October 2026 (93,492 village-month records).

Drought is fundamentally a **climatological departure from normal**. Evaluating an absolute vegetation index (e.g. NDVI = 0.35) without knowing the historical expectation for that specific calendar month leads to incorrect classifications (e.g., dry winter vs monsoon failure).

```
   ┌───────────────────────────────────────────────────────────────────────────────────┐
   │                           CLIMATOLOGICAL ENGINE                                  │
   ├───────────────────────────────┬───────────────────────────────────────────────────┤
   │ Baseline Normal (μ)           │ 10-Year historical mean per village & month       │
   │ Standard Deviation (σ)        │ Historical variance for confidence intervals      │
   │ Z-Score Anomaly               │ Z = (Observed - μ) / σ                           │
   │ Multi-Scale SPI               │ SPI-1 (Met), SPI-3 (Agri), SPI-6/12 (Hydro)       │
   │ Multi-Index Composite (CDI)   │ SPI-3 (30%) + VHI (20%) + VCI (15%) +             │
   │                               │ NDVI (15%) + EVI (10%) + PCI (10%)                │
   └───────────────────────────────┴───────────────────────────────────────────────────┘
```

---

## 2. Mathematical Definition of Baselines

### 2.1 Climatological Normal & Standard Deviation
For each village $i$ and calendar month $m \in \{1, \dots, 12\}$:
$$\mu_{i, m}^{(X)} = \frac{1}{N_m} \sum_{y \in \text{Years}} X_{i, y, m}$$
$$\sigma_{i, m}^{(X)} = \sqrt{\frac{1}{N_m - 1} \sum_{y \in \text{Years}} \left(X_{i, y, m} - \mu_{i, m}^{(X)}\right)^2}$$

Computed for:
- $\text{NDVI}$: Satellite greenness normal
- $\text{VCI}$: Condition index normal
- $\text{Rainfall (mm)}$: CHIRPS precipitation normal
- $\text{SPI-3}$: 3-month standardized precipitation anomaly normal

### 2.2 Z-Score Anomaly
$$Z_{i, y, m}^{(X)} = \frac{X_{i, y, m} - \mu_{i, m}^{(X)}}{\sigma_{i, m}^{(X)}}$$

- $Z < -1.0$: Moderate moisture deficit ($> 1\sigma$ below normal)
- $Z < -1.5$: Severe drought stress ($> 1.5\sigma$ below normal)
- $Z < -2.0$: Extreme/exceptional climatological drought ($> 2\sigma$ below normal)

### 2.3 Multi-Scale Standardized Precipitation Index (SPI)
CHIRPS precipitation is integrated across rolling accumulation windows:
1. **SPI-1 (1 Month)**: Immediate meteorological moisture shock.
2. **SPI-3 (3 Months)**: Agricultural root-zone soil moisture deficit.
3. **SPI-6 (6 Months)**: Seasonal surface runoff and small reservoir depletion.
4. **SPI-12 (12 Months)**: Annual hydrological drought, deep groundwater depletion, and inter-annual reservoir deficits.

---

## 3. Visualization Architecture & Interactive Controls

To allow decision-makers to track the progression of drought across time and space, the interface provides:

1. **Continuous 98-Month Timeline Scrubber**:
   - Scrub smoothly from `2016-01` to `2026-10`.
   - **Play / Pause Animation** at 1.5 seconds per period.
   - Stepper buttons (`< Prev`, `Next >`) and quick event bookmarks (`2018 Drought`, `2020 High Monsoon`, `2026 Current`).
2. **Climatological Baseline Comparison Chart**:
   - Current Year vs 10-Year Climatological Mean ($\mu$) with $\pm 1\sigma$ normal envelope.
   - Visual indicator showing whether the village is above normal, in deficit, or severely depleted.
3. **Multi-Scale SPI Comparison Chart**:
   - Synchronized line plot of SPI-1, SPI-3, SPI-6, and SPI-12 over time.
   - Color bands indicating WMO drought thresholds ($-1.0, -1.5, -2.0$).
4. **Multi-Index Trajectory Comparison**:
   - Dual-axis graph of CDI Composite against Rainfall and Vegetation indices.
5. **Tehsil Climatological Rankings**:
   - Comparing baseline deviation and drought percentage across all 10 tehsils.
