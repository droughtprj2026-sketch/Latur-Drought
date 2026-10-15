---
description: Always reference memory.md for repository paths, imagery, indices, and scripts
globs: *
---

# Always Reference memory.md

At the start of every task, the agent must inspect and reference [memory.md](file:///d:/Droughtprj@2026/memory.md) to understand:
1. All directory structures and absolute file paths (`output/sentinel/`, `output/chirps/`, `output/charts/`, etc.).
2. Raster locations, band orders (B2, B3, B4, B8, B11, B12), and coordinate reference systems (`EPSG:32643` vs `EPSG:4326`).
3. Drought indices calculation specifications (SPI scales 1, 3, 6, 12, McKee classifications, spectral indices).
4. Detailed descriptions of all Python scripts and their invocation methods.
5. Strict rule prohibiting reading or dumping raw `.tif` / `.tiff` imagery into context.
