import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Method · Near Real-Time Drought Monitoring System",
};

export default function AboutPage() {
  return (
    <article className="prose prose-slate mx-auto max-w-3xl px-4 py-8">
      <h1>Method and limits</h1>

      <p className="lead">
        The <strong>Near Real-Time Drought Monitoring System</strong> for Latur district, Marathwada, is developed by
        the <strong>Department of Geoinformatics, Shivaji University</strong>. It scores each of the 954 revenue
        villages every month from satellite data and classifies drought with a transparent weighted composite.
      </p>

      <h2>Project team</h2>
      <p>
        <strong>Developers:</strong> Rajnandini U. Kadam, Aishwarya B. Jagtap, Pavan S. Devkar, Shital B. Gurav,
        Trupti U. Jadhav.
        <br />
        <strong>Project guide:</strong> Dr. Sachin S. Panhalkar, Head of Department, Department of Geography.
      </p>

      <h2>How current is it?</h2>
      <p>
        The pipeline checks for new data weekly, but every input is a monthly product, so the maps change when a new
        month becomes available. The status bar at the top of the dashboard shows the last month of each source and
        when the pipeline last ran. A month that a source has not fully published stays empty.
      </p>

      <h2>Data</h2>
      <ul>
        <li><strong>Vegetation:</strong> Sentinel-2 L2A (<code>COPERNICUS/S2_SR_HARMONIZED</code>), cloud-masked with
          the scene classification layer, monthly median, village mean: NDVI and VCI.</li>
        <li><strong>Rainfall:</strong> CHIRPS daily totals summed per month (<code>UCSB-CHG/CHIRPS/DAILY</code>): SPI
          and PCI. CHIRPS is the rainfall reference. SPI is fitted on the 2016 to present record, about ten years per
          calendar month, so extreme values deserve caution.</li>
        <li><strong>Land-surface temperature:</strong> Sentinel-2 has no thermal band, so LST comes from Landsat 8 and 9
          surface temperature (30 m, clear-sky observations): TCI, and VHI = 0.5 VCI + 0.5 TCI.</li>
        <li><strong>Soil moisture (relative):</strong> Sentinel-1 VV radar backscatter (10 m). SMI is each village&apos;s
          own position between its lowest and highest value for the calendar month. It is not volumetric soil moisture.</li>
      </ul>
      <p>The thermal and soil-moisture inputs are part of the opt-in formula <code>cdi-v2026.11-thermal</code>.
        The status bar and the legend state which formula is active.</p>

      <h2>Composite drought index (CDI)</h2>
      <p>
        Each input is converted to a 0 to 1 drought intensity against the village&apos;s own record, then combined with
        the weights in <code>config/composite.yaml</code> (or <code>composite_thermal.yaml</code>). A missing input is
        left out of the sum, never replaced by zero; below the minimum number of inputs the month is not scored.
        Classes: not in drought (&lt; 0.20), D0 (0.20 to 0.35), D1 (0.35 to 0.50), D2 (0.50 to 0.65), D3 (0.65 to 0.80),
        D4 (0.80 and above). No learned classifier is used.
      </p>

      <h2>Layers</h2>
      <p>
        Current-condition layers (CDI, SPI-1, rainfall, NDVI, VCI, VHI, TCI, SMI, LST) are on the main dashboard.
        SPI-3, SPI-6 and SPI-12 accumulate rainfall over 3 to 12 months and change only when a new month is published;
        they are on the map page under &quot;Long-term accumulation&quot;. Baseline layers show the normal for the
        calendar month and the departure from it.
      </p>

      <h2>Known limits</h2>
      <ul>
        <li>Rainfall is read on a ~5 km grid, so neighbouring villages can share a value.</li>
        <li>EVI in the stored record is saturated and is not shown or used by the thermal formula.</li>
        <li>With about seven values per village and calendar month, a single month&apos;s class can change when the record
          grows. Read single-month classes as indicative.</li>
        <li>Landsat LST has gaps in the monsoon; TCI and VHI are then empty.</li>
        <li>The thermal and soil-moisture indices have not yet been validated against ground data.</li>
      </ul>
      <p>The full list, with measurements, is in <code>docs/DATA_ACCURACY_AUDIT.md</code> in the repository.</p>

      <h2>My area</h2>
      <p>
        An uploaded GeoJSON is analysed in your browser against the village polygons. Nothing is uploaded to a server.
      </p>

      <h2>Open source</h2>
      <p>
        Processing scripts, the Supabase migration and this web app are in the project repository. See the
        <a href="/sources"> Sources</a> page for data citations.
      </p>
    </article>
  );
}
