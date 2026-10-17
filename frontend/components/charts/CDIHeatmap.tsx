"use client";

import { useEffect, useState } from "react";
import { getTimeseries, type TimeseriesPoint } from "@/lib/api";
import { colorForValue } from "@/lib/classify";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Year × month heatmap for CDI (0..1 drought intensity). */
export function CDIHeatmap() {
  const [data, setData] = useState<TimeseriesPoint[]>([]);
  useEffect(() => {
    getTimeseries("cdi").then(setData).catch(() => undefined);
  }, []);

  if (!data.length) return <p className="text-xs text-slate-500">loading CDI heatmap …</p>;

  const years = Array.from(new Set(data.map((d) => Number(d.date.slice(0, 4))))).sort();
  const byKey = new Map(data.map((d) => [d.date, d] as const));

  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-0.5 text-[11px]">
        <thead>
          <tr>
            <th className="w-10 text-left"></th>
            {MONTHS.map((m) => (
              <th key={m} className="w-10 py-1 text-center font-normal text-slate-500">{m}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((y) => (
            <tr key={y}>
              <th className="pr-2 text-right font-normal text-slate-500">{y}</th>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
                const key = `${y}-${String(m).padStart(2, "0")}`;
                const p = byKey.get(key);
                const v = p?.value ?? null;
                return (
                  <td key={m} className="h-7 w-10 text-center text-[10px]"
                      style={{ background: colorForValue(v, "cdi"),
                               color: v != null && v > 0.5 ? "#fff" : "#1f2937" }}
                      title={`${key}  CDI ${v?.toFixed(2) ?? "—"}  ${p?.class ?? "No data"}`}>
                    {v != null && Number.isFinite(v) ? v.toFixed(2) : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
