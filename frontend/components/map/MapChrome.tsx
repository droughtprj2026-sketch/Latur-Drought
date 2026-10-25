"use client";

import { useMap } from "react-leaflet";
import { BASEMAPS } from "./basemaps";

/** Zoom + basemap in one right-hand stack so nothing competes with the
 *  top-left page controls or the bottom dock. */
export function MapControls({
  basemapId, onBasemap, rightInset,
}: { basemapId: string; onBasemap: (id: string) => void; rightInset: number }) {
  const map = useMap();
  const btn =
    "flex h-8 w-8 items-center justify-center font-mono text-base leading-none text-ink hover:bg-ink/5 active:bg-ink/10";
  return (
    <div
      className="absolute top-3 z-[600] flex flex-col items-end gap-2 transition-[right] duration-200"
      style={{ right: 12 + rightInset }}
    >
      <label className="flex items-center gap-2 rounded-lg border border-ink/15 bg-paper/95 px-2 py-1 shadow-card backdrop-blur">
        <span className="font-mono text-[10px] uppercase tracking-wider text-ink/55">Base</span>
        <select
          value={basemapId}
          onChange={(e) => onBasemap(e.target.value)}
          aria-label="Basemap"
          className="max-w-[150px] cursor-pointer bg-transparent text-xs font-medium text-ink focus:outline-none"
        >
          {BASEMAPS.map((b) => (
            <option key={b.id} value={b.id}>{b.label}</option>
          ))}
        </select>
      </label>
      <div className="flex flex-col divide-y divide-ink/10 overflow-hidden rounded-lg border border-ink/15 bg-paper/95 shadow-card backdrop-blur">
        <button type="button" className={btn} onClick={() => map.zoomIn()} aria-label="Zoom in">+</button>
        <button type="button" className={btn} onClick={() => map.zoomOut()} aria-label="Zoom out">−</button>
      </div>
    </div>
  );
}
