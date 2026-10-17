"use client";

import { SPI_COLORS, SPI_LABELS } from "@/lib/classify";

export function LegendBar() {
  return (
    <div className="absolute right-3 top-3 z-[400] rounded-md bg-white/90 p-2 text-xs shadow dark:bg-slate-900/90">
      <div className="mb-1 font-medium">Drought class</div>
      <ul className="space-y-0.5">
        {SPI_LABELS.map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-sm border border-slate-300"
              style={{ background: SPI_COLORS[i] }}
            />
            <span>{label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
