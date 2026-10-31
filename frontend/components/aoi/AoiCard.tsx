"use client";

import { D_COLORS, D_CODES, D_LABELS } from "@/lib/classify";
import { resultToCsv, type AoiResult } from "@/lib/aoi";

export function AoiCard({ name, result, period, onClear, onSelect }: {
  name: string; result: AoiResult; period: string; onClear: () => void; onSelect: (id: number) => void;
}) {
  const idx = (c: string) => D_CODES.indexOf(c as any);
  const classes = [...D_CODES, "ND"] as string[];
  const km2 = result.rows.reduce((s, r) => s + r.overlap_km2, 0) || 1;

  const download = () => {
    const blob = new Blob([resultToCsv(result, period)], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `aoi_${period}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <section className="w-[320px] max-w-full rounded-lg border border-teal/50 bg-paper/95 shadow-card backdrop-blur">
      <header className="flex items-start justify-between gap-2 border-b border-ink/10 px-3 py-2">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-wider text-teal">Your area of interest</p>
          <h2 className="truncate font-display text-[15px] leading-tight text-ink" title={name}>{name}</h2>
        </div>
        <button type="button" onClick={onClear} className="rounded border border-ink/20 px-1.5 py-0.5 font-mono text-[10px] text-ink/70 hover:bg-ink/5">clear</button>
      </header>
      <div className="grid grid-cols-3 gap-2 px-3 py-2 text-center">
        <Stat label="AOI area" value={`${result.aoi_km2.toFixed(1)} km²`} />
        <Stat label="Villages" value={String(result.rows.length)} />
        <Stat label={`CDI ${period}`} value={result.weighted_cdi != null ? result.weighted_cdi.toFixed(2) : "–"}
              sub={result.weighted_cdi != null ? D_LABELS[idx(result.weighted_class)] : "no score"} />
      </div>
      <div className="px-3">
        <div className="flex h-2.5 overflow-hidden rounded-sm border border-ink/20" aria-label="Area by drought class">
          {classes.map((c) => {
            const v = result.by_class[c] ?? 0;
            return v ? <span key={c} title={`${c}: ${v.toFixed(1)} km²`} style={{ width: `${(100 * v) / km2}%`, background: c === "ND" ? "#A39F90" : D_COLORS[idx(c)] }} /> : null;
          })}
        </div>
        {result.covered_km2 < result.aoi_km2 * 0.98 && (
          <p className="mt-1 text-[10px] leading-snug text-ink/60">
            {(100 * (1 - result.covered_km2 / result.aoi_km2)).toFixed(0)}% of the AOI lies outside Latur district and is ignored.
          </p>
        )}
        {result.scored_share < 0.99 && (
          <p className="mt-1 text-[10px] leading-snug text-ink/60">
            {(100 * (1 - result.scored_share)).toFixed(0)}% of the overlapped area has no composite score for {period}.
          </p>
        )}
      </div>
      <ul className="mt-1 max-h-40 overflow-y-auto px-1 pb-1">
        {result.rows.slice(0, 40).map((r) => (
          <li key={r.id}>
            <button type="button" onClick={() => onSelect(r.id)} className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-[11px] hover:bg-ink/5">
              <span className="h-2.5 w-2.5 flex-none rounded-sm border border-ink/25" style={{ background: r.cls === "ND" ? "#A39F90" : D_COLORS[idx(r.cls)] }} />
              <span className="min-w-0 flex-1 truncate">{r.village} <span className="text-ink/45">· {r.tehsil}</span></span>
              <span className="font-mono text-[10px] text-ink/60">{r.overlap_km2.toFixed(1)} km²</span>
            </button>
          </li>
        ))}
      </ul>
      <footer className="border-t border-ink/10 px-3 py-1.5">
        <button type="button" onClick={download} className="font-mono text-[11px] text-teal underline underline-offset-2">Download village table (CSV)</button>
      </footer>
    </section>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div className="font-display text-lg leading-none text-ink">{value}</div>
      <div className="mt-0.5 font-mono text-[9px] uppercase tracking-wide text-ink/50">{label}</div>
      {sub && <div className="truncate text-[9px] text-ink/60">{sub}</div>}
    </div>
  );
}
