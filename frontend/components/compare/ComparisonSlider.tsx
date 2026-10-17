"use client";

import { useEffect, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import type { FeatureCollection, Feature } from "geojson";
import type { PathOptions } from "leaflet";
import { getIndexGeoJSON, type IndexName } from "@/lib/api";
import { colorForValue } from "@/lib/classify";

interface Props {
  index: IndexName;
  a: { year: number; month: number };   // older
  b: { year: number; month: number };   // newer
}

const LATUR: [number, number] = [18.4088, 76.5604];

/**
 * Side-by-side comparison slider. Two full-coverage GeoJSON layers are
 * rendered and the "newer" layer is clipped by a CSS inset so dragging
 * the handle reveals the "older" layer underneath.
 *
 * This matches the spec: Comparison Slider — drag the handle to compare
 * drought conditions between any two periods.
 */
export function ComparisonSlider({ index, a, b }: Props) {
  const [fA, setFA] = useState<FeatureCollection | null>(null);
  const [fB, setFB] = useState<FeatureCollection | null>(null);
  const [pct, setPct] = useState(50);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getIndexGeoJSON(index, a.year, a.month).then(setFA).catch(() => setFA(null));
    getIndexGeoJSON(index, b.year, b.month).then(setFB).catch(() => setFB(null));
  }, [index, a.year, a.month, b.year, b.month]);

  const style = (f?: Feature): PathOptions => {
    const v = f?.properties?.value as number | undefined;
    return { color: "#111", weight: 0.15, fillColor: colorForValue(v), fillOpacity: 0.82 };
  };

  const onDrag = (clientX: number) => {
    if (!barRef.current) return;
    const r = barRef.current.getBoundingClientRect();
    const p = Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100));
    setPct(p);
  };

  return (
    <div className="relative h-[560px] w-full overflow-hidden rounded-lg border
                    border-slate-200 dark:border-slate-800"
         ref={barRef}
         onMouseMove={(e) => (e.buttons & 1) && onDrag(e.clientX)}
         onTouchMove={(e) => onDrag(e.touches[0].clientX)}>
      <MapContainer center={LATUR} zoom={10} className="h-full w-full" zoomControl={false}>
        <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                   attribution="&copy; OSM · CARTO" />
        {fA && <GeoJSON key={`a-${a.year}-${a.month}`} data={fA} style={style} />}
        <ZoomControl position="topright" />
      </MapContainer>

      <div className="pointer-events-none absolute inset-y-0 right-0 overflow-hidden"
           style={{ left: `${pct}%` }}>
        <MapContainer center={LATUR} zoom={10} className="h-full w-full" zoomControl={false}
                      dragging={false} scrollWheelZoom={false} doubleClickZoom={false}
                      style={{ pointerEvents: "none", width: `${100 / ((100 - pct) / 100)}%`,
                               marginLeft: `-${pct * (100 / (100 - pct || 1))}%` }}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                     attribution="" />
          {fB && <GeoJSON key={`b-${b.year}-${b.month}`} data={fB} style={style} />}
        </MapContainer>
      </div>

      <div className="pointer-events-auto absolute inset-y-0"
           style={{ left: `calc(${pct}% - 1px)` }}>
        <div className="h-full w-0.5 bg-slate-900/60 dark:bg-white/80" />
        <button
          aria-label="Drag to compare"
          onMouseDown={(e) => {
            e.preventDefault();
            const move = (ev: MouseEvent) => onDrag(ev.clientX);
            const up = () => {
              window.removeEventListener("mousemove", move);
              window.removeEventListener("mouseup", up);
            };
            window.addEventListener("mousemove", move);
            window.addEventListener("mouseup", up);
          }}
          className="absolute top-1/2 -ml-3 h-6 w-6 -translate-y-1/2 cursor-ew-resize
                     rounded-full border border-slate-400 bg-white shadow"
        >
          <span className="block text-[10px] leading-6">↔</span>
        </button>
      </div>

      <div className="absolute left-2 top-2 rounded bg-white/90 px-2 py-0.5 text-xs shadow
                      dark:bg-slate-900/90">
        A · {a.year}-{String(a.month).padStart(2, "0")}
      </div>
      <div className="absolute right-2 top-2 rounded bg-white/90 px-2 py-0.5 text-xs shadow
                      dark:bg-slate-900/90">
        B · {b.year}-{String(b.month).padStart(2, "0")}
      </div>
    </div>
  );
}
