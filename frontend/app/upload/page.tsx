"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAoi } from "@/components/aoi/useAoi";
import { D_COLORS, D_CODES, D_LABELS } from "@/lib/classify";
import { resultToCsv } from "@/lib/aoi";
import { latestCoveredPeriod, loadTimeseries } from "@/lib/data";

// The AOI is analysed in the browser against the 954 village polygons, so it
// works without a server queue and nothing leaves the device.
export default function UploadPage() {
  const [period, setPeriod] = useState("");
  useEffect(() => { loadTimeseries().then((t) => setPeriod(latestCoveredPeriod(t) ?? "")).catch(() => null); }, []);
  const { aoi, name, result, busy, error, upload, clear } = useAoi(period || "2000-01");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const idx = (c: string) => D_CODES.indexOf(c as any);

  const csv = () => {
    if (!result) return;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([resultToCsv(result, period)], { type: "text/csv" }));
    a.download = `aoi_${period}.csv`;
    a.click();
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-clay">My area</p>
      <h1 className="mt-1 font-display text-3xl leading-tight">How dry is my patch of Latur?</h1>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink/75">
        Drop a GeoJSON polygon of a watershed, a farm cluster or a project boundary. It is overlaid on the 954 village
        polygons and each overlapped village is scored with the latest composite index. The file stays in your browser.
      </p>

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) upload(f); }}
        className={`mt-6 flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${drag ? "border-teal bg-teal/5" : "border-ink/25 bg-paper"}`}
      >
        <p className="font-display text-lg">{aoi ? name : "Drag a .geojson here"}</p>
        <p className="mt-1 text-xs text-ink/60">Polygons or multipolygons in lon/lat (EPSG:4326), up to 20 MB. Shapefiles: convert with <code className="font-mono">ogr2ogr -f GeoJSON -t_srs EPSG:4326 out.geojson in.shp</code></p>
        <input ref={input} type="file" accept=".geojson,.json,application/geo+json" className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
        <div className="mt-4 flex gap-2">
          <button type="button" onClick={() => input.current?.click()} className="rounded bg-ink px-3 py-1.5 font-mono text-xs text-paper hover:bg-ink/85">Choose file</button>
          {aoi && <button type="button" onClick={clear} className="rounded border border-ink/25 px-3 py-1.5 font-mono text-xs hover:bg-ink/5">Clear</button>}
        </div>
      </div>

      {error && <p role="alert" className="mt-4 rounded border border-d3/40 bg-d3/10 px-3 py-2 text-sm">{error}</p>}
      {busy && <p className="mt-4 font-mono text-xs text-teal">Intersecting with 954 villages…</p>}

      {result && (
        <section className="mt-6">
          <div className="flex flex-wrap items-end gap-x-8 gap-y-2 border-b border-ink/15 pb-3">
            <Big label="AOI area" value={`${result.aoi_km2.toFixed(1)} km²`} />
            <Big label="Villages overlapped" value={String(result.rows.length)} />
            <Big label={`Area-weighted CDI · ${period}`} value={result.weighted_cdi != null ? result.weighted_cdi.toFixed(3) : "no score"}
                 note={result.weighted_cdi != null ? D_LABELS[idx(result.weighted_class)] : undefined} />
            <Link href="/" className="ml-auto rounded border border-teal px-3 py-1.5 font-mono text-xs font-semibold text-teal hover:bg-teal/10">Show on the map →</Link>
            <button type="button" onClick={csv} className="rounded border border-ink/25 px-3 py-1.5 font-mono text-xs hover:bg-ink/5">Download CSV</button>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-ink/20 font-mono text-[10px] uppercase tracking-wider text-ink/55">
                  <th className="py-1.5">Village</th><th>Tehsil</th><th className="text-right">Overlap km²</th>
                  <th className="text-right">% of village</th><th className="text-right">CDI</th><th className="pl-4">Class</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink/10">
                {result.rows.map((r) => (
                  <tr key={r.id}>
                    <td className="py-1.5 font-medium">{r.village}</td><td className="text-ink/70">{r.tehsil}</td>
                    <td className="text-right font-mono">{r.overlap_km2.toFixed(2)}</td>
                    <td className="text-right font-mono">{(100 * r.share_of_village).toFixed(0)}%</td>
                    <td className="text-right font-mono">{r.cdi != null ? r.cdi.toFixed(3) : "–"}</td>
                    <td className="pl-4"><span className="inline-flex items-center gap-1.5">
                      <i className="h-2.5 w-2.5 rounded-sm border border-ink/25" style={{ background: r.cls === "ND" ? "#A39F90" : D_COLORS[idx(r.cls)] }} />{r.cls}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

function Big({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div>
      <div className="font-display text-2xl leading-none">{value}</div>
      <div className="mt-1 font-mono text-[10px] uppercase tracking-wider text-ink/55">{label}</div>
      {note && <div className="text-[11px] text-ink/70">{note}</div>}
    </div>
  );
}
