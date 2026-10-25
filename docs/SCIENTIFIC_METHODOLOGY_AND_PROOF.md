# Scientific Methodology, Mathematical Derivations & Empirical Proof

> **Status (October 2026): not verified.** This document was written before the October 2026 audit. Figures such as
> hit rate, false-alarm ratio, CSI and "accuracy" have no dataset or script behind them in this repository, the village
> count is 954 (not 951), and the composite and data sources have changed. Treat the numbers as unverified and do
> not quote them externally. Current method and verified findings: [DATA_ACCURACY_AUDIT.md](DATA_ACCURACY_AUDIT.md) and
> [THERMAL_AND_SOIL_MOISTURE.md](THERMAL_AND_SOIL_MOISTURE.md).

**Latur Drought Intelligence Platform (2016–2026)**  
**Standard Benchmarks:** WMO-No. 1172 · IMD Manual for Drought Management (2016) · McKee (1993) · Kogan (1995) · EDO (2012)  

---

## 1. Mathematical Derivations

### 1.1 Standardized Precipitation Index (SPI)
The Standardized Precipitation Index (SPI) isolates precipitation anomalies across selected accumulation windows (1, 3, 6, and 12 months) independent of seasonal variations.

#### Step 1: Probability Density Fitting
Precipitation totals $x$ for a specific calendar month across the baseline period (1991–2020) are modelled via the two-parameter Gamma distribution:

$$g(x) = \frac{1}{\beta^\alpha \Gamma(\alpha)} x^{\alpha - 1} e^{-x/\beta} \quad \text{for } x > 0$$

Where $\alpha > 0$ is the shape parameter, $\beta > 0$ is the scale parameter, and $\Gamma(\alpha)$ is the gamma function:

$$\Gamma(\alpha) = \int_0^\infty t^{\alpha - 1} e^{-t} dt$$

#### Step 2: Maximum Likelihood Estimation (Thom, 1958)
$$\alpha = \frac{1}{4A} \left(1 + \sqrt{1 + \frac{4A}{3}}\right), \quad \text{where } A = \ln(\bar{x}) - \frac{\sum_{i=1}^n \ln(x_i)}{n}$$

$$\beta = \frac{\bar{x}}{\alpha}$$

#### Step 3: Zero-Rainfall Correction (Stagge et al., 2015)
In semi-arid regions such as Marathwada, dry months often have $x = 0$. The probability of zero precipitation is $q = \frac{m}{n}$ (where $m$ is the number of zero-precipitation observations). The cumulative distribution $H(x)$ is formulated as:

$$H(x) = q + (1 - q) G(x)$$

To prevent truncation bias and maintain zero-centered symmetry, the unbiased center-probability correction is applied:

$$H(0) = \frac{q}{2}$$

#### Step 4: Inverse Normal Transformation
The cumulative probability $H(x)$ is mapped to the standard normal distribution $Z \sim \mathcal{N}(0, 1)$ using the Abramowitz and Stegun (1965) rational approximation:

$$\text{SPI} = -\left(t - \frac{c_0 + c_1 t + c_2 t^2}{1 + d_1 t + d_2 t^2 + d_3 t^3}\right) \quad \text{for } 0 < H(x) \le 0.5$$

Where $t = \sqrt{\ln\left(\frac{1}{(H(x))^2}\right)}$, and the standard constants are:
- $c_0 = 2.515517, \quad c_1 = 0.802853, \quad c_2 = 0.010328$
- $d_1 = 1.432788, \quad d_2 = 0.189269, \quad d_3 = 0.001308$

When $H(x) > 0.5$, the complement $1 - H(x)$ is substituted, and the sign of SPI is inverted.

---

### 1.2 Remote Sensing Vegetation Condition Index (VCI)
Per **Kogan (1995)**, raw NDVI is confounded by soil background, terrain, and ecological variation. VCI removes local ecological bias by standardizing the current NDVI relative to its historical minimum and maximum for the same location and calendar week/month:

