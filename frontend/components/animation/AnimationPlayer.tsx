"use client";

import { useEffect, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import type { Feature, FeatureCollection } from "geojson";
import type { PathOptions } from "leaflet";
import { getAnimation, getIndexGeoJSON, type IndexName } from "@/lib/api";
import { colorForValue } from "@/lib/classify";

interface Props {
  index: IndexName;
  from?: string; // YYYY-MM
  to?: string;   // YYYY-MM
}

const LATUR: [number, number] = [18.4088, 76.5604];

/**
 * High-performance chronological drought animation player.
 * Walks through 98 sequential observation periods (2016–2026)
 * rendering verified 951-village polygon maps with in-memory caching.
 */
export function AnimationPlayer({ index, from, to }: Props) {
  const [frames, setFrames] = useState<{ period: string; geojson_url: string }[]>([]);
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [fps, setFps] = useState(2);
  const [data, setData] = useState<FeatureCollection | null>(null);
  const [hoveredVillage, setHoveredVillage] = useState<string>("");
  const cache = useRef(new Map<string, FeatureCollection>());

  // Load the sequential frame catalog
  useEffect(() => {
    getAnimation(index, from, to)
      .then((r) => {
        setFrames(r.frames || []);
        setI(0);
      })
      .catch(() => setFrames([]));
  }, [index, from, to]);

  // Load current frame (cached in memory)
  useEffect(() => {
    if (!frames.length) return;
    const f = frames[i];
    if (!f) return;
    if (cache.current.has(f.period)) {
      setData(cache.current.get(f.period)!);
      return;
    }
    const parts = f.period.split("-");
    const year = Number(parts[0]);
    const month = Number(parts[1]);
    if (!year || !month) return;

    getIndexGeoJSON(index, year, month).then((fc) => {
      cache.current.set(f.period, fc);
      setData(fc);
    });
  }, [frames, i, index]);

  // Animation interval timer
  useEffect(() => {
    if (!playing || !frames.length) return;
    const interval = setInterval(() => {
      setI((prev) => (prev + 1) % frames.length);
    }, Math.max(100, 1000 / fps));
    return () => clearInterval(interval);
  }, [playing, fps, frames.length]);

  const style = (f?: Feature): PathOptions => {
    const v = f?.properties?.value as number | undefined;
    return {
      color: "#64748b",
      weight: 0.5,
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
        setHoveredVillage(`${name} (${t}): ${index.toUpperCase()} = ${val} [${cls}]`);
      },
    });

    layer.bindTooltip(
      `<strong>${name}</strong> (${t})<br/>${index.toUpperCase()}: ${val} · ${cls}`,
      { sticky: true, className: "text-xs font-sans rounded shadow bg-white p-1.5 border border-slate-200" }
    );
  };

  const stepBack = () => setI((prev) => (prev > 0 ? prev - 1 : frames.length - 1));
  const stepForward = () => setI((prev) => (prev + 1) % frames.length);

  return (
    <div className="space-y-3">
      {/* Map Display Box */}
      <div className="relative h-[560px] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
        <MapContainer center={LATUR} zoom={10} className="h-full w-full" zoomControl={false}>
          <TileLayer
            url="https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}"
            attribution="&copy; Google Maps Terrain"
          />
          {data && (
            <GeoJSON
              key={`${frames[i]?.period}-${index}`}
              data={data}
              style={style}
              onEachFeature={onEachFeature}
            />
          )}
          <ZoomControl position="topright" />
        </MapContainer>

        {/* Current Period Floating Badge */}
        <div className="absolute left-3 top-3 z-[850] rounded-xl border border-amber-300 bg-white/95 px-3.5 py-1.5 font-mono text-xs font-bold text-amber-900 shadow-md backdrop-blur-xs flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${playing ? "bg-amber-500 animate-ping" : "bg-amber-600"}`} />
          <span>{index.toUpperCase()}</span>
          <span className="text-slate-300">|</span>
          <span className="text-slate-900 text-sm font-extrabold">{frames[i]?.period ?? "—"}</span>
        </div>

        {/* Hovered Village Display */}
        {hoveredVillage && (
          <div className="absolute bottom-3 left-3 z-[850] rounded-xl border border-slate-200 bg-white/95 px-3 py-1.5 text-xs font-mono font-semibold text-slate-800 shadow-md backdrop-blur-xs">
            {hoveredVillage}
          </div>
        )}
      </div>

      {/* Control Strip — Crisp White with Gold Accents */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        {/* Playback Transport Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={stepBack}
            className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs font-bold text-xs"
            title="Step Previous Period"
          >
            ⏮ Step
          </button>

          <button
            type="button"
            onClick={() => setPlaying(!playing)}
            className={`px-4 py-2 rounded-xl font-bold text-xs shadow-xs transition-colors flex items-center gap-2 ${
              playing
                ? "bg-amber-600 text-white hover:bg-amber-700"
                : "bg-slate-900 text-white hover:bg-slate-800"
            }`}
          >
            {playing ? "⏸ Pause Timeline" : "▶ Play Sequence"}
          </button>

          <button
            type="button"
            onClick={stepForward}
            className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs font-bold text-xs"
            title="Step Next Period"
          >
            Step ⏭
          </button>
        </div>

        {/* Slider Timeline Scrubber */}
        <div className="flex-1 min-w-[240px] flex items-center gap-3">
          <input
            type="range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            value={i}
            onChange={(e) => {
              setPlaying(false);
              setI(Number(e.target.value));
            }}
            className="w-full accent-amber-600 cursor-pointer h-2 bg-slate-200 rounded-lg"
          />
          <span className="font-mono text-xs font-bold text-slate-600 min-w-[50px] text-right">
            {i + 1} / {frames.length}
          </span>
        </div>

        {/* Speed / FPS Selector */}
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
          <span>Speed:</span>
          {[1, 2, 4, 8].map((speed) => (
            <button
              key={speed}
              type="button"
              onClick={() => setFps(speed)}
              className={`px-2.5 py-1 rounded-lg border text-xs font-bold ${
                fps === speed
                  ? "border-amber-400 bg-amber-50 text-amber-900"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
