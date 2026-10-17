"use client";

import { BASEMAPS, type Basemap } from "./basemaps";

interface Props {
  value: string;
  onChange: (id: string) => void;
}

export function BasemapSwitcher({ value, onChange }: Props) {
  return (
    <div className="absolute left-3 top-3 z-[400] rounded-md bg-white/90 p-2
                    text-xs shadow dark:bg-slate-900/90">
      <label htmlFor="basemap" className="mb-1 block font-medium">
        Basemap
      </label>
      <select
        id="basemap"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-slate-300 bg-white px-1 py-0.5
                   text-xs dark:border-slate-700 dark:bg-slate-800"
      >
        {BASEMAPS.map((b: Basemap) => (
          <option key={b.id} value={b.id}>{b.label}</option>
        ))}
      </select>
    </div>
  );
}
