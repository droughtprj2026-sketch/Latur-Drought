# Mathematical Formulations & Index Formulations

This document provides the definitive mathematical formulations for every biophysical, meteorological, and composite drought indicator computed in the system.

---

## 1. Optical Vegetation Reflectance Formulations

### 1.1 Normalized Difference Vegetation Index (NDVI)
NDVI is formulated as the normalized ratio of the surface reflectance difference between the Near-Infrared ($\text{NIR}$, $\lambda \approx 842\text{ nm}$, Sentinel-2 Band 8) and Red ($\text{Red}$, $\lambda \approx 665\text{ nm}$, Sentinel-2 Band 4) spectral bands:

$$\text{NDVI} = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}}$$

where:
- $\rho_{\text{NIR}}$: Top-of-Canopy (TOC) Bottom-of-Atmosphere (BOA) reflectance in the NIR spectrum ($0.0 \le \rho_{\text{NIR}} \le 1.0$).
- $\rho_{\text{Red}}$: BOA surface reflectance in the red chlorophyll-absorption band ($0.0 \le \rho_{\text{Red}} \le 1.0$).

### 1.2 Enhanced Vegetation Index (EVI)
In high-biomass agricultural regimes, NDVI exhibits asymptotic saturation. EVI incorporates the blue band ($\rho_{\text{Blue}}$, $\lambda \approx 490\text{ nm}$, Sentinel-2 Band 2) and empirical coefficients to decouple canopy reflectance from atmospheric aerosol scattering and background vertisol soil brightness:

$$\text{EVI} = G \times \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + C_1 \cdot \rho_{\text{Red}} - C_2 \cdot \rho_{\text{Blue}} + L}$$

Standard MODIS/Copernicus parameterized coefficients:
- $G = 2.5$ (Gain factor)
- $C_1 = 6.0$ (Aerosol resistance coefficient for red band)
- $C_2 = 7.5$ (Aerosol resistance coefficient for blue band)
- $L = 1.0$ (Canopy background brightness adjustment factor)

### 1.3 Vegetation Condition Index (VCI)
VCI scales current vegetative greenness relative to the historical ecological potential of each individual village polygon for the specific calendar month ($m$):

$$\text{VCI}_{v, m} = \left( \frac{\text{NDVI}_{v, m} - \text{NDVI}_{\min}(v, m)}{\text{NDVI}_{\max}(v, m) - \text{NDVI}_{\min}(v, m)} \right) \times 100$$

where:
- $\text{NDVI}_{v, m}$: Observed mean NDVI for village polygon $v$ during month $m$.
- $\text{NDVI}_{\min}(v, m)$: Historical minimum NDVI observed in village $v$ during month $m$ across the 2016–2026 baseline.
- $\text{NDVI}_{\max}(v, m)$: Historical maximum NDVI observed in village $v$ during month $m$ across the 2016–2026 baseline.

---

## 2. Thermal & Surface Energy Balance Formulations

### 2.1 Land Surface Temperature (LST)
From Landsat 8/9 Thermal Infrared Sensor (TIRS Band 10), at-sensor spectral radiance $L_\lambda$ ($\text{W}\cdot\text{m}^{-2}\cdot\text{sr}^{-1}\cdot\mu\text{m}^{-1}$) is converted to effective at-satellite brightness temperature $T_B$ ($\text{K}$) via Planck's inverse function:

$$T_B = \frac{K_2}{\ln \left( \frac{K_1}{L_\lambda} + 1 \right)}$$

where calibration constants for TIRS Band 10 are:
- $K_1 = 774.8853\ \text{W}\cdot\text{m}^{-2}\cdot\text{sr}^{-1}\cdot\mu\text{m}^{-1}$
- $K_2 = 1321.0789\ \text{K}$

Surface-emissivity corrected Land Surface Temperature ($\text{LST}$, in ${}^\circ\text{C}$) is then derived as:

$$\text{LST} = \left( \frac{T_B}{1 + \left( \frac{\lambda \cdot T_B}{\rho} \right) \ln \varepsilon} \right) - 273.15$$

where $\lambda = 10.895\ \mu\text{m}$ (effective wavelength), $\rho = h \cdot c / \sigma_B = 1.438 \times 10^{-2}\ \text{m}\cdot\text{K}$, and $\varepsilon$ is fractional vegetation cover emissivity derived from NDVI.

### 2.2 Temperature Condition Index (TCI)
Because high thermal radiance indicates evaporative drought stress, TCI inverts the temperature scale:

$$\text{TCI}_{v, m} = \left( \frac{\text{LST}_{\max}(v, m) - \text{LST}_{v, m}}{\text{LST}_{\max}(v, m) - \text{LST}_{\min}(v, m)} \right) \times 100$$

---

