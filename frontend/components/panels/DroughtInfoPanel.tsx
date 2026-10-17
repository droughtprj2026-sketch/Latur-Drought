"use client";

import { useEffect, useState } from "react";
import { getTimeseries, type IndexName, type TimeseriesPoint } from "@/lib/api";
import { classifyValue, colorForValue, SPI_LABELS } from "@/lib/classify";

interface Props {
  index: IndexName;
  year: number;
  month: number;
}

const INDEX_DESC: Partial<Record<IndexName, string>> = {
  ndvi: "NDVI tracks green biomass. Values close to 1 are healthy canopy; near 0 is bare soil.",
  evi:  "EVI is like NDVI but less saturated in dense canopy and more sensitive to the blue band.",
  ndmi: "NDMI uses NIR + SWIR and indicates canopy water content.",
  vci:  "VCI rescales NDVI against its own per-pixel historical range (0 % = worst, 100 % = best).",
  vhi:  "VHI blends vegetation (VCI) and thermal (TCI) stress into one index.",
  pci:  "PCI rescales monthly rainfall against its historical range per calendar month.",
  spi1:  "SPI-1 compares the last month's rainfall to its long-term distribution.",
  spi3:  "SPI-3 captures short-term agricultural drought (3-month rainfall).",
  spi6:  "SPI-6 catches crop-season / hydrological stress (6-month rainfall).",
  spi12: "SPI-12 reflects long-term hydrological drought (12-month rainfall).",
  cdi:  "CDI fuses SPI-3, NDVI, VHI and PCI into one standardized value on the SPI class scale.",
};

export function DroughtInfoPanel({ index, year, month }: Props) {
  const [points, setPoints] = useState<TimeseriesPoint[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    getTimeseries(index).then(setPoints).catch((e) => setErr(String(e)));
  }, [index]);

  const key = `${year}-${String(month).padStart(2, "0")}`;
  const point = points.find((p) => p.date === key);
  const yearPts = points.filter((p) => p.date.startsWith(String(year)) && p.value != null);
  const yrMean = yearPts.length
    ? yearPts.reduce((a, b) => a + (b.value ?? 0), 0) / yearPts.length
    : null;

  return (
    <aside className="h-[560px] overflow-y-auto rounded-lg border border-slate-200
                      bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 className="text-base font-semibold">Drought condition</h2>
      <p className="mt-1 text-xs text-slate-500">
        {index.toUpperCase()} · {key}
      </p>

      {err && <p className="mt-2 text-xs text-red-600">{err}</p>}

      <div className="mt-4 rounded-md border border-slate-200 p-3 dark:border-slate-700">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500">District mean</span>
          <span
            className="rounded px-2 py-0.5 text-xs font-medium text-white"
            style={{ background: colorForValue(point?.value ?? null) }}
          >
            {point?.class ?? classifyValue(point?.value ?? null)}
          </span>
        </div>
        <div className="mt-2 font-mono text-2xl">
          {point?.value != null ? point.value.toFixed(2) : "—"}
        </div>
        {point?.pct_area_dry != null && (
          <div className="mt-1 text-xs text-slate-500">
            % of district under drought (≤ −1): <b>{point.pct_area_dry.toFixed(1)} %</b>
          </div>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded border border-slate-200 p-2 dark:border-slate-700">
          <div className="text-slate-500">Annual mean ({year})</div>
          <div className="mt-1 font-mono">
            {yrMean != null ? yrMean.toFixed(2) : "—"}
          </div>
        </div>
        <div className="rounded border border-slate-200 p-2 dark:border-slate-700">
          <div className="text-slate-500">Dry months ({year})</div>
          <div className="mt-1 font-mono">
            {yearPts.filter((p) => (p.value ?? 0) <= -1).length}
          </div>
        </div>
      </div>

      <div className="mt-4">
        <h3 className="text-xs font-semibold text-slate-500">What this index means</h3>
        <p className="mt-1 text-xs leading-5">
          {INDEX_DESC[index] ?? "—"}
        </p>
      </div>

      <div className="mt-4">
        <h3 className="text-xs font-semibold text-slate-500">Baseline scale</h3>
        <ul className="mt-1 space-y-0.5 text-xs">
          {SPI_LABELS.map((label, i) => (
            <li key={label} className="flex items-center gap-2">
              <span
                className="inline-block h-3 w-3 rounded-sm border border-slate-300"
                style={{
                  background: [
                    "#7f0000", "#d7301f", "#fdae61", "#f7f7f7",
                    "#a6d96a", "#1a9850", "#00441b",
                  ][i],
                }}
              />
              <span>{label}</span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
