"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  GeoJSON, LayersControl, MapContainer, ScaleControl, TileLayer,
  ZoomControl, useMap, Popup,
} from "react-leaflet";
import type { Feature, FeatureCollection } from "geojson";
import type { Layer, PathOptions, LeafletMouseEvent } from "leaflet";
import { getIndexGeoJSON, getVillageIndices, getStatus, type IndexName } from "@/lib/api";
import { classifyValue, colorForValue, D_CODES, D_COLORS } from "@/lib/classify";
import L from "leaflet";
import { BASEMAPS } from "./basemaps";
import { BasemapSwitcher } from "./BasemapSwitcher";
import { BoundaryLayers } from "./BoundaryLayers";
import { LegendBar } from "./LegendBar";
import { MapExportButtons } from "@/components/export/MapExportButtons";

interface Props {
  index: IndexName;
  year: number;
  month: number;
  tehsil?: string;
  village?: string;
  latest?: boolean;
}

const LATUR_CENTER: [number, number] = [18.4088, 76.5604];
const DEFAULT_ZOOM = 10;

function FitToData({ geojson }: { geojson: FeatureCollection | null }) {
  const map = useMap();
  useEffect(() => {
    if (!geojson?.features?.length) return;
    const L = require("leaflet");
    const layer = L.geoJSON(geojson);
    map.fitBounds(layer.getBounds(), { padding: [20, 20] });
  }, [geojson, map]);
  return null;
}

function HoverPipe() {
  const map = useMap();
  useEffect(() => {
    const onMove = (e: LeafletMouseEvent) => {
      window.dispatchEvent(new CustomEvent("latur:latlon", {
        detail: { lat: e.latlng.lat, lon: e.latlng.lng },
      }));
    };
    map.on("mousemove", onMove);
    return () => { map.off("mousemove", onMove); };
  }, [map]);
  return null;
}

/** Number formatter with null-safe fallback. */
function nf(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return "—";
  return Number(v).toFixed(digits);
}

function classColor(code: string | null | undefined): string {
  if (!code) return "#e5e7eb";
  const idx = D_CODES.indexOf(code as any);
  return idx >= 0 ? D_COLORS[idx] : "#e5e7eb";
}

function buildPopupHtml(f: Feature, effective: { y: number; m: number }): string {
  const p = f.properties || {};
  const period = `${effective.y}-${String(effective.m).padStart(2, "0")}`;
  const cdi = p.CDI ?? p.composite_drought_score ?? p.value;
  const cdiClass = p.CDI_class ?? p.composite_drought_class ?? "";
  const droughtMonth = p.drought_month ?? false;
  const severity = p.drought_severity ?? "";

  return `
    <div class="text-xs font-sans leading-relaxed">
      <div class="font-bold text-slate-900 dark:text-slate-100 mb-1">
        ${p.village || p.name || "Village"} · ${p.tehsil || ""}
      </div>
      <div class="text-[10px] text-slate-500 mb-2">${period}</div>
      <div class="flex gap-2 mb-2">
        <span class="rounded px-2 py-0.5 text-[10px] font-bold"
              style="background:${classColor(cdiClass)};color:#fff">
          ${cdiClass || "—"}
        </span>
        ${droughtMonth ? '<span class="rounded px-2 py-0.5 text-[10px] font-bold text-white bg-red-600">DROUGHT MONTH</span>' : ''}
      </div>
      <div class="grid grid-cols-2 gap-1 text-[10px]">
        <div><span class="text-slate-500">CDI:</span> <span class="font-mono">${nf(cdi, 3)}</span></div>
        <div><span class="text-slate-500">NDVI:</span> <span class="font-mono">${nf(p.NDVI, 3)}</span></div>
        <div><span class="text-slate-500">EVI:</span> <span class="font-mono">${nf(p.EVI, 3)}</span></div>
        <div><span class="text-slate-500">VCI:</span> <span class="font-mono">${nf(p.VCI, 3)}</span></div>
        <div><span class="text-slate-500">VHI:</span> <span class="font-mono">${nf(p.VHI, 3)}</span></div>
        <div><span class="text-slate-500">PCI:</span> <span class="font-mono">${nf(p.PCI, 3)}</span></div>
        <div><span class="text-slate-500">SPI-3:</span> <span class="font-mono">${nf(p.SPI3, 3)}</span></div>
        <div><span class="text-slate-500">Rain:</span> <span class="font-mono">${nf(p.Rain_mm, 2)} mm</span></div>
      </div>
      ${severity ? `<div class="mt-1 text-[10px] text-slate-500">Severity: ${severity}</div>` : ""}
    </div>
  `;
}