## 3. Synthetic Aperture Radar (SAR) Soil Moisture Formulations

### 3.1 Normalized Soil Moisture Index (NSMI)
From Sentinel-1 C-band ($5.405\text{ GHz}$) dual-polarization ($\sigma^\circ_{\text{VV}}$, $\sigma^\circ_{\text{VH}}$) radar backscatter, relative surface soil moisture is calculated by normalising backscatter against dry and saturated reference baselines:

$$\text{SMI} = \frac{\sigma^\circ_{\text{VV}} - \sigma^\circ_{\text{dry}}}{\sigma^\circ_{\text{wet}} - \sigma^\circ_{\text{dry}}}$$

For cross-index parity, Normalized Soil Moisture Index ($\text{NSMI}$) is mapped to $[0.0, 1.0]$:

$$\text{NSMI}_{v, m} = \min \left( 1.0, \max \left( 0.0, \frac{\text{SMI}_{v, m} - \text{SMI}_{\min}(v, m)}{\text{SMI}_{\max}(v, m) - \text{SMI}_{\min}(v, m)} \right) \right)$$

---

## 4. Meteorological Drought Formulations (SPI)

### 4.1 Cumulative Precipitation Aggregation
For each monthly period $t$ and timescale $k \in \{1, 3, 6, 12\}$ months, cumulative precipitation $A_{k, t}$ is:

$$A_{k, t} = \sum_{i=0}^{k-1} P_{t - i}$$

where $P_t$ is the monthly CHIRPS v2.0 precipitation depth ($\text{mm}$) for village polygon $v$.

### 4.2 Gamma Distribution Fitting
Precipitation accumulations are fitted to a two-parameter Gamma probability density function:

$$g(x; \alpha, \beta) = \frac{1}{\beta^\alpha \Gamma(\alpha)} x^{\alpha - 1} e^{-x / \beta}, \quad x > 0$$

where $\alpha > 0$ is the shape parameter, $\beta > 0$ is the scale parameter, and $\Gamma(\alpha)$ is the standard Gamma function:

$$\Gamma(\alpha) = \int_0^\infty u^{\alpha - 1} e^{-u} du$$

Parameters are estimated via Maximum Likelihood Estimation (MLE) using Thom's approximation:

$$\alpha = \frac{1}{4A} \left( 1 + \sqrt{1 + \frac{4A}{3}} \right), \quad \beta = \frac{\bar{x}}{\alpha}$$

where $A = \ln(\bar{x}) - \frac{1}{n} \sum_{i=1}^n \ln(x_i)$.

### 4.3 Cumulative Probability & Standard Normal Transformation
Accounting for zero-precipitation probability $q = P(x = 0) = m_0 / n$:

$$H(x) = q + (1 - q) G(x)$$

where $G(x) = \int_0^x g(t) dt$. The cumulative probability $H(x)$ is converted to the standard normal random variable $Z \sim \mathcal{N}(0, 1)$ via the Abramowitz & Stegun rational approximation:

$$\text{SPI} = -\left( t - \frac{c_0 + c_1 t + c_2 t^2}{1 + d_1 t + d_2 t^2 + d_3 t^3} \right), \quad 0 < H(x) \le 0.5$$

$$\text{where } t = \sqrt{\ln \left( \frac{1}{(H(x))^2} \right)}$$

and symmetrically inverted for $0.5 < H(x) < 1.0$.

---

## 5. Composite Drought Index (CDI) & Dynamic Re-weighting

### 5.1 Nominal Weight Formulation
CDI integrates meteorological, vegetative, and soil moisture components into a transparent linear composite:

$$\text{CDI}_{\text{nominal}} = w_{\text{SPI3}} \cdot S(\text{SPI3}) + w_{\text{VCI}} \cdot S(\text{VCI}) + w_{\text{NSMI}} \cdot S(\text{NSMI}) + w_{\text{TCI}} \cdot S(\text{TCI})$$

where $S(I)$ is the normalized severity score ($0.0 \le S \le 1.0$, where $1.0$ is extreme drought) for index $I$.

### 5.2 Dynamic Component Re-weighting
During monsoon cloud cover (optical Sentinel-2 obscured) or sensor downtime, unobserved indices are dropped. The remaining valid indices are dynamically re-weighted such that their sum equals $1.0$:

$$\text{CDI}_{v, t} = \frac{\sum_{i \in \mathcal{V}_{v, t}} w_i \cdot S(I_{i, v, t})}{\sum_{i \in \mathcal{V}_{v, t}} w_i}$$

where $\mathcal{V}_{v, t}$ is the set of available indicators for polygon $v$ at time $t$. If $|\mathcal{V}_{v, t}| < \text{min\_inputs}$ (defined in `config/composite.yaml`), the observation is marked `pending / No Data`; it is **never synthetic or imputed**.

