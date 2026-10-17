import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About · Near-Real Time Drought Monitoring",
};

export default function AboutPage() {
  return (
    <article className="prose prose-slate dark:prose-invert max-w-3xl">
      <h1>About this dashboard</h1>

      <p className="lead">
        The <strong>Near-Real Time Drought Monitoring System</strong> for Latur
        District fetches Sentinel-2 imagery and CHIRPS rainfall for the
        selected area of interest, computes six established drought indices,
        and classifies the final drought condition with a transparent
        weighted multi-index composite.
      </p>

      <h2>Who built it</h2>
      <p>
        Built and maintained by <strong>Rajnandini Kadam</strong>
        <br />
        <a href="mailto:rajnandinikadam221@gmail.com">rajnandinikadam221@gmail.com</a>
        <br />
        <em>Organization: to be filled by the host institute / department.</em>
      </p>

      <h2>Methodology summary</h2>
      <ul>
        <li><strong>AOI handling.</strong> Default AOI is the Latur district
            shapefile under <code>data/vector/</code>. Users with the admin role
            can upload a shapefile zip or a GeoJSON FeatureCollection; the
            uploaded polygons drive the next scheduled run.</li>
        <li><strong>Sentinel-2.</strong> Pulled from GEE
            (<code>COPERNICUS/S2_SR_HARMONIZED</code>), cloud-masked with SCL
            and s2cloudless, resampled to a common 10 m grid.</li>
        <li><strong>CHIRPS.</strong> Monthly totals from
            <code> UCSB-CHG/CHIRPS/monthly</code>, with daily
            <code> UCSB-CHG/CHIRPS/DAILY</code> used for partial-month tracking.</li>
        <li><strong>Indices.</strong> NDVI, EVI, VCI, VHI, PCI from Sentinel-2;
            SPI (1 / 3 / 6 / 12) from CHIRPS using a gamma distribution fit
            against a documented reference climatology (default 1991–2020).</li>
        <li><strong>Zonal statistics.</strong> Run per tehsil and per village.
            Missing or QC-failed inputs are kept as "unavailable", never zero.</li>
        <li><strong>Composite drought class.</strong> A weighted multi-index
            composite replaces the previous Random Forest classifier. Weights
            and thresholds live in <code>config/composite.yaml</code> and the
            formula version is stamped on every classification.
            <strong> No learned classifier is used.</strong></li>
      </ul>

      <h2>Migration note</h2>
      <p>
        The Random Forest classifier (and the <code>RF Confidence</code> /
        <code> RF Uncertainty</code> outputs) has been <strong>retired</strong>.
        It has been replaced by the transparent composite drought score
        described above. The master table no longer carries any
        <code> rf_*</code> columns.
      </p>

      <h2>Open source</h2>
      <p>
        All processing scripts, the Go backend, Next.js frontend and Supabase
        migrations live in the project repository. See the
        <a href="/sources"> Sources</a> page for data citations and the
        Code of Conduct.
      </p>
    </article>
  );
}