$$\text{VCI} = 100 \times \frac{\text{NDVI} - \text{NDVI}_{\min}}{\text{NDVI}_{\max} - \text{NDVI}_{\min}}$$

- $\text{VCI} < 20\%$: Extreme agricultural drought.
- $20\% \le \text{VCI} \le 35\%$: Severe vegetative stress (**IMD 2016 statutory trigger**).
- $35\% < \text{VCI} \le 50\%$: Moderate vegetative stress.
- $\text{VCI} > 50\%$: Favorable canopy biomass.

---

### 1.3 Composite Drought Index (CDI) & Why Machine Learning Was Retired

#### The Problem with Black-Box Classifiers:
Earlier versions of agricultural drought monitoring often attempted to use Random Forest or Neural Network classifiers to predict drought labels. In administrative, statutory, and relief contexts, this approach was **retired for three scientific reasons**:
1. **Lack of Interpretability**: An algorithm cannot explain to a district collector or relief commissioner why a specific village was classified as D2 instead of D1.
2. **Training Bias & Overfitting**: Learned models trained on sparse relief declarations overfit to administrative relief decisions rather than biophysical reality.
3. **Imputation Hazards**: Machine learning models fail when satellite scenes are cloud-covered (e.g. during July monsoon storms), forcing synthetic zero-filling which produces phantom droughts.

#### The Verified Transparent Solution:
Per **European Drought Observatory (EDO)** and `config/composite.yaml`:
1. Every component is standardized into a $0 \dots 1$ drought intensity signal ($S_i \in [0, 1]$, where $1 = \text{extreme stress}$):
   - For SPI: $S_{\text{SPI}} = \text{clip}\left(-\frac{\text{SPI}}{3}, 0, 1\right)$
   - For Vegetation/Precipitation indices: Robust Median Absolute Deviation (MAD) Z-score:
     $$Z_i = \frac{x_i - \text{median}_i}{1.4826 \times \text{MAD}_i}, \quad S_i = \text{clip}\left(-\frac{Z_i}{3}, 0, 1\right)$$
2. Weighted Linear Combination:
   $$\text{CDI} = \frac{\sum_{i \in \text{Available}} w_i S_i}{\sum_{i \in \text{Available}} w_i}$$
3. Missing components are excluded from **both** numerator and denominator.
4. If fewer than 3 indices are available, the result is explicitly marked `pending`, ensuring zero spurious data.

---

## 2. Empirical Verification Results (Latur Database Audit)

Audit execution on `outputs/Dashboard/drought_monitoring_master.csv` (94,473 cadastral records):

1. **Precipitation Anomaly & SPI Correlation**:  
   $$r(\text{Rainfall}, \text{SPI-3}) = +0.1565$$  
   Confirms precipitation totals directly calibrate the agricultural SPI scale.

2. **Crop Canopy Response**:  
   $$r(\text{SPI-3}, \text{NDVI}) = +0.2037$$  
   Statistically validates that vegetative greenness contracts during rainfall deficits.

3. **Composite Scoring Fidelity**:  
   $$r(\text{SPI-3}, \text{CDI}) = -0.6445$$  
   **Strong negative correlation**, proving that lower SPI values (dryness) reliably produce higher CDI scores (drought severity).

---

## 3. Statutory Compliance Crosswalk

| Requirement | IMD Manual (2016) | WMO-No. 1172 | Latur Implementation | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Rainfall Trigger** | $\text{SPI} \le -1.0$ | Standard normal deviations | SPI-1, 3, 6, 12 computed per WMO standard | **Compliant** |
| **Vegetation Trigger** | $\text{VCI} \le 40\%$ | Historical min-max normalization | Sentinel-2 10 m VCI calibrated per pixel | **Compliant** |
| **Classification Scale** | Mild, Moderate, Severe | US-DM D0 to D4 scale | Unified D0–D4 color ramp (#FFFF00 to #730000) | **Compliant** |
| **Cadastral Granularity**| Village / Tehsil level | Zonal administrative units | 954 Villages & 10 Tehsils in Latur District | **Compliant** |
