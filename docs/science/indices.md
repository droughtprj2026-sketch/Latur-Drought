# Drought Indices Encyclopedia

This encyclopedia documents every biophysical and meteorological drought index computed, calibrated, and monitored within the Latur district system across 954 revenue villages.

---

## 1. Summary of Monitored Indicators

| Index Symbol | Full Formal Name | Physical Domain | Primary Sensor Source | Baseline / Scale |
| :--- | :--- | :--- | :--- | :--- |
| **NDVI** | Normalized Difference Vegetation Index | Canopy Greenness & Biomass | Sentinel-2 MSI (B4, B8) | $-1.0 \text{ to } +1.0$ |
| **EVI** | Enhanced Vegetation Index | Atmospheric & Soil Adjusted Canopy | Sentinel-2 MSI (B2, B4, B8) | $-1.0 \text{ to } +1.0$ |
| **VCI** | Vegetation Condition Index | Relative Phenological Anomaly | Sentinel-2 MSI Baseline | $0.0 \text{ to } 100.0\%$ |
| **TCI** | Temperature Condition Index | Thermal Evaporative Stress | Landsat 8/9 TIRS (Band 10) | $0.0 \text{ to } 100.0\%$ |
| **NSMI** | Normalized Soil Moisture Index | Surface Moisture (SWIR reflectance) | Sentinel-2 MSI (B11, B12) | $0.0 \text{ to } 1.0$ |
| **SMI** | Soil Moisture Index | Root-Zone Water Permittivity | Sentinel-1 SAR (VV) | $0.0 \text{ to } 100.0\%$ |
| **VHI** | Vegetation Health Index | Joint Vegetative & Thermal Stress | Dual Optical-Thermal | $0.0 \text{ to } 100.0\%$ |
| **SPI-1** | 1-Month Standardized Precipitation Index | Flash Meteorological Drought | UCSB CHIRPS v2.0 | $-\infty \text{ to } +\infty$ |
| **SPI-3** | 3-Month Standardized Precipitation Index | Seasonal Kharif/Rabi Moisture | UCSB CHIRPS v2.0 | $-\infty \text{ to } +\infty$ |
| **SPI-6** | 6-Month Standardized Precipitation Index | Medium-Term Agricultural Water | UCSB CHIRPS v2.0 | $-\infty \text{ to } +\infty$ |
| **SPI-12** | 12-Month Standardized Precipitation Index | Hydrological & Storage Deficit | UCSB CHIRPS v2.0 | $-\infty \text{ to } +\infty$ |
| **CDI** | Composite Drought Index | Multi-Index Integrated Risk | Multi-Sensor Synthesis | $0.0 \text{ to } 1.0$ |

---

## 2. Statistical Distributions Across Drought Classes

The empirical separation of each biophysical index across USDM drought severity tiers confirms clear multi-sensor sensitivity:

![Index Distributions Across Drought Classes](../figures/05_distributions/d1_index_distributions.png)
<div class="figure-caption">Figure 2.1: Multi-index distributions across drought severity classes over 124,020 observed village-months. Click image to inspect full-screen.</div>

![Class Separation Analysis](../figures/05_distributions/d3_class_separation.png)
<div class="figure-caption">Figure 2.2: Statistical separability analysis demonstrating clean differentiation between normal and severe drought states.</div>

---

## 3. Mathematical Specifications & Biophysical Formulations

### 3.1 Normalized Difference Vegetation Index (NDVI)
NDVI quantifies photosynthetic absorption of red light ($665\text{ nm}$, Sentinel-2 Band 4) and mesophyll scattering of near-infrared ($842\text{ nm}$, Sentinel-2 Band 8):

$$\text{NDVI} = \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + \rho_{\text{Red}}}$$

- **Ecological Calibrations in Latur Vertisols:**
  - Water bodies & wetlands: $< 0.0$
  - Fallow / bare soil (pre-monsoon April–May): $0.10\text{--}0.18$
  - Early Kharif emergence (July): $0.20\text{--}0.28$
  - Peak Kharif soybean/pulses canopy (August–September): $0.35\text{--}0.65$
  - Post-monsoon Rabi crop / senescence (October–December): $0.25\text{--}0.38$

