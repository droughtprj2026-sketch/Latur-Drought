import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Data Sources & Provenance · Latur Drought Intelligence",
};

export default function SourcesPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6 text-slate-900">
      {/* Header Banner */}
      <div className="border-b border-slate-200 pb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
            Open Earth Science Data Sources
          </span>
        </div>
        <h1 className="text-2xl font-black tracking-tight text-slate-900">
          Sensor & Ingestion Registry
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Rigorous open-access satellite earth observation, precipitation climatology, and cadastral boundary sources powering the Latur drought monitoring platform.
        </p>
      </div>

      {/* Sources Table Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px]">
              <th className="py-2.5 font-bold">Data Stream</th>
              <th className="py-2.5 font-bold">Earth Engine / Catalog ID</th>
              <th className="py-2.5 font-bold">Derived Index</th>
              <th className="py-2.5 font-bold">Temporal Cadence</th>
              <th className="py-2.5 font-bold">License / Terms</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-medium">
            <tr>
              <td className="py-3 font-bold text-slate-900">ESA Copernicus Sentinel-2 L2A</td>
              <td className="py-3 font-mono text-[11px] text-amber-800">COPERNICUS/S2_SR_HARMONIZED</td>
              <td className="py-3">NDVI, EVI, VCI, VHI, PCI</td>
              <td className="py-3">5-Day Revisit</td>
              <td className="py-3 text-slate-500">Copernicus Free & Open</td>
            </tr>
            <tr>
              <td className="py-3 font-bold text-slate-900">UCSB CHIRPS Monthly v2.0</td>
              <td className="py-3 font-mono text-[11px] text-amber-800">UCSB-CHG/CHIRPS/monthly</td>
              <td className="py-3">SPI-1, SPI-3, SPI-6, SPI-12, Rain mm</td>
              <td className="py-3">Monthly</td>
              <td className="py-3 text-slate-500">Public Domain (UCSB)</td>
            </tr>
            <tr>
              <td className="py-3 font-bold text-slate-900">NASA MODIS Terra LST</td>
              <td className="py-3 font-mono text-[11px] text-amber-800">MODIS/061/MOD11A1</td>
              <td className="py-3">Temperature Condition Index (TCI), VHI</td>
              <td className="py-3">Daily</td>
              <td className="py-3 text-slate-500">NASA Open Data</td>
            </tr>
            <tr>
              <td className="py-3 font-bold text-slate-900">Google Maps Platform Tiles</td>
              <td className="py-3 font-mono text-[11px] text-amber-800">mt1.google.com/vt/lyrs=p</td>
              <td className="py-3">Google Terrain, Roadmap, Satellite Hybrid</td>
              <td className="py-3">Live</td>
              <td className="py-3 text-slate-500">Google Maps Terms</td>
            </tr>
            <tr>
              <td className="py-3 font-bold text-slate-900">Survey of India Cadastral Vector</td>
              <td className="py-3 font-mono text-[11px] text-amber-800">frontend/public/data/latur_villages.geojson</td>
              <td className="py-3">954 Village revenue boundaries</td>
              <td className="py-3">Official SOI Baseline</td>
              <td className="py-3 text-slate-500">Survey of India / Open Data</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
