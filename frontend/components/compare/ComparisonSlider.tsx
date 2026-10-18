"use client";

import { useEffect, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import type { FeatureCollection, Feature } from "geojson";
import type { PathOptions } from "leaflet";
import { getIndexGeoJSON, type IndexName } from "@/lib/api";
import { colorForValue } from "@/lib/classify";

interface Props {
  index: IndexName;
  a: { year: number; month: number };   // older period
  b: { year: number; month: number };   // newer period
}

const LATUR: [number, number] = [18.4088, 76.5604];

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Bi-temporal side-by-side comparison curtain slider.
 * Both layers render synchronized 951-village polygons over Google Terrain.
 * Dragging the divider curtain wipes between Period A and Period B.
 */
export function ComparisonSlider({ index, a, b }: Props) {
  const [fA, setFA] = useState<FeatureCollection | null>(null);
  const [fB, setFB] = useState<FeatureCollection | null>(null);
  const [pct, setPct] = useState(50);
  const [hoveredInfo, setHoveredInfo] = useState<string>("");
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setHoveredInfo("");
    getIndexGeoJSON(index, a.year, a.month).then(setFA).catch(() => setFA(null));
    getIndexGeoJSON(index, b.year, b.month).then(setFB).catch(() => setFB(null));
  }, [index, a.year, a.month, b.year, b.month]);

  const style = (f?: Feature): PathOptions => {
    const v = f?.properties?.value as number | undefined;
    return {
      color: "#475569",
      weight: 0.6,
      fillColor: colorForValue(v, index),
      fillOpacity: 0.85,
    };
  };

  const onEachFeature = (feature: Feature, layer: any) => {
    const p = feature.properties || {};
    const name = p.village || p.VILLAGE || p.name || "Village";
    const t = p.tehsil || p.TEHSIL || "";
    const val = p.value != null && !isNaN(p.value) ? Number(p.value).toFixed(2) : "—";
    const cls = p.class || "None";

    layer.on({
      mouseover: () => {
        setHoveredInfo(`${name} (${t}): ${index.toUpperCase()} = ${val} [${cls}]`);
      },
    });

    layer.bindTooltip(
      `<strong>${name}</strong> (${t})<br/>${index.toUpperCase()}: ${val} · ${cls}`,
      { sticky: true, className: "text-xs font-sans rounded shadow bg-white p-1.5 border border-slate-200" }
    );
  };

  const onDrag = (clientX: number) => {
    if (!barRef.current) return;
    const r = barRef.current.getBoundingClientRect();
    const p = Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100));
    setPct(p);
  };

  return (
    <div
      className="relative h-[600px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs select-none"
      ref={barRef}
      onMouseMove={(e) => (e.buttons & 1) && onDrag(e.clientX)}
      onTouchMove={(e) => onDrag(e.touches[0].clientX)}
    >
      {/* Underlying Map: Period A */}
      <MapContainer center={LATUR} zoom={10} className="h-full w-full" zoomControl={false}>
        <TileLayer
          url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
          attribution="&copy; Google Maps Terrain"
        />
        {fA && <GeoJSON key={`a-${a.year}-${a.month}-${index}`} data={fA} style={style} onEachFeature={onEachFeature} />}
        <ZoomControl position="topright" />
      </MapContainer>

      {/* Overlying Map: Period B, dynamically clipped from the right */}
      <div
        className="pointer-events-none absolute inset-y-0 right-0 overflow-hidden"
        style={{ left: `${pct}%` }}
      >
        <MapContainer
          center={LATUR}
          zoom={10}
          className="h-full w-full"
          zoomControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          style={{
            pointerEvents: "none",
            width: `${100 / ((100 - pct) / 100 || 1)}%`,
            marginLeft: `-${pct * (100 / (100 - pct || 1))}%`,
          }}
        >
          <TileLayer
            url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
            attribution=""
          />
          {fB && <GeoJSON key={`b-${b.year}-${b.month}-${index}`} data={fB} style={style} />}
        </MapContainer>
      </div>

      {/* Dividing Curtain Bar & Handle */}
      <div
        className="pointer-events-auto absolute inset-y-0 z-[800]"
        style={{ left: `calc(${pct}% - 1px)` }}
      >
        <div className="h-full w-0.5 bg-amber-600 shadow-md" />
        <button
          type="button"
          aria-label="Drag comparison divider"
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
          className="absolute top-1/2 -ml-3.5 h-7 w-7 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-amber-500 bg-white shadow-lg flex items-center justify-center hover:scale-110 transition-transform"
        >
          <span className="text-[12px] font-bold text-amber-700">↔</span>
        </button>
      </div>

      {/* Top Floating Badge A */}
      <div className="absolute left-3 top-3 z-[850] rounded-xl border border-amber-300 bg-white/95 px-3 py-1 text-xs font-bold shadow-md text-amber-900 flex items-center gap-1.5 backdrop-blur-xs">
        <span className="w-2 h-2 rounded-full bg-amber-500" />
        <span>Layer A: {MONTHS[a.month - 1]} {a.year}</span>
      </div>

      {/* Top Floating Badge B */}
      <div className="absolute right-12 top-3 z-[850] rounded-xl border border-blue-300 bg-white/95 px-3 py-1 text-xs font-bold shadow-md text-blue-900 flex items-center gap-1.5 backdrop-blur-xs">
        <span className="w-2 h-2 rounded-full bg-blue-500" />
        <span>Layer B: {MONTHS[b.month - 1]} {b.year}</span>
      </div>

      {/* Bottom Floating Hover Status Card */}
      {hoveredInfo && (
        <div className="absolute bottom-3 left-3 z-[850] rounded-xl border border-slate-200 bg-white/95 px-3 py-1.5 text-xs font-mono font-semibold text-slate-800 shadow-md backdrop-blur-xs">
          {hoveredInfo}
        </div>
      )}
    </div>
  );
}
