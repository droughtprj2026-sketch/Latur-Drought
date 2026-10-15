# Agent Workspace Guidelines: Drought Project Latur (2016–2026)

## Mandatory Starting Rule
Before planning, writing code, or running analyses in this repository, **you MUST always read and reference [memory.md](file:///d:/Droughtprj@2026/memory.md)**.

`memory.md` contains:
- Complete directory and folder path mappings
- Sentinel-2 and CHIRPS image locations, band structures, and resolutions
- Meteorological & remote sensing drought indices specifications (SPI-1, SPI-3, SPI-6, SPI-12, NDVI, NDMI, etc.)
- Shapefile boundary data (district, 10 tehsils, 954 villages)
- Catalog of all project scripts detailing their workflows, CLI arguments, and outputs

## Core Operational Constraints
1. **Never read raw `.tif` or `.tiff` rasters directly into context**. Use Python with `rasterio` or GDAL for metadata inspection and statistical analysis.
2. **Handle CRS conversions explicitly**: Sentinel-2 (`EPSG:32643`), CHIRPS (`EPSG:4326`), and `Latur.shp` (`LCC_WGS84`).
3. **Check `cloud_threshold_log.csv`** before flagging missing monsoon months (June–September).
4. **Follow the `PREFERRED_PREFIX = 'CHIRPS_'` rule** when resolving duplicate precipitation rasters.
