# Scientific visualization suite

Generated 2026-11-01T11:09:30

| item | value |
| --- | --- |
| Study area | Latur |
| Period | 2016-01 to 2026-10 (2016-2026) |
| Villages | 954 |
| Tehsils | 10 |
| Village-months | 124,020 |
| Figures | 53 |

## 01_image_availability - Image availability and sampling completeness

- `01_image_availability/a1_tehsil_year_availability.png`
  - Sentinel-2, Sentinel-1 and CHIRPS coverage (%) for every tehsil and year.
  - Data: village_with_baseline.csv
- `01_image_availability/a2_month_year_availability.png`
  - Month x year availability grid for all three sources; grey cells are months with no observation at all.
  - Data: village_with_baseline.csv
- `01_image_availability/a3_tehsil_availability_ranking.png`
  - Tehsil-level coverage bars for each source, plus the district-wide figure with the min-max tehsil range.
  - Data: village_with_baseline.csv
- `01_image_availability/a4_annual_availability_trend.png`
  - Per-year count of months present and the spatial coverage of each source within those months.
  - Data: village_with_baseline.csv
- `01_image_availability/a5_component_completeness.png`
  - Distribution of available CDI components per village-month and the drought class reached at each level.
  - Data: village_with_baseline.csv

## 02_correlation - Inter-index correlation structure (Pearson and Spearman)

- `02_correlation/c1_pearson_matrix.png`
  - Pearson correlation matrix for all eleven indices over the full study period.
  - Data: village_with_baseline.csv
- `02_correlation/c2_spearman_matrix.png`
  - Spearman rank correlation matrix for the same eleven indices.
  - Data: village_with_baseline.csv
- `02_correlation/c3_pearson_vs_spearman_agreement.png`
  - Per-pair comparison of Pearson and Spearman coefficients and their signed difference matrix.
  - Data: village_with_baseline.csv
- `02_correlation/c4_significance_matrices.png`
  - Significance stars over -log10(p) for Pearson and Spearman correlation.
  - Data: village_with_baseline.csv
- `02_correlation/c5_annual_pearson_grid.png`
  - Year-by-year Pearson correlation grid for the six core indices.
  - Data: village_with_baseline.csv
- `02_correlation/c6_annual_spearman_grid.png`
  - Year-by-year Spearman correlation grid for the six core indices.
  - Data: village_with_baseline.csv
- `02_correlation/c7_seasonal_pearson_spearman.png`
  - Wet-season and dry-season correlation matrices, computed with both Pearson and Spearman.
  - Data: village_with_baseline.csv
- `02_correlation/c8_tehsil_pearson_heatmap.png`
  - Per-tehsil Pearson correlation for fourteen index pairs.
  - Data: village_with_baseline.csv
- `02_correlation/c9_tehsil_spearman_heatmap.png`
  - Per-tehsil Spearman correlation for the same fourteen index pairs.
  - Data: village_with_baseline.csv
- `02_correlation/c10_key_correlation_forest.png`
  - Forest plot of the headline index correlations with 95% confidence intervals, Pearson and Spearman.
  - Data: village_with_baseline.csv

## 03_heatmaps - Full heatmap atlas of every index over time and space

- `03_heatmaps/h1_index_heatmap_atlas_month_year.png`
  - Month x year mean of every index in the registry, one panel per index.
  - Data: village_with_baseline.csv
- `03_heatmaps/h2_index_heatmap_atlas_tehsil_year.png`
  - Tehsil x year mean of every index in the registry, rows ranked by ten-year mean.
  - Data: village_with_baseline.csv
- `03_heatmaps/h3_village_year_clustermap.png`
  - Clustered village x year matrix of annual mean CDI, revealing drought-exposure archetypes.
  - Data: village_with_baseline.csv
- `03_heatmaps/h4_drought_frequency_heatmaps.png`
  - Drought-occurrence frequency by tehsil x year and by month x year.
  - Data: village_with_baseline.csv
- `03_heatmaps/h5_class_share_by_year.png`
  - Percentage of scored village-months in each drought class, year by year.
  - Data: village_with_baseline.csv

## 04_index_relationships - Index relationships, regressions and response lags

- `04_index_relationships/r1_core_scatter_regressions.png`
  - Four core scatter regressions with OLS fit, 95% confidence band and full diagnostics.
  - Data: village_with_baseline.csv
- `04_index_relationships/r2_pairplot_matrix.png`
  - Seaborn pairplot of the five core indices coloured by drought class, with KDE margins.
  - Data: village_with_baseline.csv
- `04_index_relationships/r3_hexbin_density.png`
  - Hexbin density plots of the two central couplings with both correlation coefficients.
  - Data: village_with_baseline.csv