### 3.2 Enhanced Vegetation Index (EVI)
In dense agricultural canopies, NDVI approaches saturation. EVI incorporates the blue band ($\rho_{\text{Blue}}$, $490\text{ nm}$, Sentinel-2 Band 2) to correct for atmospheric aerosol scattering and soil background reflectance:

$$\text{EVI} = G \times \frac{\rho_{\text{NIR}} - \rho_{\text{Red}}}{\rho_{\text{NIR}} + C_1 \cdot \rho_{\text{Red}} - C_2 \cdot \rho_{\text{Blue}} + L}$$

where $G = 2.5$, $C_1 = 6.0$, $C_2 = 7.5$, and $L = 1.0$.

### 3.3 Vegetation Condition Index (VCI)
Raw NDVI cannot be compared directly between distinct geographical zones (e.g., irrigated canals in Latur tehsil vs rainfed stony soils in Jalkot). VCI decouples climate-induced vegetation stress from the local ecological baseline by evaluating current NDVI relative to its historical extremes for that specific calendar month ($m$):

$$\text{VCI}_{v, m} = \left( \frac{\text{NDVI}_{v, m} - \text{NDVI}_{\min}(v, m)}{\text{NDVI}_{\max}(v, m) - \text{NDVI}_{\min}(v, m)} \right) \times 100$$

- $\text{VCI} \ge 60\%$: Optimal canopy health / favorable conditions.
- $40\% \le \text{VCI} < 60\%$: Normal vegetative development.
- $30\% \le \text{VCI} < 40\%$: Mild to moderate vegetative stress.
- $20\% \le \text{VCI} < 30\%$: Severe agricultural drought.
- $\text{VCI} < 20\%$: Extreme agricultural crisis / extensive crop failure.

### 3.4 Temperature Condition Index (TCI)
TCI is derived from Top-of-Atmosphere (TOA) and surface-calibrated thermal radiance measured by Landsat 8/9 Thermal Infrared Sensor (TIRS Band 10, $10.60\text{--}11.19\ \mu\text{m}$). Under water stress, vegetation closes stomata to conserve water, reducing latent heat flux (evaporative cooling) and dramatically elevating surface skin temperature. TCI inverts this relationship:

$$\text{TCI}_{v, m} = \left( \frac{\text{LST}_{\max}(v, m) - \text{LST}_{v, m}}{\text{LST}_{\max}(v, m) - \text{LST}_{\min}(v, m)} \right) \times 100$$

High temperatures produce low TCI values, indicating severe thermal stress.

### 3.5 Vegetation Health Index (VHI)
Vegetation Health Index integrates vegetative condition (VCI) and thermal evaporative stress (TCI) into a joint biophysical index:

$$\text{VHI} = \alpha \cdot \text{VCI} + (1 - \alpha) \cdot \text{TCI}$$

where $\alpha = 0.5$ represents equal biophysical weighting between moisture stress and thermal elevation.

### 3.6 Normalized Soil Moisture Index (NSMI)
NSMI is a Sentinel-2 shortwave infrared index that exploits the sensitivity of SWIR bands to leaf and soil water content:

$$\text{NSMI} = \frac{\rho_{\text{SWIR1}} - \rho_{\text{SWIR2}}}{\rho_{\text{SWIR1}} + \rho_{\text{SWIR2}}}$$

where $\rho_{\text{SWIR1}}$ = Sentinel-2 Band 11 ($1610\text{ nm}$) and $\rho_{\text{SWIR2}}$ = Sentinel-2 Band 12 ($2190\text{ nm}$). Higher values indicate wetter soil and canopy.

Because NSMI relies on optical Sentinel-2 imagery, it is **unavailable during monsoon cloud cover** (June–September), like NDVI and VCI. During these months, the CDI rests on SPI alone.

### 3.6b Soil Moisture Index from SAR (SMI)
SMI is derived from Sentinel-1 C-band ($5.405\text{ GHz}$) radar backscatter ($\sigma^\circ_{\text{VV}}$), normalised against dry and saturated baselines:

$$\text{SMI} = \frac{\sigma^\circ_{\text{VV}} - \sigma^\circ_{\text{dry}}}{\sigma^\circ_{\text{wet}} - \sigma^\circ_{\text{dry}}}$$

