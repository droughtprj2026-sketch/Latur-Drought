"use client";

import { BASEMAPS, type Basemap } from "./basemaps";

interface Props {
  value: string;
  onChange: (id: string) => void;
}

export function BasemapSwitcher({ value, onChange }: Props) {
  return (
    <div className="rounded-xl bg-white/95 p-2 text-xs shadow-md border border-slate-200 backdrop-blur-md">
      <label htmlFor="basemap" className="mb-1 block font-bold text-[10px] uppercase tracking-wider text-slate-600">
        Basemap Layer
      </label>
      <select
        id="basemap"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
      >
        {BASEMAPS.map((b: Basemap) => (
          <option key={b.id} value={b.id}>{b.label}</option>
        ))}
      </select>
    </div>
  );
}
