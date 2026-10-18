"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import type { FeatureCollection, Feature } from "geojson";
import type { PathOptions } from "leaflet";
import type * as L from "leaflet";
import { getIndexGeoJSON, type IndexName } from "@/lib/api";
import { colorForValue, classifyValue } from "@/lib/classify";

interface Props {
  index: IndexName;
  a: { year: number; month: number };   // older period
  b: { year: number; month: number };   // newer period
}

const LATUR: [number, number] = [18.4088, 76.5604];

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Bi-Temporal Comparison Curtain Slider.
 * Synchronizes two full-resolution Leaflet map instances with GPU-accelerated CSS clipPath.
 * Wipes cleanly between Period A on the left and Period B on the right at 60 FPS.
 */
export function ComparisonSlider({ index, a, b }: Props) {
  const [fA, setFA] = useState<FeatureCollection | null>(null);
  const [fB, setFB] = useState<FeatureCollection | null>(null);
  const [pct, setPct] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [hoveredInfo, setHoveredInfo] = useState<string>("");
  const containerRef = useRef<HTMLDivElement>(null);

  const [mapA, setMapA] = useState<L.Map | null>(null);
  const [mapB, setMapB] = useState<L.Map | null>(null);

  // Fetch verified GeoJSON for Period A and Period B
  useEffect(() => {
    setHoveredInfo("");
    getIndexGeoJSON(index, a.year, a.month)
      .then(setFA)
      .catch(() => setFA(null));
    getIndexGeoJSON(index, b.year, b.month)
      .then(setFB)
      .catch(() => setFB(null));
  }, [index, a.year, a.month, b.year, b.month]);

  // Synchronize pan and zoom between Map A and Map B
  useEffect(() => {
    if (!mapA || !mapB) return;
    let isSyncing = false;

    const syncAtoB = () => {
      if (isSyncing) return;
      isSyncing = true;
      mapB.setView(mapA.getCenter(), mapA.getZoom(), { animate: false });
      isSyncing = false;
    };

    const syncBtoA = () => {
      if (isSyncing) return;
      isSyncing = true;
      mapA.setView(mapB.getCenter(), mapB.getZoom(), { animate: false });
      isSyncing = false;
    };

    mapA.on("move", syncAtoB);
    mapB.on("move", syncBtoA);

    return () => {
      mapA.off("move", syncAtoB);
      mapB.off("move", syncBtoA);
    };
  }, [mapA, mapB]);

  const getFeatureValue = (f?: Feature) => {
    const p = f?.properties || {};
    if (p.value != null && !isNaN(p.value)) return Number(p.value);
    const idxLower = String(index || "cdi").toLowerCase();
    for (const [k, v] of Object.entries(p)) {
      if (k.toLowerCase() === idxLower && v != null && !isNaN(v as any)) {
        return Number(v);
      }
    }
    if (idxLower === "rain" && p.Rain_mm != null) return Number(p.Rain_mm);
    if (idxLower === "cdi" && p.CDI != null) return Number(p.CDI);
    if (idxLower === "ndvi" && p.NDVI != null) return Number(p.NDVI);
    if (idxLower === "vhi" && p.VHI != null) return Number(p.VHI);
    if (idxLower === "vci" && p.VCI != null) return Number(p.VCI);
    if (idxLower === "evi" && p.EVI != null) return Number(p.EVI);
    if (idxLower === "pci" && p.PCI != null) return Number(p.PCI);
    if (idxLower === "spi1" && p.SPI1 != null) return Number(p.SPI1);
    if (idxLower === "spi3" && p.SPI3 != null) return Number(p.SPI3);
    if (idxLower === "spi6" && p.SPI6 != null) return Number(p.SPI6);
    if (idxLower === "spi12" && p.SPI12 != null) return Number(p.SPI12);
    return undefined;
  };

  const styleA = (f?: Feature): PathOptions => {
    const v = getFeatureValue(f);
    return {
      color: "#475569",
      weight: 0.6,
      fillColor: colorForValue(v, index),
      fillOpacity: 0.85,
    };
  };

  const styleB = (f?: Feature): PathOptions => {
    const v = getFeatureValue(f);
    return {
      color: "#1e293b",
      weight: 0.6,
      fillColor: colorForValue(v, index),
      fillOpacity: 0.85,
    };
  };

  const onEachFeatureA = (feature: Feature, layer: any) => {
    const p = feature.properties || {};
    const name = p.village || p.VILLAGE || p.name || "Village";
    const t = p.tehsil || p.TEHSIL || "";
    const v = getFeatureValue(feature);
    const val = v != null ? Number(v).toFixed(2) : "No data";
    const cls = classifyValue(v, index);

    layer.on({
      mouseover: () => {
        setHoveredInfo(`Layer A [${MONTHS[a.month - 1]} ${a.year}]: ${name} (${t}) — ${index.toUpperCase()} = ${val} (${cls})`);
      },
    });

    layer.bindTooltip(
      `<div class="font-sans text-xs">
        <div class="font-bold text-slate-900">${name} (${t})</div>
        <div class="text-amber-800 font-semibold">Layer A: ${MONTHS[a.month - 1]} ${a.year}</div>
        <div class="font-mono text-slate-700">${index.toUpperCase()}: <b>${val}</b> (${cls})</div>
      </div>`,
      { sticky: true, className: "rounded-lg shadow bg-white p-1.5 border border-slate-200" }
    );
  };

  const onEachFeatureB = (feature: Feature, layer: any) => {
    const p = feature.properties || {};
    const name = p.village || p.VILLAGE || p.name || "Village";
    const t = p.tehsil || p.TEHSIL || "";
    const v = getFeatureValue(feature);
    const val = v != null ? Number(v).toFixed(2) : "No data";
    const cls = classifyValue(v, index);

    layer.on({
      mouseover: () => {
        setHoveredInfo(`Layer B [${MONTHS[b.month - 1]} ${b.year}]: ${name} (${t}) — ${index.toUpperCase()} = ${val} (${cls})`);
      },
    });

    layer.bindTooltip(
      `<div class="font-sans text-xs">
        <div class="font-bold text-slate-900">${name} (${t})</div>
        <div class="text-blue-800 font-semibold">Layer B: ${MONTHS[b.month - 1]} ${b.year}</div>
        <div class="font-mono text-slate-700">${index.toUpperCase()}: <b>${val}</b> (${cls})</div>
      </div>`,
      { sticky: true, className: "rounded-lg shadow bg-white p-1.5 border border-slate-200" }
    );
  };

  const updatePosition = (clientX: number) => {
    if (!containerRef.current) return;
    const r = containerRef.current.getBoundingClientRect();
    const pos = Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100));
    setPct(pos);
  };

  // Global mouse/touch drag listener
  useEffect(() => {
    if (!isDragging) return;
    const handleMove = (e: MouseEvent) => {
      updatePosition(e.clientX);
    };
    const handleUp = () => {
      setIsDragging(false);
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches[0]) updatePosition(e.touches[0].clientX);
    };
    const handleTouchEnd = () => {
      setIsDragging(false);
    };

    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    window.addEventListener("touchmove", handleTouchMove);
    window.addEventListener("touchend", handleTouchEnd);

    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
    };
  }, [isDragging]);

  // Compute aggregate statistics between Period A and Period B
  const stats = useMemo(() => {
    let sumA = 0, countA = 0;
    let sumB = 0, countB = 0;

    if (fA?.features) {
      for (const f of fA.features) {
        const v = getFeatureValue(f);
        if (v != null && !isNaN(v)) {
          sumA += v;
          countA++;
        }
      }
    }

    if (fB?.features) {
      for (const f of fB.features) {
        const v = getFeatureValue(f);
        if (v != null && !isNaN(v)) {
          sumB += v;
          countB++;
        }
      }
    }

    const meanA = countA > 0 ? sumA / countA : null;
    const meanB = countB > 0 ? sumB / countB : null;
    const delta = meanA != null && meanB != null ? meanB - meanA : null;

    return { meanA, meanB, delta, countA, countB };
  }, [fA, fB, index]);

  return (
    <div className="space-y-3 select-none">
      {/* Map Viewport Container */}
      <div
        ref={containerRef}
        className="relative h-[600px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs"
      >
        {/* Layer A (Underlying Map): Covers entire container */}
        <div className="absolute inset-0 z-0">
          <MapContainer
            center={LATUR}
            zoom={10}
            minZoom={8}
            maxZoom={15}
            className="h-full w-full"
            zoomControl={false}
            ref={setMapA}
          >
            <TileLayer
              url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
              attribution="&copy; Google Maps Terrain"
            />
            {fA && (
              <GeoJSON
                key={`layerA-${a.year}-${a.month}-${index}`}
                data={fA}
                style={styleA}
                onEachFeature={onEachFeatureA}
              />
            )}
            <ZoomControl position="topright" />
          </MapContainer>
        </div>

        {/* Layer B (Overlying Map): Covers entire container, clipped from pct% to 100% */}
        <div
          className="absolute inset-0 z-10"
          style={{
            clipPath: `polygon(${pct}% 0%, 100% 0%, 100% 100%, ${pct}% 100%)`,
            WebkitClipPath: `polygon(${pct}% 0%, 100% 0%, 100% 100%, ${pct}% 100%)`,
          }}
        >
          <MapContainer
            center={LATUR}
            zoom={10}
            minZoom={8}
            maxZoom={15}
            className="h-full w-full"
            zoomControl={false}
            ref={setMapB}
          >
            <TileLayer
              url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
              attribution="&copy; Google Maps Terrain"
            />
            {fB && (
              <GeoJSON
                key={`layerB-${b.year}-${b.month}-${index}`}
                data={fB}
                style={styleB}
                onEachFeature={onEachFeatureB}
              />
            )}
          </MapContainer>
        </div>

        {/* Dividing Curtain Bar & Draggable Handle */}
        <div
          className="pointer-events-auto absolute inset-y-0 z-20"
          style={{ left: `calc(${pct}% - 2px)` }}
        >
          {/* Vertical Dividing Line */}
          <div className="h-full w-1 bg-amber-600 shadow-xl" />

          {/* Center Drag Handle */}
          <button
            type="button"
            aria-label="Drag comparison curtain divider"
            onMouseDown={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onTouchStart={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            className={`absolute top-1/2 -ml-3.5 h-8 w-8 -translate-y-1/2 cursor-ew-resize rounded-full border-2 border-amber-600 bg-white shadow-xl flex items-center justify-center transition-transform ${
              isDragging ? "scale-125 bg-amber-500 text-white" : "hover:scale-110 text-amber-700"
            }`}
          >
            <span className="text-[13px] font-black leading-none">↔</span>
          </button>
        </div>

        {/* Top Floating Badge A */}
        <div className="absolute left-3 top-3 z-30 rounded-xl border border-amber-300 bg-white/95 px-3 py-1.5 text-xs font-bold shadow-md text-amber-900 flex items-center gap-2 backdrop-blur-xs">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-600" />
          <span>Layer A: {MONTHS[a.month - 1]} {a.year}</span>
          {stats.meanA != null && (
            <span className="ml-1 px-1.5 py-0.5 rounded bg-amber-100 font-mono text-[11px]">
              Mean: {stats.meanA.toFixed(2)}
            </span>
          )}
        </div>

        {/* Top Floating Badge B */}
        <div className="absolute right-12 top-3 z-30 rounded-xl border border-blue-300 bg-white/95 px-3 py-1.5 text-xs font-bold shadow-md text-blue-900 flex items-center gap-2 backdrop-blur-xs">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-600" />
          <span>Layer B: {MONTHS[b.month - 1]} {b.year}</span>
          {stats.meanB != null && (
            <span className="ml-1 px-1.5 py-0.5 rounded bg-blue-100 font-mono text-[11px]">
              Mean: {stats.meanB.toFixed(2)}
            </span>
          )}
        </div>

        {/* Floating Split Ratio Display */}
        <div className="absolute bottom-3 right-3 z-30 rounded-xl border border-slate-200 bg-white/95 px-3 py-1.5 text-xs font-mono font-bold text-slate-700 shadow-md backdrop-blur-xs">
          Split: {Math.round(pct)}% A | {Math.round(100 - pct)}% B
        </div>

        {/* Bottom Floating Hover Status Card */}
        {hoveredInfo && (
          <div className="absolute bottom-3 left-3 z-30 rounded-xl border border-slate-200 bg-white/95 px-3.5 py-1.5 text-xs font-mono font-semibold text-slate-800 shadow-md backdrop-blur-xs max-w-lg truncate">
            {hoveredInfo}
          </div>
        )}
      </div>

      {/* Analytical Comparison Metric Delta Summary Strip */}
      <div className="rounded-2xl border border-slate-200 bg-white p-3.5 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-bold uppercase text-[10px]">Active Index:</span>
            <span className="font-extrabold text-amber-800 font-mono">{index.toUpperCase()}</span>
          </div>
          <div className="h-4 w-px bg-slate-200" />
          <div>
            <span className="text-slate-500 text-[10px] uppercase font-bold mr-1">Layer A Mean:</span>
            <span className="font-mono font-bold text-slate-800">
              {stats.meanA != null ? stats.meanA.toFixed(3) : "—"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 text-[10px] uppercase font-bold mr-1">Layer B Mean:</span>
            <span className="font-mono font-bold text-slate-800">
              {stats.meanB != null ? stats.meanB.toFixed(3) : "—"}
            </span>
          </div>
        </div>

        {/* Delta Difference Pill */}
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-[10px] uppercase font-bold">Bi-Temporal Delta (B − A):</span>
          {stats.delta != null ? (
            <span className={`px-2.5 py-0.5 rounded-lg font-mono font-black text-xs ${
              stats.delta > 0.05
                ? (index === "cdi" ? "bg-rose-100 text-rose-800" : "bg-emerald-100 text-emerald-800")
                : stats.delta < -0.05
                ? (index === "cdi" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800")
                : "bg-slate-100 text-slate-700"
            }`}>
              {stats.delta > 0 ? `+${stats.delta.toFixed(3)}` : stats.delta.toFixed(3)}
            </span>
          ) : (
            <span className="text-slate-400 font-mono">—</span>
          )}
        </div>
      </div>
    </div>
  );
}
