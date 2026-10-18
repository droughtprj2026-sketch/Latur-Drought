"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import {
  GeoJSON,
  MapContainer,
  ScaleControl,
  TileLayer,
  ZoomControl,
  useMap,
} from "react-leaflet";
import type { Feature, FeatureCollection } from "geojson";
import type { Layer, PathOptions, LeafletMouseEvent } from "leaflet";
import L from "leaflet";
import { BASEMAPS } from "./basemaps";
import { BasemapSwitcher } from "./BasemapSwitcher";
import { LegendBar } from "./LegendBar";
import { D_CODES, D_COLORS } from "@/lib/classify";
import type { VillageProperties } from "@/components/panels/VillageIntelligenceDrawer";

export type MetricName =
  | "cdi"
  | "cdi_class"
  | "ndvi"
  | "evi"
  | "vci"
  | "vhi"
  | "spi1"
  | "spi3"
  | "spi6"
  | "spi12"
  | "rain";

interface Props {
  metric: MetricName;
  tehsil?: string;
  selectedVillageName?: string;
  currentPeriod?: string;
  onSelectVillage?: (props: VillageProperties) => void;
  geeTileUrl?: string | null;
  showGeeLayer?: boolean;
}

const LATUR_CENTER: [number, number] = [18.4088, 76.5604];
const DEFAULT_ZOOM = 9;

// Color ramp helpers
function getCDIColor(code?: string, score?: number | null): string {
  if (code) {
    const idx = D_CODES.indexOf(code as any);
    if (idx >= 0) return D_COLORS[idx];
  }
  if (score == null || isNaN(score)) return "#64748b"; // fallback slate
  if (score < 0.20) return "#22c55e"; // Normal (Green)
  if (score < 0.35) return "#eab308"; // D0 (Yellow)
  if (score < 0.50) return "#f59e0b"; // D1 (Amber)
  if (score < 0.65) return "#ea580c"; // D2 (Orange)
  if (score < 0.80) return "#dc2626"; // D3 (Red)
  return "#7f1d1d"; // D4 (Dark Red)
}

function getNDVIColor(val?: number | null): string {
  if (val == null || isNaN(val)) return "#475569";
  if (val < 0.15) return "#854d0e";
  if (val < 0.25) return "#ca8a04";
  if (val < 0.35) return "#a3e635";
  if (val < 0.45) return "#4ade80";
  return "#15803d";
}

function getVCIColor(val?: number | null): string {
  if (val == null || isNaN(val)) return "#475569";
  if (val < 10) return "#7f1d1d";
  if (val < 20) return "#dc2626";
  if (val < 35) return "#ea580c";
  if (val < 50) return "#eab308";
  return "#22c55e";
}

function getSPIColor(val?: number | null): string {
  if (val == null || isNaN(val)) return "#94a3b8";
  if (val <= -2.0) return "#7f1d1d"; // Extremely Dry
  if (val <= -1.5) return "#dc2626"; // Severely Dry
  if (val <= -1.0) return "#ea580c"; // Moderately Dry
  if (val <= -0.5) return "#eab308"; // Abnormally Dry
  if (val < 1.0) return "#cbd5e1";   // Near Normal
  if (val < 2.0) return "#38bdf8";   // Moderately Wet
  return "#1d4ed8";                  // Extremely Wet
}

function getMetricColor(p: any, metric: MetricName): string {
  switch (metric) {
    case "cdi":
    case "cdi_class":
      return getCDIColor(p.CDI_class || p.class, p.CDI);
    case "ndvi":
      return getNDVIColor(p.NDVI);
    case "evi":
      return getNDVIColor(p.EVI);
    case "vci":
      return getVCIColor(p.VCI);
    case "vhi":
      return getVCIColor(p.VHI);
    case "spi1":
      return getSPIColor(p.SPI1 ?? p.spi1);
    case "spi3":
      return getSPIColor(p.SPI3 ?? p.spi3);
    case "spi6":
      return getSPIColor(p.SPI6 ?? p.spi6);
    case "spi12":
      return getSPIColor(p.SPI12 ?? p.spi12);
    case "rain":
      return p.Rain_mm && p.Rain_mm > 50 ? "#0284c7" : p.Rain_mm && p.Rain_mm > 20 ? "#38bdf8" : "#f59e0b";
    default:
      return getCDIColor(p.CDI_class, p.CDI);
  }
}