- `04_index_relationships/r4_regression_by_tehsil.png`
  - Per-tehsil SPI-3 vs NDVI scatter regressions with r and n annotated.
  - Data: village_with_baseline.csv
- `04_index_relationships/r5_response_lag.png`
  - Pooled lagged correlations of SPI-1/3/6 against NDVI, VCI and NSMI for lags of zero to six months.
  - Data: village_with_baseline.csv
- `04_index_relationships/r6_index_agreement.png`
  - NDVI/EVI agreement, VCI/VHI agreement and the NDVI-EVI residual distribution.
  - Data: village_with_baseline.csv

## 05_distributions - Index distributions and drought-class separation

- `05_distributions/d1_index_distributions.png`
  - Histogram plus KDE for every index, with mean, median, n and skewness.
  - Data: village_with_baseline.csv
- `05_distributions/d2_monthly_climatology.png`
  - Monthly boxplots for rainfall, NDVI, NSMI and CDI showing the seasonal cycle and its spread.
  - Data: village_with_baseline.csv
- `05_distributions/d3_class_separation.png`
  - Violin plots of each index by drought class with Kruskal-Wallis tests, plus class frequencies.
  - Data: village_with_baseline.csv
- `05_distributions/d4_village_variability.png`
  - Ranked village mean CDI with per-village p10-p90 band, plus the fourteen most exposed villages.
  - Data: village_with_baseline.csv
- `05_distributions/d5_component_contributions.png`
  - Distribution of each component's contribution to the CDI and its presence across village-months.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_CDI.png`
  - Distribution of CDI against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_NDVI.png`
  - Distribution of NDVI against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_Rain.png`
  - Distribution of Rain against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_SPI-1.png`
  - Distribution of SPI-1 against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_SPI-3.png`
  - Distribution of SPI-3 against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_SPI-6.png`
  - Distribution of SPI-6 against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_SPI-12.png`
  - Distribution of SPI-12 against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_EVI.png`
  - Distribution of EVI against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_VCI.png`
  - Distribution of VCI against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_VHI.png`
  - Distribution of VHI against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv
- `05_distributions/per_index/d6_distribution_NSMI.png`
  - Distribution of NSMI against all other indices: raw density, standardised overlay and ECDF.
  - Data: village_with_baseline.csv

## 06_temporal_analysis - Temporal evolution and drought episodes

- `06_temporal_analysis/t1_hovmoller_cdi_spi.png`
  - Month x year Hovmoller heatmaps of the CDI and SPI-3.
  - Data: village_with_baseline.csv
- `06_temporal_analysis/t2_annual_series_trends.png`
  - Annual series of CDI, drought share, SPI-3, SPI-12, rainfall and NDVI with Mann-Kendall and Sen's slope.
  - Data: village_with_baseline.csv
- `06_temporal_analysis/t3_class_composition.png`
  - Stacked area and stacked bars of the monthly and annual drought-class composition.
  - Data: village_with_baseline.csv
- `06_temporal_analysis/t4_drought_extent.png`
  - Monthly share of villages in any drought and in severe-or-worse drought, with a 3-month running mean.
  - Data: village_with_baseline.csv
- `06_temporal_analysis/t5_spi12_episodes.png`
  - District mean SPI-12 with SPI class bands and detected multi-month drought episodes.
  - Data: village_with_baseline.csv
- `06_temporal_analysis/t6_tehsil_trends.png`
  - Small-multiple annual CDI series for every tehsil with Sen's slope and Mann-Kendall p-value.
  - Data: village_with_baseline.csv

## 07_spatial_analysis - Spatial pattern across villages and tehsils

- `07_spatial_analysis/s1_village_mean_cdi.png`
  - Choropleth of ten-year mean CDI per village with the most exposed villages labelled.
  - Data: village_with_baseline.csv + latur_villages_latest.geojson
- `07_spatial_analysis/s2_village_spi_ndvi_correlation.png`
  - Village choropleth and histogram of the SPI-3 vs NDVI Pearson correlation.
  - Data: village_with_baseline.csv + latur_villages_latest.geojson
- `07_spatial_analysis/s3_village_trend.png`
  - Choropleth of Sen's slope of annual mean CDI per village.
  - Data: village_with_baseline.csv + latur_villages_latest.geojson
- `07_spatial_analysis/s4_annual_drought_atlas.png`
  - Small-multiple annual choropleths of mean village CDI.
  - Data: village_with_baseline.csv + latur_villages_latest.geojson
- `07_spatial_analysis/s5_tehsil_vulnerability_ranking.png`
  - Tehsil vulnerability ranking and its choropleth, built from mean CDI, drought frequency and trend.
  - Data: village_with_baseline.csv + latur_villages_latest.geojson
