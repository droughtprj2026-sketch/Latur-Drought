import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sources · Near-Real Time Drought Monitoring",
};

export default function SourcesPage() {
  return (
    <article className="prose prose-slate dark:prose-invert max-w-4xl">
      <h1>Data sources</h1>

      <table>
        <thead>
          <tr><th>Source</th><th>Identifier</th><th>Use</th><th>Cadence</th><th>License</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>ESA Copernicus Sentinel-2 L2A</td>
            <td><code>COPERNICUS/S2_SR_HARMONIZED</code> (GEE)</td>
            <td>NDVI, EVI, VCI, VHI, PCI, RGB overlay</td>
            <td>~5-day revisit</td>
            <td>Copernicus free &amp; open</td>
          </tr>
          <tr>
            <td>UCSB CHIRPS Monthly</td>
            <td><code>UCSB-CHG/CHIRPS/monthly</code> (GEE)</td>
            <td>Monthly rainfall, SPI inputs</td>
            <td>Monthly</td>
            <td>Public domain</td>
          </tr>
          <tr>
            <td>UCSB CHIRPS Daily</td>
            <td><code>UCSB-CHG/CHIRPS/DAILY</code> (GEE)</td>
            <td>Partial-month tracking</td>
            <td>Daily</td>
            <td>Public domain</td>
          </tr>
          <tr>
            <td>MODIS LST</td>
            <td><code>MODIS/061/MOD11A1</code> (GEE)</td>
            <td>VHI thermal component</td>
            <td>1–2 days</td>
            <td>Public</td>
          </tr>
          <tr>
            <td>Latur district boundary</td>
            <td><code>data/shapefiles/latur_district.shp</code></td>
            <td>AOI, mapping</td>
            <td>Static</td>
            <td>Project</td>
          </tr>
          <tr>
            <td>Latur tehsil boundaries</td>
            <td><code>data/shapefiles/latur_tehsils.shp</code></td>
            <td>Zonal stats, dropdowns</td>
            <td>Static</td>
            <td>Project</td>
          </tr>
          <tr>
            <td>Latur village boundaries</td>
            <td><code>data/shapefiles/latur_villages.shp</code></td>
            <td>Zonal stats, dropdowns</td>
            <td>Static</td>
            <td>Project</td>
          </tr>
          <tr>
            <td>Basemap · OpenStreetMap</td>
            <td><code>tile.openstreetmap.org</code></td>
            <td>Base layer</td>
            <td>Live</td>
            <td>ODbL</td>
          </tr>
          <tr>
            <td>Basemap · Carto</td>
            <td><code>basemaps.cartocdn.com</code></td>
            <td>Base layer</td>
            <td>Live</td>
            <td>CC-BY</td>
          </tr>
          <tr>
            <td>Basemap · Esri World Imagery</td>
            <td><code>services.arcgisonline.com</code></td>
            <td>Satellite base</td>
            <td>Live</td>
            <td>Esri terms</td>
          </tr>
          <tr>
            <td>Basemap · OpenTopoMap</td>
            <td><code>tile.opentopomap.org</code></td>
            <td>Topographic base</td>
            <td>Live</td>
            <td>CC-BY-SA</td>
          </tr>
        </tbody>
      </table>

      <h2>Index formulas</h2>
      <ul>
        <li><strong>NDVI</strong> = (NIR − Red) / (NIR + Red)</li>
        <li><strong>EVI</strong> = 2.5 × (NIR − Red) / (NIR + 6·Red − 7.5·Blue + 1)</li>
        <li><strong>VCI</strong> = 100 × (NDVI − NDVIₘᵢₙ) / (NDVIₘₐₓ − NDVIₘᵢₙ) per calendar month</li>
        <li><strong>VHI</strong> = α · VCI + (1 − α) · TCI, α = 0.5</li>
        <li><strong>PCI</strong> = 100 × (P − Pₘᵢₙ) / (Pₘₐₓ − Pₘᵢₙ) per calendar month</li>
        <li><strong>SPI</strong> = Φ⁻¹(G(P_k)) where G is a Gamma CDF fit per
            calendar month with Thom (1958) MLE and the Stagge (2015)
            zero-correction. SPI reference climatology default: 1991–2020.</li>
        <li><strong>Composite CDI</strong> = ∑ᵢ wᵢ · Sᵢ / ∑ᵢ wᵢ (available i only).
            Default weights: SPI 0.30, VHI 0.20, VCI 0.15, NDVI 0.15, EVI 0.10,
            PCI 0.10. Thresholds (0..1): None &lt; 0.20, D0 &lt; 0.35, D1 &lt; 0.50,
            D2 &lt; 0.65, D3 &lt; 0.80, D4 ≥ 0.80. Formula version is
            <code> cdi-v2026.10</code>.</li>
      </ul>

      <h2>Citing this dashboard</h2>
      <pre>
Kadam, R. (2026). Near Real-Time Drought Monitoring System for Latur
District (Marathwada). [Software + dashboard]. Formula cdi-v2026.10.
      </pre>
    </article>
  );
}
