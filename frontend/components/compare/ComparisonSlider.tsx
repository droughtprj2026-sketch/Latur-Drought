"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import type { FeatureCollection, Feature } from "geojson";
import L from "leaflet";
import { getIndexGeoJSON, type IndexName } from "@/lib/api";
import { colorForIndex, specForIndex } from "@/lib/metrics";
import { LegendStrip } from "@/components/map/MapLegend";

interface Props {
  index: IndexName;
  a: { year: number; month: number };
  b: { year: number; month: number };
}

const LATUR: [number, number] = [18.4088, 76.5604];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Renders two GeoJSON layers on separate panes and clips each to its half of the viewport. */
function SplitLayers({
  fA, fB, index, pctRef,
}: {
  fA: FeatureCollection | null;
  fB: FeatureCollection | null;
  index: IndexName;
  pctRef: React.RefObject<number>;
}) {
  const map = useMap();
  const layerARef = useRef<L.GeoJSON | null>(null);
  const layerBRef = useRef<L.GeoJSON | null>(null);
  const paneARef = useRef<HTMLElement | null>(null);
  const paneBRef = useRef<HTMLElement | null>(null);

  const styleFor = useCallback(
    (f?: Feature) => {
      const v = f?.properties?.value as number | undefined;
      return {
        color: "#ffffff",
        weight: 0.6,
        fillColor: colorForIndex(index, v),
        fillOpacity: 0.85,
      };
    },
    [index],
  );

  const tooltip = (f: Feature, l: L.Layer) => {
    const p = f.properties || {};
    const name = p.village || p.VILLAGE || p.name || "Village";
    const t = p.tehsil || p.TEHSIL || "";
    const val = p.value != null && !isNaN(p.value) ? Number(p.value).toFixed(2) : "--";
    const cls = p.class || "None";
    (l as L.Path).bindTooltip(
      `<b>${name}</b> (${t})<br/>${index.toUpperCase()}: ${val} · ${cls}`,
      { sticky: true, className: "text-xs font-sans rounded shadow bg-white p-1.5 border border-slate-200" },
    );
  };

  // Create panes once.
  useEffect(() => {
    if (!paneARef.current) {
      const pa = map.createPane("compareA");
      pa.style.zIndex = "450";
      paneARef.current = pa;
    }
    if (!paneBRef.current) {
      const pb = map.createPane("compareB");
      pb.style.zIndex = "451";
      paneBRef.current = pb;
    }
  }, [map]);

  // Update clip rectangles when the map moves or when pct changes.
  const updateClip = useCallback(() => {
    const size = map.getSize();
    const pct = pctRef.current ?? 50;
    const splitX = Math.round(size.x * pct / 100);
    if (paneARef.current) {
      paneARef.current.style.clipPath = `inset(0 ${size.x - splitX}px 0 0)`;
    }
    if (paneBRef.current) {
      paneBRef.current.style.clipPath = `inset(0 0 0 ${splitX}px)`;
    }
  }, [map, pctRef]);

  useEffect(() => {
    updateClip();
    map.on("move", updateClip);
    map.on("zoom", updateClip);
    map.on("resize", updateClip);
    return () => {
      map.off("move", updateClip);
      map.off("zoom", updateClip);
      map.off("resize", updateClip);
    };
  }, [map, updateClip]);

  // Layer A.
  useEffect(() => {
    layerARef.current?.remove();
    layerARef.current = null;
    if (!fA) return;
    const layer = L.geoJSON(fA, { pane: "compareA", style: styleFor, onEachFeature: tooltip }).addTo(map);
    layerARef.current = layer;
    updateClip();
    return () => { layer.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fA, index, map]);

  // Layer B.
  useEffect(() => {
    layerBRef.current?.remove();
    layerBRef.current = null;
    if (!fB) return;
    const layer = L.geoJSON(fB, { pane: "compareB", style: styleFor, onEachFeature: tooltip }).addTo(map);
    layerBRef.current = layer;
    updateClip();
    return () => { layer.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fB, index, map]);

  return null;
}

/**
 * Bi-temporal side-by-side comparison curtain slider.
 * Uses a single Leaflet map with two clip-masked GeoJSON layers
 * so pan, zoom and tooltip all work across the full viewport.
 */
export function ComparisonSlider({ index, a, b }: Props) {
  const [fA, setFA] = useState<FeatureCollection | null>(null);
  const [fB, setFB] = useState<FeatureCollection | null>(null);
  const [pct, setPct] = useState(50);
  const pctRef = useRef(50);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getIndexGeoJSON(index, a.year, a.month).then(setFA).catch(() => setFA(null));
    getIndexGeoJSON(index, b.year, b.month).then(setFB).catch(() => setFB(null));
  }, [index, a.year, a.month, b.year, b.month]);

  const onDrag = useCallback((clientX: number) => {
    if (!barRef.current) return;
    const r = barRef.current.getBoundingClientRect();
    const p = Math.max(5, Math.min(95, ((clientX - r.left) / r.width) * 100));
    pctRef.current = p;
    setPct(p);
  }, []);

  // Expose pctRef changes to the SplitLayers clip updater.
  useEffect(() => {
    pctRef.current = pct;
    // Fire a custom event so clip updates without map movement.
    barRef.current?.querySelector(".leaflet-container")
      ?.dispatchEvent(new Event("resize"));
  }, [pct]);

  return (
    <div
      className="relative h-[600px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs select-none"
      ref={barRef}
      onMouseMove={(e) => (e.buttons & 1) && onDrag(e.clientX)}
      onTouchMove={(e) => onDrag(e.touches[0].clientX)}
    >
      <MapContainer center={LATUR} zoom={10} className="h-full w-full" zoomControl={false}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; <a href='https://openstreetmap.org/copyright'>OpenStreetMap</a>"
        />
        <SplitLayers fA={fA} fB={fB} index={index} pctRef={pctRef} />
      </MapContainer>

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
          onTouchStart={(e) => {
            e.preventDefault();
            const move = (ev: TouchEvent) => onDrag(ev.touches[0].clientX);
            const up = () => {
              window.removeEventListener("touchmove", move);
              window.removeEventListener("touchend", up);
            };
            window.addEventListener("touchmove", move);
            window.addEventListener("touchend", up);
          }}
          className="absolute top-1/2 -ml-3.5 h-7 w-7 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-amber-500 bg-white shadow-lg flex items-center justify-center hover:scale-110 transition-transform"
        >
          <span className="text-[12px] font-bold text-amber-700">&#x2194;</span>
        </button>
      </div>

      {/* Period badges */}
      <div className="absolute left-3 top-3 z-[850] rounded-xl border border-amber-300 bg-white/95 px-3 py-1 text-xs font-bold shadow-md text-amber-900 flex items-center gap-1.5 backdrop-blur-xs">
        <span className="w-2 h-2 rounded-full bg-amber-500" />
        <span>Layer A: {MONTHS[a.month - 1]} {a.year}</span>
      </div>
      <div className="absolute right-12 top-3 z-[850] rounded-xl border border-blue-300 bg-white/95 px-3 py-1 text-xs font-bold shadow-md text-blue-900 flex items-center gap-1.5 backdrop-blur-xs">
        <span className="w-2 h-2 rounded-full bg-blue-500" />
        <span>Layer B: {MONTHS[b.month - 1]} {b.year}</span>
      </div>

      <div className="absolute bottom-3 right-3 z-[850] max-w-[min(520px,52%)]">
        <LegendStrip spec={specForIndex(index)} />
      </div>
    </div>
  );
}