function MapAutoZoomer({
  geojson,
  tehsil,
  selectedVillageName,
}: {
  geojson: FeatureCollection | null;
  tehsil: string;
  selectedVillageName?: string;
}) {
  const map = useMap();
  useEffect(() => {
    if (!geojson?.features?.length) return;
    if (selectedVillageName) {
      const match = geojson.features.find((f) => {
        const v = f.properties?.village || f.properties?.VILLAGE || f.properties?.name || "";
        return v.toLowerCase() === selectedVillageName.toLowerCase();
      });
      if (match) {
        const layer = L.geoJSON(match as any);
        map.fitBounds(layer.getBounds(), { padding: [60, 60], maxZoom: 13 });
        return;
      }
    }
    if (tehsil && tehsil !== "All") {
      const filtered = geojson.features.filter((f) => {
        const t = f.properties?.tehsil || f.properties?.TEHSIL || "";
        return t.toLowerCase() === tehsil.toLowerCase();
      });
      if (filtered.length) {
        const layer = L.geoJSON({ type: "FeatureCollection", features: filtered } as any);
        map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 12 });
        return;
      }
    }
    map.setView(LATUR_CENTER, DEFAULT_ZOOM);
  }, [geojson, tehsil, selectedVillageName, map]);
  return null;
}

