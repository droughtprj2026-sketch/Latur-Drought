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
import { D_CODES, D_COLORS, codeForCDI, classifyValue, colorForValue } from "@/lib/classify";
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
  timeseriesCache?: Record<string, any[]> | null;
}

const LATUR_CENTER: [number, number] = [18.4088, 76.5604];
const DEFAULT_ZOOM = 9;

function getMetricColor(p: any, metric: MetricName): string {
  if (!p) return "#94a3b8";
  let val: number | null | undefined = undefined;

  switch (metric) {
    case "cdi":
    case "cdi_class":
      val = p.CDI ?? p.cdi ?? (p.value != null ? Number(p.value) : undefined);
      if (val == null && (p.CDI_class || p.class || p.cls)) {
        const c = String(p.CDI_class || p.class || p.cls);
        const idx = D_CODES.indexOf(c as any);
        if (idx >= 0) return D_COLORS[idx];
      }
      break;
    case "ndvi":
      val = p.NDVI ?? p.ndvi ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "evi":
      val = p.EVI ?? p.evi ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "vci":
      val = p.VCI ?? p.vci ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "vhi":
      val = p.VHI ?? p.vhi ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "spi1":
      val = p.SPI1 ?? p.spi1 ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "spi3":
      val = p.SPI3 ?? p.spi3 ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "spi6":
      val = p.SPI6 ?? p.spi6 ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "spi12":
      val = p.SPI12 ?? p.spi12 ?? (p.value != null ? Number(p.value) : undefined);
      break;
    case "rain":
      val = p.Rain_mm ?? p.rain ?? p.pci ?? (p.value != null ? Number(p.value) : undefined);
      break;
    default:
      val = p.CDI ?? p.cdi ?? (p.value != null ? Number(p.value) : undefined);
  }

  return colorForValue(val, metric);
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
  timeseriesCache,
}: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [basemapId, setBasemapId] = useState<string>("google-terrain");
  const [villagesData, setVillagesData] = useState<FeatureCollection | null>(null);
  const [districtData, setDistrictData] = useState<FeatureCollection | null>(null);
  const [tehsilsData, setTehsilsData] = useState<FeatureCollection | null>(null);
  const [indexValues, setIndexValues] = useState<Record<string, any>>({});
  const [indexRevision, setIndexRevision] = useState(0);
  const [internalTs, setInternalTs] = useState<Record<string, any[]> | null>(null);
  const [loading, setLoading] = useState(true);
  const [indexLoading, setIndexLoading] = useState(false);
  const [hoveredVillage, setHoveredVillage] = useState<string | null>(null);
  const geoJsonRef = useRef<L.GeoJSON | null>(null);

  const basemap = useMemo(
    () => BASEMAPS.find((b) => b.id === basemapId) ?? BASEMAPS.find((b) => b.id === "google-terrain") ?? BASEMAPS[0],
    [basemapId]
  );

  // Load static vector boundaries once
  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch("/data/latur_villages_latest.geojson")
        .then((r) => r.json()).catch(() => null),
      fetch("/data/latur_district.geojson")
        .then((r) => r.json()).catch(() => null),
      fetch("/data/latur_tehsils.geojson")
        .then((r) => r.json()).catch(() => null),
    ])
      .then(([vil, dist, teh]) => {
        if (vil) setVillagesData(vil);
        if (dist) setDistrictData(dist);
        if (teh) setTehsilsData(teh);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load map data:", err);
        setLoading(false);
      });
  }, []);

  // Pre-load full village timeseries for instant 60fps timeline scrubbing
  useEffect(() => {
    if (timeseriesCache) return;
    fetch("/data/village_timeseries.json")
      .then((r) => r.json())
      .then((d) => setInternalTs(d))
      .catch(() => null);
  }, [timeseriesCache]);

  const activeTs = timeseriesCache || internalTs;

  // Load index-specific values from API as secondary verification
  useEffect(() => {
    if (!currentPeriod) return;
    const [y, m] = currentPeriod.split("-");
    const year = Number(y);
    const month = Number(m);
    if (!year || !month) return;

    setIndexLoading(true);
    fetch(`/api/v1/indices/${metric}/${year}/${month}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((gj: FeatureCollection) => {
        const lookup: Record<string, any> = {};
        gj.features?.forEach((f: any) => {
          const p = f.properties || {};
          const t = (p.tehsil || p.TEHSIL || "").trim().toLowerCase();
          const v = (p.village || p.VILLAGE || p.name || "").trim().toLowerCase();
          const key = `${t}::${v}`;
          lookup[key] = {
            value: p.value,
            class: p.class,
            cdi: p.cdi,
            spi1: p.spi1,
            spi3: p.spi3,
            spi6: p.spi6,
            spi12: p.spi12,
            ndvi: p.ndvi,
            evi: p.evi,
            vci: p.vci,
            vhi: p.vhi,
            pci: p.pci ?? null,
            rain: p.rain,
            period: p.period,
          };
        });
        setIndexValues(lookup);
        setIndexRevision((prev) => prev + 1);
        setIndexLoading(false);
      })
      .catch((err) => {
        setIndexLoading(false);
      });
  }, [metric, currentPeriod]);

  // Synchronously merge index values with village properties (Instant during scrubbing)
  const getActiveVillageProps = useCallback(
    (p: any) => {
      if (!p) return {};
      const vName = (p.village || p.VILLAGE || p.name || "").trim().toLowerCase();
      const tName = (p.tehsil || p.TEHSIL || "").trim().toLowerCase();
      const key = `${tName}::${vName}`;

      // 1. Fast in-memory timeseries lookup (instantaneous 60fps animation)
      if (activeTs && activeTs[key]) {
        const pts = activeTs[key];
        const match = Array.isArray(pts) ? pts.find((x: any) => (x.p || x.date) === currentPeriod) : null;
        if (match) {
          let metricVal: number | null | undefined = undefined;
          switch (metric) {
            case "cdi":
            case "cdi_class":
              metricVal = match.cdi;
              break;
            case "ndvi":
              metricVal = match.ndvi;
              break;
            case "evi":
              metricVal = match.evi ?? match.ndvi;
              break;
            case "vci":
              metricVal = match.vci;
              break;
            case "vhi":
              metricVal = match.vhi;
              break;
            case "spi1":
              metricVal = match.spi1;
              break;
            case "spi3":
              metricVal = match.spi3;
              break;
            case "spi6":
              metricVal = match.spi6;
              break;
            case "spi12":
              metricVal = match.spi12;
              break;
            case "rain":
              metricVal = match.rain;
              break;
            default:
              metricVal = match.cdi;
          }

          return {
            ...p,
            ...match,
            value: metricVal,
            CDI: match.cdi,
            cdi: match.cdi,
            CDI_class: match.cls || "None",
            class: match.cls || "None",
            cls: match.cls || "None",
            NDVI: match.ndvi,
            ndvi: match.ndvi,
            EVI: match.evi ?? match.ndvi,
            evi: match.evi ?? match.ndvi,
            VCI: match.vci,
            vci: match.vci,
            VHI: match.vhi,
            vhi: match.vhi,
            SPI1: match.spi1,
            spi1: match.spi1,
            SPI3: match.spi3,
            spi3: match.spi3,
            SPI6: match.spi6,
            spi6: match.spi6,
            SPI12: match.spi12,
            spi12: match.spi12,
            Rain_mm: match.rain,
            rain: match.rain,
            period: currentPeriod,
            date: currentPeriod,
          };
        } else {
          // No satellite / rainfall observation available for this specific period (e.g. cloudy month / missing year)
          return {
            ...p,
            value: null,
            CDI: null,
            cdi: null,
            CDI_class: "ND",
            class: "ND",
            cls: "ND",
            NDVI: null,
            ndvi: null,
            EVI: null,
            evi: null,
            VCI: null,
            vci: null,
            VHI: null,
            vhi: null,
            SPI1: null,
            spi1: null,
            SPI3: null,
            spi3: null,
            SPI6: null,
            spi6: null,
            SPI12: null,
            spi12: null,
            Rain_mm: null,
            rain: null,
            period: currentPeriod,
            date: currentPeriod,
          };
        }
      }

      // 2. Fallback to API index values lookup
      const idx = indexValues[key];
      if (idx) {
        return {
          ...p,
          ...idx,
          CDI: idx.cdi ?? p.CDI,
          cdi: idx.cdi ?? p.cdi,
          CDI_class: idx.class ?? idx.cls ?? p.CDI_class,
          class: idx.class ?? idx.cls ?? p.class,
          NDVI: idx.ndvi ?? p.NDVI,
          ndvi: idx.ndvi ?? p.ndvi,
          EVI: idx.evi ?? p.EVI,
          evi: idx.evi ?? p.evi,
          VCI: idx.vci ?? p.VCI,
          vci: idx.vci ?? p.vci,
          VHI: idx.vhi ?? p.VHI,
          vhi: idx.vhi ?? p.vhi,
          SPI1: idx.spi1 ?? p.SPI1,
          spi1: idx.spi1 ?? p.spi1,
          SPI3: idx.spi3 ?? p.SPI3,
          spi3: idx.spi3 ?? p.spi3,
          SPI6: idx.spi6 ?? p.SPI6,
          spi6: idx.spi6 ?? p.spi6,
          SPI12: idx.spi12 ?? p.SPI12,
          spi12: idx.spi12 ?? p.spi12,
          Rain_mm: idx.rain ?? p.Rain_mm,
          rain: idx.rain ?? p.rain,
          value: idx.value,
          period: currentPeriod,
          date: currentPeriod,
        };
      }
      return p;
    },
    [activeTs, indexValues, currentPeriod, metric]
  );

  // Keep selected village in sync
  useEffect(() => {
    if (!selectedVillageName || !onSelectVillage || !villagesData) return;
    const match = villagesData.features.find((f) => {
      const v = f.properties?.village || f.properties?.VILLAGE || f.properties?.name || "";
      return v.toLowerCase() === selectedVillageName.toLowerCase();
    });
    if (match) {
      const active = getActiveVillageProps(match.properties);
      onSelectVillage(active as VillageProperties);
    }
  }, [selectedVillageName, villagesData, getActiveVillageProps, onSelectVillage]);

  // Polygon styling
  const styleVillage = useCallback(
    (f?: Feature): PathOptions => {
      const rawProps = f?.properties || {};
      const p = getActiveVillageProps(rawProps);
      const vName = p.village || p.VILLAGE || p.name || "";
      const tName = p.tehsil || p.TEHSIL || "";
      const isSelected = selectedVillageName && vName.toLowerCase() === selectedVillageName.toLowerCase();
      const isHovered = hoveredVillage && vName.toLowerCase() === hoveredVillage.toLowerCase();

      const matchesTehsil = tehsil === "All" || tName.toLowerCase() === tehsil.toLowerCase();
      const fillColor = getMetricColor(p, metric);

      return {
        fillColor,
        fillOpacity: isSelected ? 0.95 : isHovered ? 0.9 : matchesTehsil ? 0.78 : 0.15,
        color: isSelected ? "#f59e0b" : isHovered ? "#ffffff" : matchesTehsil ? "#1e293b" : "#334155",
        weight: isSelected ? 3 : isHovered ? 2 : 0.6,
        opacity: matchesTehsil ? 0.8 : 0.2,
      };
    },
    [metric, tehsil, selectedVillageName, hoveredVillage, getActiveVillageProps]
  );

  // Instantly re-style all 954 village polygons on every scrub frame without DOM destruction
  useEffect(() => {
    if (geoJsonRef.current) {
      geoJsonRef.current.setStyle(styleVillage);
    }
  }, [styleVillage]);

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
      const spi3 = p.SPI3 != null ? Number(p.SPI3).toFixed(2) : "—";
      const vci = p.VCI != null ? `${Number(p.VCI).toFixed(1)}%` : "—";

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
          <div class="text-[10px] text-slate-500 mt-0.5">
            <span class="mr-2">NDVI: <b class="text-emerald-700">${esc(ndvi)}</b></span>
            <span class="mr-2">VCI: <b class="text-amber-700">${esc(vci)}</b></span>
            <span class="mr-2">SPI-3: <b class="text-blue-700">${esc(spi3)}</b></span>
            <span>Rain: <b class="text-blue-700">${esc(rain)}</b></span>
          </div>
        </div>`,
        { sticky: true, className: "custom-leaflet-tooltip" }
      );

      layer.on({
        mouseover: () => setHoveredVillage(vName),
        mouseout: () => setHoveredVillage(null),
        click: (e: LeafletMouseEvent) => {
          if (onSelectVillage) {
            onSelectVillage(p as VillageProperties);
          }
          const map = (e.target as any)._map;
          if (map) {
            map.fitBounds((layer as any).getBounds(), { padding: [60, 60], maxZoom: 13 });
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
            <span className="text-xs font-semibold text-slate-700">Loading map data...</span>
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

        {showGeeLayer && geeTileUrl && (
          <TileLayer
            key={geeTileUrl}
            url={geeTileUrl}
            opacity={0.7}
            attribution="Google Earth Engine Sentinel-2"
          />
        )}

        {/* Village Polygons Choropleth — Dynamic key ensures instant repainting on any frame/metric change */}
        {villagesData && (
          <GeoJSON
            ref={geoJsonRef as any}
            key={`villages-${metric}-${currentPeriod}-${tehsil}-${selectedVillageName}-rev${indexRevision}-${activeTs ? "cached" : "api"}`}
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

      {/* Floating Bottom Legend — Tailored specifically to the active metric */}
      <div className="absolute bottom-6 left-4 z-[900] bg-white/95 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-200 shadow-md max-w-lg text-slate-800">
        <div className="text-[11px] font-bold text-slate-700 mb-1.5 flex items-center justify-between">
          <span className="uppercase tracking-wider">
            {metric.startsWith("spi")
              ? `WMO ${metric.toUpperCase()} Rainfall Anomaly Scale`
              : metric === "cdi"
              ? "CDI Multi-Index Drought Severity"
              : metric === "ndvi" || metric === "evi"
              ? `${metric.toUpperCase()} Vegetation Canopy Greenness Scale`
              : metric === "vci" || metric === "vhi"
              ? `${metric.toUpperCase()} Vegetation Health Condition (%)`
              : "Rainfall Volume (mm)"}
          </span>
          <span className="text-[10px] text-amber-700 font-mono font-bold">Latur Cadastral ({currentPeriod})</span>
        </div>

        {metric.startsWith("spi") ? (
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#7f1d1d" }} /> &le; -2.0 Extr. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#dc2626" }} /> -1.5 Sev. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#ea580c" }} /> -1.0 Mod. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#eab308" }} /> -0.5 Abnorm. Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#cbd5e1" }} /> &plusmn;1.0 Normal</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#38bdf8" }} /> &ge; 1.0 Wet</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#1d4ed8" }} /> &ge; 2.0 Extr. Wet</span>
          </div>
        ) : metric === "ndvi" || metric === "evi" ? (
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#854d0e" }} /> &lt; 0.15 Bare / Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#ca8a04" }} /> 0.15–0.25 Stressed</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#a3e635" }} /> 0.25–0.35 Moderate</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#4ade80" }} /> 0.35–0.45 Normal</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#15803d" }} /> &gt; 0.45 Lush Canopy</span>
          </div>
        ) : metric === "vci" || metric === "vhi" ? (
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#7f1d1d" }} /> &lt; 10 Extreme</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#dc2626" }} /> 10–20 Severe</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#ea580c" }} /> 20–35 Moderate</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#eab308" }} /> 35–50 Mild Dry</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#22c55e" }} /> &ge; 50 Normal / Good</span>
          </div>
        ) : metric === "rain" ? (
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#f59e0b" }} /> &lt; 20 mm Deficit</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#38bdf8" }} /> 20–50 mm Moderate</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#0284c7" }} /> &gt; 50 mm Adequate</span>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold text-slate-700">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#22c55e" }} /> &lt; 0.20 None</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#eab308" }} /> 0.20–0.35 D0</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#f59e0b" }} /> 0.35–0.50 D1</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#ea580c" }} /> 0.50–0.65 D2</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#dc2626" }} /> 0.65–0.80 D3</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded" style={{ background: "#7f1d1d" }} /> &ge; 0.80 D4</span>
          </div>
        )}
      </div>
    </div>
  );
}
