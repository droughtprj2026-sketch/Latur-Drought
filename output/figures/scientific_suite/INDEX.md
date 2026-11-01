# Scientific visualization suite

Generated 2026-11-01T10:50:02

| item | value |
| --- | --- |
| Study area | Latur |
| Period | 2016-01 to 2026-10 (2016-2026) |
| Villages | 954 |
| Tehsils | 10 |
| Village-months | 101,124 |
| Figures | 5 |

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
  - Per-year temporal and spatial completeness for each source, against a 90% target.
  - Data: village_with_baseline.csv
- `01_image_availability/a5_component_completeness.png`
  - Distribution of available CDI components per village-month and the drought class reached at each level.
  - Data: village_with_baseline.csv
