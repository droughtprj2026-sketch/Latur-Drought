# Scientific Literature Review & Theoretical Foundations

## 1. Evolution of Remote Sensing-Based Drought Monitoring

Drought is a creeping natural hazard characterized by complex, multi-temporal interactions between meteorological precipitation deficits, soil moisture depletion, vegetation physiological stress, and hydrological storage anomalies (Wilhite & Glantz, 1985; Mishra & Singh, 2010).

Historically, drought monitoring in semi-arid tropics relied almost exclusively on ground-based meteorological station networks measuring point rainfall (e.g., India Meteorological Department standard rain gauges). However, ground stations suffer from severe spatial interpolation uncertainties in convective tropical rainfall regimes (McKee et al., 1993; Vicente-Serrano et al., 2010).

The advent of satellite Earth Observation (EO) revolutionized drought assessment by providing continuous, spatially exhaustive observations of land surface biophysical parameters:

```
+---------------------------------------------------------------------------------------------+
|                                DROUGHT PROPAGATION SEQUENCE                                 |
+---------------------------------------------------------------------------------------------+
|  Atmospheric Circulation Anomaly                                                            |
|         │                                                                                   |
|         ▼                                                                                   |
|  Meteorological Drought   ──►  Rainfall Deficit (CHIRPS v2.0, SPI-1 / SPI-3 / SPI-6)        |
|         │                                                                                   |
|         ▼                                                                                   |
|  Agricultural Drought     ──►  Soil Moisture Depletion (Sentinel-2 SWIR NSMI)               |
|         │                      Canopy Stress & Wilting (Sentinel-2 MSI NDVI, VCI)           |
|         │                      Thermal Evaporative Stress (Landsat 8/9 LST, TCI)            |
|         ▼                                                                                   |
|  Hydrological Drought     ──►  Reservoir & Groundwater Depletion (SPI-12, Runoff Deficit)   |
|         │                                                                                   |
|         ▼                                                                                   |
|  Socio-Economic Drought   ──►  Crop Loss, Fodder Scarcity, Municipal Water Deprivation      |
+---------------------------------------------------------------------------------------------+
```

---

## 2. Benchmark International & National Drought Frameworks

Our system is engineered to align strictly with authoritative global and national drought surveillance standards:

### 2.1 WMO & GWP Standardized Precipitation Index Guidelines
The **World Meteorological Organization (WMO)** and the **Global Water Partnership (GWP)** established the Standardized Precipitation Index (SPI) as the definitive global meteorological drought metric (WMO-No. 1090, *Standardized Precipitation Index User Guide*, 2012). SPI normalizes precipitation accumulations across varying temporal windows (1, 3, 6, 12, 24 months) by fitting a two-parameter Gamma distribution, enabling direct comparisons of dryness across differing climatological regimes.

### 2.2 U.S. Drought Monitor (USDM) Severity Categorization
Developed cooperatively by the USDA, NOAA, and the National Drought Mitigation Center (NDMC) at the University of Nebraska-Lincoln (Svoboda et al., 2002), the **USDM** established the percentile-based 5-class severity standard:

$$\text{USDM Classes:}\quad \text{D0 (Abnormally Dry, 20th–30th percentile)} \longrightarrow \text{D4 (Exceptional Drought, } \le \text{2nd percentile)}$$

Our system maps both physical indices and composite indicators directly to this USDM/WMO severity scale, ensuring cross-institutional comparability.

### 2.3 Indian National Manual for Drought Management (2016)
The Ministry of Agriculture and Farmers Welfare, Government of India, promulgated the revised statutory *Manual for Drought Management (2016)*, mandating a multi-criteria trigger mechanism:

1. **Trigger 1 (Mandatory):** Rainfall deficiency (SPI or Deviation from Normal $\le -1.0$).
2. **Trigger 2 (Impact Indicators):** Remote sensing vegetative indices (NDVI/VCI deviation), soil moisture status, and reservoir storage levels.

By integrating CHIRPS SPI, Sentinel-2 VCI, and Sentinel-1 soil moisture into an automated composite, this platform provides direct operational support for Trigger 1 and Trigger 2 scientific verification.

---

## 3. Scientific Literature Grounding for Individual Indices