export default function LaturMap({
  metric = "cdi",
  tehsil = "All",
  selectedVillageName = "",
  currentPeriod = "2026-10",
  onSelectVillage,
  geeTileUrl,
  showGeeLayer = false,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [basemapId, setBasemapId] = useState<string>("google-terrain");
  const [villagesData, setVillagesData] = useState<FeatureCollection | null>(null);
  const [districtData, setDistrictData] = useState<FeatureCollection | null>(null);
  const [tehsilsData, setTehsilsData] = useState<FeatureCollection | null>(null);
  const [timeseriesCache, setTimeseriesCache] = useState<Record<string, any[]> | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredVillage, setHoveredVillage] = useState<string | null>(null);

  const basemap = useMemo(
    () => BASEMAPS.find((b) => b.id === basemapId) ?? BASEMAPS.find((b) => b.id === "google-terrain") ?? BASEMAPS[0],
    [basemapId]
  );

  // Load vector boundaries and timeseries cache
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch("/data/latur_villages_latest.geojson").then((r) => r.json()),
      fetch("/data/latur_district.geojson").then((r) => r.json()).catch(() => null),
      fetch("/data/latur_tehsils.geojson").then((r) => r.json()).catch(() => null),
      fetch("/data/village_timeseries.json").then((r) => r.json()).catch(() => null),
    ])
      .then(([vil, dist, teh, ts]) => {
        setVillagesData(vil);
        setDistrictData(dist);
        setTehsilsData(teh);
        if (ts) setTimeseriesCache(ts);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load map data:", err);
        setLoading(false);
      });
  }, []);

  // Helper to get active properties for currentPeriod
  const getActiveVillageProps = useCallback(
    (p: any) => {
      if (!p) return {};
      if (!timeseriesCache) return p;
      const vName = (p.village || p.VILLAGE || p.name || "").trim().toLowerCase();
      const tName = (p.tehsil || p.TEHSIL || "").trim().toLowerCase();
      const key = `${tName}::${vName}`;
      const pts = timeseriesCache[key];
      if (pts) {
        const match = pts.find((x: any) => x.p === currentPeriod);
        if (match) {
          return {
            ...p,
            ...match,
            period: currentPeriod,
            date: currentPeriod,
            CDI: match.cdi,
            CDI_class: match.cls,
            class: match.cls,
            NDVI: match.ndvi,
            VHI: match.vhi,
            VCI: match.vci,
            Rain_mm: match.rain,
            SPI1: match.spi1,
            SPI3: match.spi3,
            SPI6: match.spi6,
            SPI12: match.spi12,
          };
        }
      }
      return {
        ...p,
        period: currentPeriod,
        date: currentPeriod,
      };
    },
    [timeseriesCache, currentPeriod]
  );

  // Keep selected village in sync with currentPeriod
  useEffect(() => {
    if (!selectedVillageName || !onSelectVillage || !villagesData || !timeseriesCache) return;
    const match = villagesData.features.find((f) => {
      const v = f.properties?.village || f.properties?.VILLAGE || f.properties?.name || "";
      return v.toLowerCase() === selectedVillageName.toLowerCase();
    });
    if (match) {
      const active = getActiveVillageProps(match.properties);
      onSelectVillage(active as VillageProperties);
    }
  }, [currentPeriod, selectedVillageName, villagesData, timeseriesCache, getActiveVillageProps, onSelectVillage]);

  // Polygon styling
  const styleVillage = useCallback(
    (f?: Feature): PathOptions => {
      const rawProps = f?.properties || {};
      const p = getActiveVillageProps(rawProps);
      const vName = p.village || p.VILLAGE || p.name || "";
      const tName = p.tehsil || p.TEHSIL || "";
      const isSelected = selectedVillageName && vName.toLowerCase() === selectedVillageName.toLowerCase();
      const isHovered = hoveredVillage && vName.toLowerCase() === hoveredVillage.toLowerCase();

      // Check tehsil filter
      const matchesTehsil = tehsil === "All" || tName.toLowerCase() === tehsil.toLowerCase();

      const fillColor = getMetricColor(p, metric);

      return {
        fillColor,
        fillOpacity: isSelected ? 0.95 : isHovered ? 0.9 : matchesTehsil ? 0.75 : 0.15,
        color: isSelected ? "#f59e0b" : isHovered ? "#ffffff" : matchesTehsil ? "#1e293b" : "#334155",
        weight: isSelected ? 3 : isHovered ? 2 : 0.6,
        opacity: matchesTehsil ? 0.8 : 0.2,
      };
    },
    [metric, tehsil, selectedVillageName, hoveredVillage, getActiveVillageProps]
  );

  const onEachVillage = useCallback(
    (f: Feature, layer: Layer) => {
      const rawProps = f.properties || {};
      const p = getActiveVillageProps(rawProps);
      const vName = p.village || p.VILLAGE || p.name || "Village";
      const tName = p.tehsil || p.TEHSIL || "Tehsil";
      const cdi = p.CDI != null ? Number(p.CDI).toFixed(3) : "—";
      const cdiClass = p.CDI_class || p.class || "None";
      const ndvi = p.NDVI != null ? Number(p.NDVI).toFixed(3) : "—";
      const rain = p.Rain_mm != null ? `${Number(p.Rain_mm).toFixed(1)} mm` : "—";

      // Micro-tooltip styled for light theme. Values are escaped so a
      // malicious feature property (e.g. uploaded via /upload/aoi) cannot
      // inject HTML/JS through bindTooltip.
      const esc = (s: unknown) => {
        const str = s == null ? "" : String(s);
        return str
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      };
      layer.bindTooltip(
        `<div class="font-sans text-xs">
          <div class="font-extrabold text-slate-900 text-sm leading-tight">${esc(vName)}</div>
          <div class="text-[11px] text-slate-600 font-medium">${esc(tName)} Tehsil · <span class="font-mono font-bold text-amber-700">CDI: ${esc(cdi)} (${esc(cdiClass)})</span></div>
          <div class="text-[10px] text-slate-500">NDVI: <span class="font-mono font-bold text-emerald-700">${esc(ndvi)}</span> · Rain: <span class="font-mono font-bold text-blue-700">${esc(rain)}</span></div>
        </div>`,
        { sticky: true, className: "custom-leaflet-tooltip" }
      );

      layer.on({
        mouseover: () => setHoveredVillage(vName),
        mouseout: () => setHoveredVillage(null),
        click: () => {
          if (onSelectVillage) {
            onSelectVillage(p as VillageProperties);
          }
        },
      });
    },
    [onSelectVillage, getActiveVillageProps]
  );

  return (
    <div ref={rootRef} className="relative h-full w-full overflow-hidden bg-slate-100">
      {loading && (
        <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/80 backdrop-blur-sm">
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-amber-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-semibold text-slate-700">Rendering 954 Village Polygons...</span>
          </div>
        </div>
      )}

      <MapContainer
        center={LATUR_CENTER}
        zoom={DEFAULT_ZOOM}
        minZoom={8}
        maxZoom={15}
        zoomControl={false}
        scrollWheelZoom
        className="h-full w-full"
      >
        <TileLayer
          key={basemap.id}
          url={basemap.url}
          attribution={basemap.attribution}
          maxZoom={basemap.maxZoom ?? 19}
        />

        {/* Optional Live GEE Satellite Raster Layer */}
        {showGeeLayer && geeTileUrl && (
          <TileLayer
            key={geeTileUrl}
            url={geeTileUrl}
            opacity={0.7}
            attribution="Google Earth Engine Sentinel-2"
          />
        )}

        {/* Village Polygons Choropleth */}
        {villagesData && (
          <GeoJSON
            key={`villages-${metric}-${tehsil}-${currentPeriod}-${selectedVillageName}`}
            data={villagesData}
            style={styleVillage}
            onEachFeature={onEachVillage}
          />
        )}

        {/* Tehsil Outer Outlines */}
        {tehsilsData && (
          <GeoJSON
            key="tehsils-overlay"
            data={tehsilsData}
            style={() => ({
              fillColor: "transparent",
              color: "#b45309",
              weight: 1.8,
              dashArray: "4 4",
              opacity: 0.8,
            })}
          />
        )}

        {/* District Boundary */}
        {districtData && (
          <GeoJSON
            key="district-boundary"
            data={districtData}
            style={() => ({
              fillColor: "transparent",
              color: "#0f172a",
              weight: 2.5,
              opacity: 0.9,
            })}
          />
        )}

        <ZoomControl position="topright" />
        <ScaleControl position="bottomleft" imperial={false} />
        <MapAutoZoomer geojson={villagesData} tehsil={tehsil} selectedVillageName={selectedVillageName} />
      </MapContainer>

      {/* Floating Basemap Selector */}
      <div className="absolute top-4 left-4 z-[900]">
        <BasemapSwitcher value={basemapId} onChange={setBasemapId} />
      </div>

      {/* Floating Bottom Legend — White Theme with Gold Accents */}
      <div className="absolute bottom-6 left-4 z-[900] bg-white/95 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-200 shadow-md max-w-md text-slate-800">
        <div className="text-[11px] font-bold text-slate-700 mb-1 flex items-center justify-between">
          <span className="uppercase tracking-wider">
            {metric.startsWith("spi") ? `WMO ${metric.toUpperCase()} Rainfall Anomaly Scale` : metric === "cdi" ? "CDI Severity Scale" : `${metric.toUpperCase()} Scale`}
          </span>
          <span className="text-[10px] text-amber-700 font-mono font-bold">Latur Multi-Scale</span>
        </div>
        {metric.startsWith("spi") ? (
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#7f1d1d" }} /> &le; -2.0 Extr. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#dc2626" }} /> -1.5 Sev. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#ea580c" }} /> -1.0 Mod. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#cbd5e1" }} /> &plusmn;1.0 Normal</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#38bdf8" }} /> &ge; 1.0 Wet</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#1d4ed8" }} /> &ge; 2.0 Extr. Wet</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#22c55e" }} /> None</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#eab308" }} /> D0</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#f59e0b" }} /> D1</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#ea580c" }} /> D2</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#dc2626" }} /> D3</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#7f1d1d" }} /> D4</span>
          </div>
        )}
      </div>
    </div>
  );
}
