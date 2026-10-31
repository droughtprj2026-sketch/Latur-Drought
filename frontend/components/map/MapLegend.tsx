"use client";

import { useState } from "react";
import type { Bin, MetricSpec } from "@/lib/metrics";
import { NO_DATA_COLOR } from "@/lib/metrics";

export interface LegendProps {
  spec: MetricSpec;
  /** Villages per bin for the month/tehsil on screen (same order as spec.bins). */
  counts: number[];
  noData: number;
  total: number;
  period: string;
  tehsilLabel: string;
  /** Newest month that has data for this layer, when the current one is mostly blank. */
  jumpTo?: { period: string; go: () => void } | null;
}

/** Display order: worst conditions first for drought scales. */
function ordered(bins: Bin[], counts: number[]) {
  return bins.map((b, i) => ({ b, n: counts[i] ?? 0 }));
}

export function MapLegend({ spec, counts, noData, total, period, tehsilLabel, jumpTo }: LegendProps) {
  const [open, setOpen] = useState(false);
  const rows = ordered(spec.bins, counts);
  const max = Math.max(1, ...rows.map((r) => r.n), noData);
  const mostlyBlank = total > 0 && noData / total > 0.5;

  return (
    <section
      aria-label={`Legend: ${spec.title}`}
      className="pointer-events-auto w-full md:w-[272px] flex-none rounded-lg border border-ink/15 bg-paper/95 shadow-card backdrop-blur"
    >
      <header className="flex items-start justify-between gap-2 px-3 pt-2.5">
        <div className="min-w-0">
          <h2 className="font-display text-[15px] leading-tight text-ink">{spec.title}</h2>
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-ink/55">
            {period} · {tehsilLabel}
          </p>
          {spec.group === "Long-term" && (
            <p className="mt-0.5 text-[10px] leading-tight text-ink/60">
              Accumulated over several months. Changes only when a new month is published.
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="mt-0.5 rounded border border-ink/20 px-1.5 py-0.5 font-mono text-[10px] text-ink/70 hover:bg-ink/5"
        >
          {open ? "hide" : "defn"}
        </button>
      </header>

      {open && (
        <p className="px-3 pt-1.5 text-[11px] leading-snug text-ink/70">{spec.definition}</p>
      )}

      <ul className="px-3 pb-2 pt-2">
        {rows.map(({ b, n }) => (
          <li
            key={b.label + b.range}
            className="flex items-center gap-2 rounded-[2px] py-[2px] pl-0.5 pr-1 text-[11px] leading-tight"
            style={{ backgroundImage: `linear-gradient(90deg, rgba(29,43,37,.07) ${(n / max) * 100}%, transparent ${(n / max) * 100}%)` }}
            title={`${n} villages`}
          >
            <span className="h-3 w-5 flex-none rounded-[2px] border border-ink/25" style={{ background: b.color }} aria-hidden />
            <span className="min-w-0 flex-1 truncate text-ink">{b.label}</span>
            <span className="flex-none font-mono text-[10px] text-ink/55">{b.range}</span>
            <span className="w-8 flex-none text-right font-mono text-[10px] text-ink/80">{n}</span>
          </li>
        ))}
        <li className="flex items-center gap-2 border-t border-ink/10 pt-1.5 mt-1 text-[11px] leading-tight">
          <span className="h-3 w-5 flex-none rounded-[2px] border border-ink/25" style={{ background: NO_DATA_COLOR }} aria-hidden />
          <span className="flex-1 text-ink/70">No data this month</span>
          <span className="w-8 text-right font-mono text-[10px] text-ink/70">{noData}</span>
        </li>
      </ul>

      {mostlyBlank && (
        <p className="mx-3 mb-2.5 rounded border border-d3/40 bg-d3/10 px-2 py-1 text-[11px] leading-snug text-ink">
          {noData} of {total} villages have no {spec.title.split(" (")[0]} value for {period}. The
          source for this layer has not published this month yet.
          {jumpTo && (
            <button type="button" onClick={jumpTo.go} className="mt-1 block font-mono text-[11px] font-semibold text-clay underline underline-offset-2">
              Show {jumpTo.period}, the latest month with data
            </button>
          )}
        </p>
      )}
    </section>
  );
}

/** Compact legend for the two-map pages (compare, timelapse). */
export function LegendStrip({ spec }: { spec: MetricSpec }) {
  return (
    <div className="pointer-events-auto rounded-lg border border-ink/15 bg-paper/95 px-3 py-2 shadow-card backdrop-blur">
      <div className="mb-1 font-display text-[13px] leading-tight">{spec.title}</div>
      <ul className="flex flex-wrap gap-x-3 gap-y-1">
        {spec.bins.map((b) => (
          <li key={b.label + b.range} className="flex items-center gap-1.5 text-[10px]">
            <span className="h-3 w-4 rounded-[2px] border border-ink/25" style={{ background: b.color }} />
            <span>{b.label}</span>
            <span className="font-mono text-ink/55">{b.range}</span>
          </li>
        ))}
        <li className="flex items-center gap-1.5 text-[10px]">
          <span className="h-3 w-4 rounded-[2px] border border-ink/25" style={{ background: NO_DATA_COLOR }} />
          <span className="text-ink/70">No data</span>
        </li>
      </ul>
    </div>
  );
}
