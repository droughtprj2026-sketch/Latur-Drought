"use client";

import { useEffect, useRef, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import type { Feature, FeatureCollection } from "geojson";
import type { PathOptions } from "leaflet";
import { getAnimation, getIndexGeoJSON, type IndexName } from "@/lib/api";
import { colorForValue } from "@/lib/classify";

interface Props {
  index: IndexName;
  from?: string;      // YYYY-MM
  to?: string;        // YYYY-MM
}

const LATUR: [number, number] = [18.4088, 76.5604];

/**
 * Animation player — walks every weekly / monthly frame in the given
 * range, reading each frame LIVE from the API. No frame is faked.
 */
export function AnimationPlayer({ index, from, to }: Props) {
  const [frames, setFrames] = useState<{ period: string; geojson_url: string }[]>([]);
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [fps, setFps] = useState(2);
  const [data, setData] = useState<FeatureCollection | null>(null);
  const cache = useRef(new Map<string, FeatureCollection>());

  // Load the frame index.
  useEffect(() => {
    getAnimation(index, from, to).then((r) => {
      setFrames(r.frames);
      setI(0);
    }).catch(() => setFrames([]));
  }, [index, from, to]);

  // Load current frame (uses cache).
  useEffect(() => {
    if (!frames.length) return;
    const f = frames[i];
    if (!f) return;
    if (cache.current.has(f.period)) {
      setData(cache.current.get(f.period)!);
      return;
    }
    const [, year, month] = f.period.match(/^(\d{4})-(\d{2})$/) || [];
    if (!year || !month) return;
    getIndexGeoJSON(index, Number(year), Number(month)).then((fc) => {
      cache.current.set(f.period, fc);
      setData(fc);
    });
  }, [frames, i, index]);

  // Playback.
  useEffect(() => {
    if (!playing || !frames.length) return;
    const id = setInterval(
      () => setI((prev) => (prev + 1) % frames.length),
      Math.max(100, 1000 / fps),
    );
    return () => clearInterval(id);
  }, [playing, fps, frames.length]);

  const style = (f?: Feature): PathOptions => {
    const v = f?.properties?.value as number | undefined;
    return { color: "#111", weight: 0.15, fillColor: colorForValue(v), fillOpacity: 0.82 };
  };

  return (
    <div className="space-y-2">
      <div className="relative h-[520px] overflow-hidden rounded-lg border
                      border-slate-200 dark:border-slate-800">
        <MapContainer center={LATUR} zoom={10} className="h-full w-full" zoomControl={false}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                     attribution="&copy; OSM · CARTO" />
          {data && <GeoJSON key={frames[i]?.period} data={data} style={style} />}
          <ZoomControl position="topright" />
        </MapContainer>
        <div className="absolute left-3 top-3 rounded bg-white/90 px-2 py-0.5 font-mono text-xs shadow
                        dark:bg-slate-900/90">
          {index.toUpperCase()} · {frames[i]?.period ?? "—"}
        </div>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <button onClick={() => setPlaying((p) => !p)}
                className="rounded border border-slate-300 px-3 py-1 dark:border-slate-700">
          {playing ? "Pause" : "Play"}
        </button>
        <input type="range" min={0} max={Math.max(0, frames.length - 1)} value={i}
               onChange={(e) => setI(Number(e.target.value))}
               className="flex-1 accent-blue-600" />
        <label className="text-xs text-slate-500">
          fps
          <input type="number" min={1} max={10} value={fps}
                 onChange={(e) => setFps(Number(e.target.value))}
                 className="ml-1 w-12 rounded border border-slate-300 bg-transparent
                            px-1 py-0.5 text-xs dark:border-slate-700" />
        </label>
        <span className="font-mono text-xs text-slate-500">
          {i + 1}/{frames.length}
        </span>
      </div>
    </div>
  );
}
