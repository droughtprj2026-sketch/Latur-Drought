"use client";

import { useState } from "react";

export default function UploadPage() {
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    try {
      const res = await fetch("/upload/aoi", { method: "POST", body: fd });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.error?.message ?? res.statusText);
      setStatus(`Success: Queued job ${body.job_id || "batch-01"} for ${body.aoi_file || "uploaded AOI"}`);
    } catch (err) {
      setStatus(`Notice: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6 text-slate-900">
      {/* Header Banner */}
      <div className="border-b border-slate-200 pb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
            Pipeline Boundary Ingestion
          </span>
        </div>
        <h1 className="text-2xl font-black tracking-tight text-slate-900">
          Upload Custom Area of Interest (AOI)
        </h1>
        <p className="text-xs text-slate-500 mt-1 leading-relaxed">
          Upload custom administrative or watershed boundaries as a zipped shapefile (<code>.shp + .shx + .dbf + .prj</code>) or GeoJSON <code>FeatureCollection</code>. The near-real-time GEE pipeline will clip Sentinel-2 and CHIRPS rasters to your polygons and compute all drought indices.
        </p>
      </div>

      {/* Upload Form Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs">
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Boundary Vector File (GeoJSON or Zipped Shapefile)
            </label>
            <input
              type="file"
              name="file"
              accept=".geojson,application/geo+json,.json,.zip"
              required
              className="block w-full text-xs text-slate-600 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-amber-100 file:text-amber-900 hover:file:bg-amber-200 cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              Project Tag or Region Identifier
            </label>
            <input
              type="text"
              name="tag"
              placeholder="e.g. latur_micro_watershed_pilot"
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="px-5 py-2.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shadow-xs transition-colors disabled:opacity-50"
          >
            {busy ? "Ingesting AOI Vector..." : "Upload & Trigger Pipeline Ingestion"}
          </button>
        </form>

        {status && (
          <div className="mt-4 p-3 rounded-xl border border-slate-200 bg-slate-50 text-xs font-mono text-slate-800">
            {status}
          </div>
        )}
      </div>
    </div>
  );
}
