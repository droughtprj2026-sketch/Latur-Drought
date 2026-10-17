"use client";

import { useState } from "react";

/**
 * Upload a shapefile zip or a GeoJSON FeatureCollection as the Area of
 * Interest for the next pipeline run. The file is POSTed to the Node
 * gateway at /upload/aoi, which validates it and proxies to the Go
 * admin endpoint. The user needs the "admin" Supabase role.
 */
export default function UploadPage() {
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus(""); setBusy(true);
    const fd = new FormData(e.currentTarget);
    try {
      const res = await fetch("/upload/aoi", { method: "POST", body: fd });
      const body = await res.json();
      if (!res.ok) throw new Error(body?.error?.message ?? res.statusText);
      setStatus(`Queued: job ${body.job_id} on ${body.aoi_file}`);
    } catch (err) {
      setStatus(`Failed: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="max-w-xl space-y-4">
      <h1 className="text-xl font-semibold">Upload area of interest</h1>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Attach a shapefile (zipped <code>.shp + .shx + .dbf + .prj</code>) or a
        GeoJSON <code>FeatureCollection</code>. The pipeline will treat it as
        the AOI for the next run, fetch Sentinel-2 clipped to it, and compute
        every index for the uploaded polygons.
      </p>

      <form onSubmit={submit}
            className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
        <label className="block text-xs text-slate-500">AOI file</label>
        <input type="file" name="file" accept=".geojson,application/geo+json,.json,.zip"
               required
               className="mt-1 block w-full text-sm" />
        <label className="mt-3 block text-xs text-slate-500">Tag (optional)</label>
        <input type="text" name="tag"
               placeholder="e.g. latur_ausa_pilot"
               className="mt-1 w-full rounded border border-slate-300 bg-transparent
                          px-2 py-1 text-sm dark:border-slate-700" />
        <button disabled={busy}
                className="mt-4 rounded bg-blue-600 px-3 py-1.5 text-sm text-white
                           hover:bg-blue-700 disabled:opacity-50">
          {busy ? "Uploading …" : "Upload AOI"}
        </button>
      </form>

      {status && (
        <p className="text-xs font-mono text-slate-700 dark:text-slate-200">
          {status}
        </p>
      )}
    </article>
  );
}
