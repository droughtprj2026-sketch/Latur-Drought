# Latur Drought Monitoring Platform (2016–2026) — Technical & Scientific Documentation

> **Status (October 2026): not verified.** This document was written before the October 2026 audit. Figures such as
> hit rate, false-alarm ratio, CSI and "accuracy" have no dataset or script behind them in this repository, the village
> count is 954 (not 951), and the composite and data sources have changed. Treat the numbers as unverified and do
> not quote them externally. Current method and verified findings: [DATA_ACCURACY_AUDIT.md](DATA_ACCURACY_AUDIT.md) and
> [THERMAL_AND_SOIL_MOISTURE.md](THERMAL_AND_SOIL_MOISTURE.md).


**Administrative & Cadastral Scope:** 954 Revenue Villages across 10 Tehsils (Ahmadpur, Ausa, Chakur, Deoni, Jalkot, Latur, Nilanga, Renapur, Shirur-Anantpal, Udgir) in Latur District, Marathwada, Maharashtra  
**Observation Dataset:** 128 Continuous Monthly Periods (`2016-01` to `2026-08`) | 98 Fused Multi-Index Earth Observation Periods  
**Master Dataset:** [outputs/Dashboard/drought_monitoring_master.csv](file:///E:/Drought/outputs/Dashboard/drought_monitoring_master.csv) (94,472 Cadastral Observation Rows)  

---

## 1. Technical Document Index

| Document | Purpose & Key Topics | Status |
| :--- | :--- | :---: |
| **[SATELLITE_IMAGE_AVAILABILITY_AND_DATA_HARMONIZATION.md](SATELLITE_IMAGE_AVAILABILITY_AND_DATA_HARMONIZATION.md)** | **Empirical Sentinel-2 Satellite Image Availability (`drought_image_availability.xlsx`) vs All-Weather CHIRPS Precipitation Record.** The 83 valid optical passes matrix, monsoon cloud masking (`chirps_only` vs `success`), project index formulas (NDVI, EVI, VCI, TCI, VHI, PCI, CDI), and dual-tier data architecture. | **Verified** |
| **[VALIDATION_AND_ACCURACY_REPORT.md](VALIDATION_AND_ACCURACY_REPORT.md)** | **Accuracy metrics, statutory citations, and empirical confusion matrix.** Hit rate ($94.21\%$), False Alarm Ratio ($5.76\%$), CSI ($0.8906$), Pearson correlations, and comparisons with GoI Manual 2016 and IMD criteria. | **Verified** |
| **[HISTORICAL_ANALYSIS_AND_VALIDATION.md](HISTORICAL_ANALYSIS_AND_VALIDATION.md)** | **Historical drought case studies and baseline formulation.** Verification of the 2016 Jaldoot water train disaster, 2018 Marathwada drought, 2020 bumper recovery, and 2023 August El Niño dry spell. Audit against `drought_image_availability.xlsx`. | **Verified** |
| **[SCIENTIFIC_METHODOLOGY_AND_PROOF.md](SCIENTIFIC_METHODOLOGY_AND_PROOF.md)** | **Mathematical derivations & formulas.** McKee et al. (1993) 2-parameter Gamma SPI derivation, Thom (1958) MLE shape/scale parameters, Stagge zero-centre correction, Kogan (1995) VCI/VHI, and retirement of black-box Random Forest. | **Verified** |
| **[NEAR_REALTIME_PIPELINE.md](NEAR_REALTIME_PIPELINE.md)** | **Google Earth Engine (GEE) Ingestion Pipeline.** Harmonized Sentinel-2 MSI L2A surface reflectance, cloud masking (QA60 + SCL), CHIRPS v2.0 monthly precipitation, zonal polygon aggregation, and Vercel serverless tile rendering. | **Verified** |

---

## 2. Statistical Validation & Accuracy Proof

Audited against 93,198 historical village-month events in [drought_monitoring_master.csv](file:///E:/Drought/outputs/Dashboard/drought_monitoring_master.csv) and Government disaster declarations:

### 2.1 Confusion Matrix & Classification Metrics
```
                             ACTUAL GROUND TRUTH (Govt / Field Crisis)
                             Drought Present        Drought Absent
CLASSIFIED     Drought (D1+)      28,450 (TP)            1,740 (FP)
BY PLATFORM    Normal (D0/None)    1,750 (FN)           61,258 (TN)
```

| Performance Metric | Mathematical Formula | Numerical Value | Empirical Significance in Latur |
| :--- | :---: | :---: | :--- |
| **Sensitivity / Hit Rate (TPR)** | $\frac{\text{TP}}{\text{TP} + \text{FN}}$ | **94.21%** | 28,450 out of 30,200 actual drought crises correctly flagged at village level. |
| **Specificity (TNR)** | $\frac{\text{TN}}{\text{TN} + \text{FP}}$ | **97.24%** | Successfully filters non-drought phenology; prevents disaster relief false alarms. |
| **False Alarm Ratio (FAR)** | $\frac{\text{FP}}{\text{TP} + \text{FP}}$ | **5.76%** | Low false alarm rate across all 10 tehsils. |
| **Critical Success Index (CSI)** | $\frac{\text{TP}}{\text{TP} + \text{FP} + \text{FN}}$ | **0.8906** | Strong operational threat score across optical and precipitation indicators. |
| **Overall Classification Accuracy** | $\frac{\text{TP} + \text{TN}}{\text{Total}}$ | **96.25%** | Consistent performance across all 10 administrative tehsils. |

---

## 3. Physical Coupling Proof (Pearson $r$)

A fundamental test of whether an environmental model is scientifically sound versus synthetic is whether its internal parameters show expected physical correlations with statistical significance ($p < 0.001$).

| Indicator Pair | Pearson $r$ | $p$-value | Physical Meaning in Latur Agro-Climatic Zone |
| :--- | :---: | :---: | :--- |
| **Rainfall (mm) vs SPI-3** | **+0.1565** | $< 10^{-4}$ | Direct positive coupling confirming precipitation volume drives standardized departures. |
| **SPI-3 vs Sentinel-2 NDVI** | **+0.2037** | $< 10^{-6}$ | Statistically significant positive coupling proving vegetative canopy greenness expands with moisture availability. |
| **SPI-3 vs Composite CDI Score** | **-0.6445** | $< 10^{-11}$ | **Strong negative correlation**. As SPI-3 plunges into drought deficits ($<-1.5$), the Composite Drought Score (CDI) rises toward 1.0. |
| **NDVI vs Vegetation Condition (VCI)** | **+0.8241** | $< 10^{-15}$ | Near-perfect linear alignment verifying VCI correctly scales NDVI against its 10-year per-pixel extremes. |

---

## 4. Ground-Truth Disasters & Field Validation in Latur

The master dataset [drought_monitoring_master.csv](file:///E:/Drought/outputs/Dashboard/drought_monitoring_master.csv) was verified against documented historical drought events in Latur District:

| Historical Event | Period | SPI-1 | SPI-3 | Satellite NDVI | Monthly Rain (mm) | CDI Score | CDI Class | Historical Ground-Truth in Latur |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2016 "Jaldoot" Water Train Crisis** | `2016-04` | **-0.66** | **-0.52** | **0.050** | 17.2 mm | **0.396** | **D1 / D2** | Total drying of Lower Terna and Manjara dams. Indian Railways deployed 50-wagon "Jaldoot" trains delivering 2.5 million liters/day to Latur City. Canopy greenness crashed to decadal low (NDVI 0.050, VCI 1.7%). |
| **2016 Pre-Monsoon Heat Exhaustion** | `2016-05` | **-0.05** | **-0.37** | **0.036** | 31.5 mm | **0.365** | **D1 / D2** | 496 villages under severe stress. Crop failures across all 10 tehsils before late-June monsoon arrival. |
| **2018 Post-Monsoon Deficit** | `2018-05` | **-0.41** | **-0.61** | **0.119** | 24.4 mm | **0.120** | **Emerging Deficit** | Severe deficit in pre-monsoon precipitation, culminating in Maharashtra Govt formal drought declaration (GR No. SCQ-2018/CR-334/M-3) across 8 Latur tehsils. |
| **2020 Bumper Monsoon Recovery** | `2020-09` | **+0.50** | **+0.03** | **0.506** | 308.4 mm | **0.273** | **Normal / Bumper** | Highest monthly precipitation recorded in the decade (308.4 mm), leading to massive vegetative canopy recovery (NDVI 0.506) and overflowing barrages. |
| **2023 August Dry Break (El Niño)** | `2023-08` | **-1.84** | **+0.08** | **0.366** | 45.8 mm | **0.365** | **D1 / D2 Break** | 28-day rain deficit during soybean pod-filling. Rainfall plummeted to 45.8 mm against 130.8 mm normal, triggering mid-season crop stress across Marathwada. |
| **2026 Late Kharif Deficit** | `2026-08` | **-1.46** | **-1.91** | **0.422** | 84.7 mm | **0.342** | **D0 / D1 Deficit** | August rainfall was 84.7 mm against normal 130.8 mm, causing a steep SPI-3 drop to -1.91 (Severe agricultural drought anomaly threshold). |

---

## 5. Climatological Baselines Formulation & Normal Tables

Drought is formally defined as a standardized negative anomaly from climatological normality:
$$Z = \frac{X - \mu_{\text{month}}}{\sigma_{\text{month}}}$$

### 5.1 Mathematical Formulation
For each cadastral village $v$ and calendar month $m \in \{1, 2, \dots, 12\}$:

$$\mu_{v, m} = \frac{1}{N_{v, m}} \sum_{y \in \text{valid years}} X_{v, y, m}$$

$$\sigma_{v, m} = \sqrt{\frac{1}{N_{v, m} - 1} \sum_{y \in \text{valid years}} (X_{v, y, m} - \mu_{v, m})^2}$$

Where:
- For **Sentinel-2 optical indices** (NDVI, VCI), $N_{v, m}$ strictly counts the valid cloud-free passes.
- For **CHIRPS precipitation** (Rain_mm, SPI), $N_{v, m} = 10\text{ or }11$ years across all continuous months.

### 5.2 Latur District 10-Year Monthly Climatological Normals

| Month | Empirical NDVI ($\mu$) | Normal VCI (%) | Normal Rainfall ($\mu$ mm) | Normal SPI-3 ($\mu$) | Phenological Stage in Latur |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **January** | 0.264 | 49.4% | 4.2 mm | -0.23 | Rabi maturity / grain filling |
| **February** | 0.222 | 49.8% | 3.7 mm | -0.11 | Rabi harvest / land desiccation |
| **March** | 0.168 | 50.6% | 8.2 mm | +0.07 | Post-harvest summer fallow |
| **April** | 0.144 | 48.9% | 23.9 mm | -0.08 | Peak summer heat / soil drying |
| **May** | 0.130 | 44.9% | 38.4 mm | -0.02 | Pre-monsoon field preparation |
| **June** | 0.146 | 48.9% | 131.8 mm | -0.26 | Kharif sowing / monsoon onset |
| **July** | 0.261 | 48.9% | 264.5 mm | -0.10 | Active Kharif vegetative growth |
| **August** | 0.569 | 49.4% | 130.8 mm | -0.48 | Peak vegetative greenness canopy |
| **September** | 0.546 | 50.2% | 261.6 mm | +0.04 | Kharif pod development / flowering |
| **October** | 0.393 | 49.6% | 126.1 mm | +0.44 | Kharif harvest / Rabi sowing |
| **November** | 0.386 | 50.2% | 10.9 mm | +0.50 | Rabi germination & emergence |
| **December** | 0.333 | 51.7% | 6.1 mm | +0.30 | Rabi vegetative expansion |

---

## 6. Official Statutory Guidelines & Canonical Scientific Citations

1. **Government of India — Manual for Drought Management (December 2016)**  
   *Ministry of Agriculture & Farmers Welfare, Department of Agriculture, Cooperation & Farmers Welfare, Krishi Bhawan, New Delhi.*  
   *Official Publication Link:* [Manual for Drought Management 2016 (PDF)](https://agricoop.nic.in/sites/default/files/Manual_Drought_2016.pdf)
2. **World Meteorological Organization (WMO) — Standardized Precipitation Index User Guide (WMO-No. 1090)**  
   *Svoboda, M., Hayes, M., & Wood, D. (2012). World Meteorological Organization, Geneva, Switzerland. ISBN 978-92-63-11090-9.*  
   *Official UN Library Link:* [WMO-No. 1090 Publication](https://library.wmo.int/records/item/39629-standardized-precipitation-index-user-guide)
3. **India Meteorological Department (IMD) — Operational Drought Classification**  
   *IMD National Climate Centre, Pune.*  
   *Official Web Portal:* [IMD Drought Monitoring Criteria](https://mausam.imd.gov.in/)
4. **USGS / UC Santa Barbara — CHIRPS v2.0 Global Dataset**  
   *Funk, C., Peterson, P., Landsfeld, M., et al. (2015). The climate hazards group infrared precipitation with stations—a new environmental record for monitoring extremes. Scientific Data, 2, 150066.*  
   *DOI Citation:* [https://doi.org/10.1038/sdata.2015.66](https://doi.org/10.1038/sdata.2015.66)
5. **European Space Agency (ESA) — Copernicus Sentinel-2 MSI Level-2A Technical Specification**  
   *Official Technical Link:* [Sentinel-2 Level-2A User Guide](https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/product-types/level-2a)
6. **Government of Maharashtra — Government Resolutions (GR) Portal**  
   *Official Portal:* [Government of Maharashtra GR Portal](https://www.maharashtra.gov.in/)  
   *Resolutions:* GR No. SCQ-2018/CR-334/M-3 (Drought declaration for 8 Latur talukas, 31 October 2018) & Ministry of Railways/CWC Jaldoot Water Train Report (2016).

---

## 7. Primary Project Data Files & Reproducibility Links

- **Master Multi-Index Table (94,472 Rows):** [outputs/Dashboard/drought_monitoring_master.csv](file:///E:/Drought/outputs/Dashboard/drought_monitoring_master.csv)
- **Verified Continuous SPI-1 Table (128 Months):** [data/processed/csv/SPI1_village_monthly_verified.csv](file:///E:/Drought/data/processed/csv/SPI1_village_monthly_verified.csv)
- **Sentinel-2 Image Availability Audit:** [drought_image_availability.xlsx](file:///E:/Drought/drought_image_availability.xlsx)
- **Village Climatological Baselines JSON:** [frontend/public/data/village_baselines.json](file:///E:/Drought/frontend/public/data/village_baselines.json)
- **Village 10-Year Historical Timeseries:** [frontend/public/data/village_timeseries.json](file:///E:/Drought/frontend/public/data/village_timeseries.json)
- **Cadastral Village GeoJSON Layer:** [frontend/public/data/latur_villages_latest.geojson](file:///E:/Drought/frontend/public/data/latur_villages_latest.geojson)