### 3.1 Normalized Difference Vegetation Index (NDVI) & Enhanced Vegetation Index (EVI)
- **Rouse et al. (1974); Tucker (1979):** Established NDVI as the normalized contrast between red absorption by chlorophyll-a ($665\text{ nm}$) and near-infrared (NIR) scattering by mesophyll cell structures ($842\text{ nm}$).
- **Huete et al. (2002):** Developed EVI to overcome canopy saturation in high-biomass regimes and minimize soil background brightness in semi-arid sparse vegetation through blue-band atmospheric correction.

### 3.2 Vegetation Condition Index (VCI)
- **Kogan (1990, 1995, 1997):** Demonstrated that raw NDVI reflects both climatic fluctuations and local ecological carrying capacity (e.g., irrigated crops vs barren plateau). Kogan introduced VCI to isolate the climatic drought signal by normalizing current NDVI against its multi-year historical minimum and maximum for that specific calendar month.
- VCI provides a universal $0\text{--}100\%$ scale, where values $<40\%$ indicate agricultural drought and $<20\%$ indicate severe crop failure.

### 3.3 Temperature Condition Index (TCI) & Vegetation Health Index (VHI)
- **Kogan (1995); Karnieli et al. (2010):** Demonstrated that vegetation thermal radiance (Land Surface Temperature, LST) rises sharply under soil moisture deficit due to stomatal closure and transpiration cessation. TCI normalizes LST inversely, such that lower TCI values correspond to higher thermal stress.
- **VHI** combines VCI and TCI in an equal or weighted balance, reflecting joint moisture and thermal vegetative strain.

### 3.4 Synthetic Aperture Radar (SAR) Soil Moisture (SMI / NSMI)
- **Ulaby et al. (1982); Wagner et al. (1999); Bauer-Marschallinger et al. (2019):** Established the physical sensitivity of C-band SAR backscatter ($\sigma^\circ$) to surface soil dielectric permittivity. In cloud-shrouded monsoon regimes where optical sensors fail, Sentinel-1 VV/VH backscatter provides continuous surface soil moisture estimates.

### 3.5 Composite Drought Indices (CDI) & Re-weighting Theory
- **Anderson et al. (2011); Sepulcre-Canto et al. (2012); Hao & AghaKouchak (2013):** Proved that univariate drought indices fail to capture joint agricultural-meteorological crises. Composite approaches provide robust, holistic risk detection.
- **Why Random Forest Was Retired:** In earlier phases, machine learning classifiers (Random Forest) were explored. However, as documented by Zscheischler et al. (2018) and Rudin (2019), learned black-box classifiers often produce non-monotonic artifacts, uninterpretable predictions during rare out-of-distribution extremes, and lack physical traceability. Our platform retired Random Forest in favor of a **transparent, weighted linear composite** with dynamic re-weighting under missing components (`config/composite.yaml`).

---

## 4. Key Academic References

1. **Kogan, F. N. (1990).** Remote sensing of weather impacts on vegetation in non-homogeneous areas. *International Journal of Remote Sensing*, 11(8), 1405–1419.
2. **Kogan, F. N. (1995).** Droughts of the late 1980s in the United States as derived from NOAA polar-orbiting satellite data. *Bulletin of the American Meteorological Society*, 76(5), 655–668.
3. **McKee, T. B., Doesken, N. J., & Kleist, J. (1993).** The relationship of drought frequency and duration to time scales. *Proceedings of the 8th Conference on Applied Climatology*, 17(22), 179–183.
4. **Svoboda, M., et al. (2002).** The Drought Monitor. *Bulletin of the American Meteorological Society*, 83(8), 1181–1190.
5. **Vicente-Serrano, S. M., Beguería, S., & López-Moreno, J. I. (2010).** A multiscalar drought index sensitive to global warming: The Standardized Precipitation Evapotranspiration Index. *Journal of Climate*, 23(7), 1696–1718.
6. **Funk, C., et al. (2015).** The climate hazards group infrared precipitation with stations—a new environmental record for monitoring extremes. *Scientific Data*, 2(1), 1–21.
7. **Ministry of Agriculture & Farmers Welfare, GoI (2016).** *Manual for Drought Management*. Department of Agriculture, Cooperation & Farmers Welfare, New Delhi.
8. **Sepulcre-Canto, G., et al. (2012).** Development of a Combined Drought Indicator to detect agricultural drought in Europe. *Natural Hazards and Earth System Sciences*, 12(11), 3519–3531.