export default function LaturMap({
  index, year, month, tehsil = "All", village = "", latest = false,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [basemapId, setBasemapId] = useState<string>("carto-light");
  const [pixels, setPixels] = useState<FeatureCollection | null>(null);
  const [effective, setEffective] = useState<{ y: number; m: number }>({ y: year, m: month });
  const [err, setErr] = useState<string | null>(null);
  const [isFull, setFull] = useState(false);
  const [selectedVillage, setSelectedVillage] = useState<Feature | null>(null);

  const basemap = useMemo(
    () => BASEMAPS.find((b) => b.id === basemapId) ?? BASEMAPS[0],
    [basemapId]
  );

  useEffect(() => {
    setErr(null); setPixels(null); setSelectedVillage(null);
    const resolve = async () => {
      if (!latest) return { y: year, m: month };
      try {
        const s = await getStatus();
        const pid = s.sentinel2?.latest_period_id ?? s.chirps?.latest_period_id;
        if (!pid) return { y: year, m: month };
        const [yy, mm] = pid.split("-");
        return { y: Number(yy), m: Number(mm) };
      } catch { return { y: year, m: month }; }
    };
    resolve().then((e) => {
      setEffective(e);
      return getVillageIndices(index, e.y, e.m);
    }).then(setPixels).catch((e) => setErr(String(e)));
  }, [index, year, month, latest]);

  const styleFor = (f?: Feature): PathOptions => {
    const v = f?.properties?.value as number | undefined;
    return { color: "#111", weight: 0.15, fillColor: colorForValue(v, index), fillOpacity: 0.82 };
  };

  const pointToLayer = (f: Feature, latlng: L.LatLng) => {
    const L = require("leaflet");
    const p = f.properties || {};
    const score = p.score as number | undefined;
    const v = p.value as number | undefined;
    const cdiClass = p.cdi_class || p.CDI_class || p.composite_drought_class || "";
    const color = classColor(cdiClass);
    const radius = score != null && score >= 0 ? 4 + score * 6 : 5;
    return L.circleMarker(latlng, {
      radius,
      fillColor: color,
      color: "#222",
      weight: 1,
      fillOpacity: 0.85,
    });
  };

  /** Build a rich popup showing ALL indices for the clicked village. */
  const onEach = (f: Feature, layer: Layer) => {
    const p = f.properties || {};
    const period = `${effective.y}-${String(effective.m).padStart(2, "0")}`;
    const cdi = p.CDI ?? p.composite_drought_score ?? p.value;
    const cdiClass = p.CDI_class ?? p.composite_drought_class ?? "";
    const droughtMonth = p.drought_month ?? false;
    const severity = p.drought_severity ?? "";

    const html = `
      <div class="text-xs font-sans leading-relaxed">
        <div class="font-bold text-slate-900 dark:text-slate-100 mb-1">
          ${p.village || p.name || "Village"} · ${p.tehsil || ""}
        </div>
        <div class="text-[10px] text-slate-500 mb-2">${period}</div>
        <div class="flex gap-2 mb-2">
          <span class="rounded px-2 py-0.5 text-[10px] font-bold"
                style="background:${classColor(cdiClass)};color:#fff">
            ${cdiClass || "—"}
          </span>
          ${droughtMonth ? '<span class="rounded px-2 py-0.5 text-[10px] font-bold text-white bg-red-600">DROUGHT MONTH</span>' : ''}
        </div>
        <div class="grid grid-cols-2 gap-1 text-[10px]">
          <div><span class="text-slate-500">CDI:</span> <span class="font-mono">${nf(cdi, 3)}</span></div>
          <div><span class="text-slate-500">NDVI:</span> <span class="font-mono">${nf(p.NDVI, 3)}</span></div>
          <div><span class="text-slate-500">EVI:</span> <span class="font-mono">${nf(p.EVI, 3)}</span></div>
          <div><span class="text-slate-500">VCI:</span> <span class="font-mono">${nf(p.VCI, 3)}</span></div>
          <div><span class="text-slate-500">VHI:</span> <span class="font-mono">${nf(p.VHI, 3)}</span></div>
          <div><span class="text-slate-500">PCI:</span> <span class="font-mono">${nf(p.PCI, 3)}</span></div>
          <div><span class="text-slate-500">SPI-3:</span> <span class="font-mono">${nf(p.SPI3, 3)}</span></div>
          <div><span class="text-slate-500">Rain:</span> <span class="font-mono">${nf(p.Rain_mm, 2)} mm</span></div>
        </div>
        <div class="mt-1 text-[10px] text-slate-500">
          Click to keep this info open
        </div>
      </div>
    `;
    layer.bindPopup(html);
    layer.on("click", () => setSelectedVillage(f));
  };

  const toggleFullscreen = () => {
    setFull((f) => !f);
  };

  return (
    <div ref={rootRef}
         className={isFull
           ? "fixed inset-0 z-[1000] bg-white dark:bg-slate-900"
           : "relative h-full w-full"}>
      <MapContainer center={LATUR_CENTER} zoom={DEFAULT_ZOOM} minZoom={7}
                    maxZoom={basemap.maxZoom ?? 18} zoomControl={false}
                    scrollWheelZoom className="h-full w-full">
        <TileLayer key={basemap.id} url={basemap.url}
                   attribution={basemap.attribution}
                   maxZoom={basemap.maxZoom ?? 19} />

        <LayersControl position="bottomright" collapsed={false}>
          <LayersControl.Overlay name="District boundary" checked>
            <GeoJSONToggleWrapper child={<BoundaryLayers showDistrict showTehsils={false} />} />
          </LayersControl.Overlay>
          <LayersControl.Overlay name="Tehsil boundary" checked>
            <GeoJSONToggleWrapper child={<BoundaryLayers showDistrict={false} showTehsils />} />
          </LayersControl.Overlay>
          <LayersControl.Overlay name="Villages">
            <GeoJSONToggleWrapper child={<BoundaryLayers showDistrict={false} showTehsils={false} showVillages />} />
          </LayersControl.Overlay>
        </LayersControl>

        {pixels && (
          <GeoJSON
            key={`${index}-${effective.y}-${effective.m}-${tehsil}-${village}`}
            data={pixels}
            pointToLayer={pointToLayer}
            style={styleFor}
            onEachFeature={onEach}
          />
        )}

        {selectedVillage && (
          <Popup position={[selectedVillage.properties?.lat || 18.4088, selectedVillage.properties?.lon || 76.5604]}>
            <div className="p-2">
              <button onClick={() => setSelectedVillage(null)}
                      className="text-[10px] text-slate-500 hover:text-slate-900 mb-1">✕ Close</button>
              <div dangerouslySetInnerHTML={{ __html: buildPopupHtml(selectedVillage, effective) }} />
            </div>
          </Popup>
        )}

        <ZoomControl position="topright" />
        <ScaleControl position="bottomleft" imperial={false} />
        <FitToData geojson={pixels} />
        <HoverPipe />
      </MapContainer>

      <BasemapSwitcher value={basemapId} onChange={setBasemapId} />
      <LegendBar />

      <button onClick={toggleFullscreen}
              aria-label={isFull ? "Exit fullscreen" : "Enter fullscreen"}
              className="absolute right-3 top-32 z-[400] rounded bg-white/90 px-2 py-1 text-xs
                         shadow dark:bg-slate-900/90">
        {isFull ? "Exit" : "⛶"}
      </button>

      <MapExportButtons index={index} year={effective.y} month={effective.m}
                        getMapRoot={() => rootRef.current} />

      <div className="absolute bottom-14 left-3 rounded bg-white/90 px-2 py-1 text-xs shadow
                      dark:bg-slate-900/90">
        {index.toUpperCase()} · {effective.y}-{String(effective.m).padStart(2, "0")}
        {latest && <span className="ml-2 text-emerald-700 dark:text-emerald-300">(latest)</span>}
      </div>

      {err && (
        <div className="absolute bottom-14 right-3 rounded bg-red-50 px-2 py-1 text-xs text-red-700 shadow">
          {err}
        </div>
      )}
    </div>
  );
}

function GeoJSONToggleWrapper({ child }: { child: React.ReactNode }) {
  return <>{child}</>;
}
