"use client";

import { useEffect, useMemo, useRef, useState } from "react";

interface Props {
  periods: string[];
  currentPeriod: string;
  onPeriodChange: (period: string) => void;
  /** Period that counts as "now" (latest observation actually available). */
  latestPeriod?: string;
  /** Jump targets computed from the data (see recordMarkers); none are assumed. */
  markers?: { p: string; label: string }[];
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const fmt = (p: string) => {
  const [y, m] = p.split("-");
  return `${MONTHS[parseInt(m, 10) - 1] ?? m} ${y}`;
};

export function MonthlyTimelineScrubber({ periods, currentPeriod, onPeriodChange, latestPeriod, markers = [] }: Props) {
  const [playing, setPlaying] = useState(false);
  const idx = Math.max(0, periods.indexOf(currentPeriod));
  const idxRef = useRef(idx);
  idxRef.current = idx;

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => {
      const next = idxRef.current + 1;
      if (next >= periods.length) { setPlaying(false); return; }
      onPeriodChange(periods[next]);
    }, 900);
    return () => clearInterval(t);
  }, [playing, periods, onPeriodChange]);

  const years = useMemo(() => {
    const out: { y: string; at: number }[] = [];
    periods.forEach((p, i) => { const y = p.slice(0, 4); if (!out.length || out[out.length - 1].y !== y) out.push({ y, at: i }); });
    return out;
  }, [periods]);

  const latest = latestPeriod ?? periods[periods.length - 1];
  const step = (d: number) => periods[idx + d] && onPeriodChange(periods[idx + d]);
  const btn = "rounded border border-ink/20 bg-paper px-2 py-1 font-mono text-[11px] text-ink hover:bg-ink/5 disabled:opacity-35";

  return (
    <div className="rounded-lg border border-ink/15 bg-paper/95 px-3 py-2 shadow-card backdrop-blur">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <button type="button" onClick={() => setPlaying((v) => !v)} aria-pressed={playing}
          className="rounded bg-ink px-2.5 py-1 font-mono text-[11px] text-paper hover:bg-ink/85">
          {playing ? "Pause" : "Play"}
        </button>
        <button type="button" className={btn} onClick={() => step(-1)} disabled={idx === 0} aria-label="Previous month">‹</button>
        <button type="button" className={btn} onClick={() => step(1)} disabled={idx >= periods.length - 1} aria-label="Next month">›</button>
        <div className="font-display text-lg leading-none text-ink">{fmt(periods[idx] ?? currentPeriod)}</div>
        <span className="font-mono text-[10px] text-ink/50">{idx + 1}/{periods.length}</span>
        <div className="ml-auto hidden items-center gap-1 xl:flex">
          {markers.filter((e) => periods.includes(e.p)).map((e) => (
            <button key={e.p} type="button" className={btn} onClick={() => onPeriodChange(e.p)} title={e.p}>{e.label}</button>
          ))}
          <button type="button" onClick={() => onPeriodChange(latest)}
            className="rounded border border-clay bg-clay/10 px-2 py-1 font-mono text-[11px] font-semibold text-clay hover:bg-clay/20">
            Latest · {latest}
          </button>
        </div>
      </div>
      <input
        type="range" min={0} max={Math.max(0, periods.length - 1)} value={idx}
        onChange={(e) => periods[Number(e.target.value)] && onPeriodChange(periods[Number(e.target.value)])}
        aria-label="Observation month" aria-valuetext={fmt(periods[idx] ?? currentPeriod)}
        className="mt-1.5 h-1.5 w-full cursor-pointer accent-clay"
      />
      <div className="relative mt-0.5 h-3 font-mono text-[9px] text-ink/50">
        {years.map((y) => (
          <span key={y.y} className="absolute -translate-x-1/2" style={{ left: `${(y.at / Math.max(1, periods.length - 1)) * 100}%` }}>
            {y.y}
          </span>
        ))}
      </div>
    </div>
  );
}