Because SAR microwaves penetrate cloud cover, SMI provides all-weather monitoring. It is used in the opt-in thermal formula (`config/composite_thermal.yaml`) but not in the default `cdi-v2026.12` formula.

### 3.7 Standardized Precipitation Index (SPI-1, SPI-3, SPI-6, SPI-12)
Precipitation from UCSB CHIRPS v2.0 ($0.05^\circ$ grid, daily blended satellite-gauge) is aggregated across rolling windows:

$$A_{k, t} = \sum_{i=0}^{k-1} P_{t - i}$$

- **SPI-1 (30 days):** Detects sudden meteorological dry spells and flash droughts during sowing.
- **SPI-3 (90 days):** Primary agricultural metric reflecting full Kharif or Rabi rainfall balance.
- **SPI-6 (180 days):** Captures seasonal transition and soil reservoir replenishment.
- **SPI-12 (365 days):** Reflects long-term groundwater recharge, reservoir levels, and multi-season hydrological drought.

Cumulative precipitation is fitted to a 2-parameter Gamma distribution $g(x; \alpha, \beta)$ and transformed to standard normal $Z \sim \mathcal{N}(0, 1)$.

### 3.8 Composite Drought Index (CDI)
CDI integrates meteorological deficit (SPI), vegetation condition (VCI), canopy greenness (NDVI), and surface moisture (NSMI) into a single composite:

$$\text{CDI}_{\text{nominal}} = 0.50 \cdot S(\text{SPI}) + 0.25 \cdot S(\text{VCI}) + 0.15 \cdot S(\text{NDVI}) + 0.10 \cdot S(\text{NSMI})$$

where $S(I)$ is the normalized severity score ($0.0 \le S \le 1.0$, where $1.0$ is extreme drought) for index $I$. See `config/composite.yaml` for the authoritative weights and normalisation methods.

---

## 4. Seasonal Phenological Cycles

The 11-year seasonal violin plots show the phenological timing of moisture, vegetative vigor, and drought onset:

![Seasonal Climatology Violins](../figures/05_distributions/d2_monthly_climatology.png)
<div class="figure-caption">Figure 2.3: Monthly climatology distributions (Jan–Dec) illustrating the monsoon expansion in July–September and dry season dormancy in March–May.</div>

![Monthly Index Heatmap Atlas](../figures/03_heatmaps/h1_index_heatmap_atlas_month_year.png)
<div class="figure-caption">Figure 2.4: Decadal calendar heatmap showing annual cycles of rainfall, SPI, NDVI, and CDI from 2016 to 2026.</div>

---

## 5. Drought Class Thresholds (USDM / WMO Parity)

| Drought Code | Severity Category | CDI Threshold | SPI-3 Threshold | VCI Threshold | Agricultural Impact Description |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **None** | Normal / Wet | $< 0.20$ | $> -0.50$ | $\ge 60\%$ | Optimal crop growth; adequate soil moisture. |
| **D0** | Abnormally Dry | $0.20 \le \text{CDI} < 0.35$ | $-0.80 \le \text{SPI} < -0.50$ | $40\text{--}60\%$ | Minor soil moisture deficit; sowing delays. |
| **D1** | Moderate Drought | $0.35 \le \text{CDI} < 0.50$ | $-1.30 \le \text{SPI} < -0.80$ | $30\text{--}40\%$ | Visible crop wilting; stunted vegetative growth. |
| **D2** | Severe Drought | $0.50 \le \text{CDI} < 0.65$ | $-1.60 \le \text{SPI} < -1.30$ | $20\text{--}30\%$ | Significant yield loss; fodder scarcity; water stress. |
| **D3** | Extreme Drought | $0.65 \le \text{CDI} < 0.80$ | $-2.00 \le \text{SPI} < -1.60$ | $10\text{--}20\%$ | Extensive crop failure; acute livestock distress. |
| **D4** | Exceptional Drought | $\ge 0.80$ | $\le -2.00$ | $< 10\%$ | Catastrophic crisis; emergency water rationing. |

---

<div class="chapter-nav-card">
  <a class="prev-link" href="../literature/">← Literature Review & Foundations</a>
  <a class="next-link" href="../equations/">Mathematical Formulations →</a>
</div>
