# Operational Workflows & Runbooks

This runbook documents standard operational procedures for running weekly pipeline updates, rebuilding scientific visualizations, and deploying documentation.

---

## 1. Running Operational Weekly Updates

To execute the weekly automated ingest and publish pipeline:

```bash
python scripts/realtime/realtime_update.py
```

### Execution Steps
1. Ingests any new Sentinel-2 or CHIRPS rasters listed in raw directories.
2. Updates `manifests/sentinel.json` and `manifests/chirps.json`.
3. Recalculates rolling SPI windows affected by new precipitation data.
4. Updates village-level CDI scores and drought classifications.
5. Emits production files to `outputs/Dashboard/`:
   - `latest_status.json`
   - `drought_monitoring_master.csv`
   - `data_availability.json`
   - `processing_manifest.json`
6. Synchronizes updated records with Supabase PostgreSQL and Storage bucket.

---

## 2. Rebuilding the Scientific Visualization & Animation Suite

To re-render the full 143-figure cartographic atlas, PowerPoint animations, and interactive HTML suite:

```bash
# Generate the full publication figure suite
python scripts/analysis/generate_scientific_visualizations.py

# Generate PowerPoint presentation GIF animations
python -c "from scripts.analysis.scientific_suite import animations, data; panel = data.load_panel(); animations.build(panel)"

# Regenerate interactive HTML gallery and INDEX.md
python -c "from scripts.analysis.scientific_suite import report, data; panel = data.load_panel(); meta = {'district': 'Latur District', 'period': f'{panel.period.min()} to {panel.period.max()}', 'villages': 954, 'tehsils': 10, 'rows': f'{len(panel):,}', 'village_months': f'{len(panel):,}', 'completeness': '99.2%'}; report.scan_and_index_disk(); report.write_html(meta); report.write_markdown(meta)"
```

---

## 3. Serving & Building the MkDocs Documentation Website

### 3.1 Live Development Preview
To preview the documentation website locally with hot reloading:

```bash
mkdocs serve
```
Open [http://localhost:8000](http://localhost:8000) in your web browser.

### 3.2 Compiling the Production Static Site
To compile the documentation into a standalone, deployable static website:

```bash
mkdocs build --strict
```
The compiled HTML, CSS, JavaScript, and asset files are written to the `site/` directory.

### 3.3 Deploying to GitHub Pages
To publish the documentation directly to GitHub Pages:

```bash
mkdocs gh-deploy --clean
```

