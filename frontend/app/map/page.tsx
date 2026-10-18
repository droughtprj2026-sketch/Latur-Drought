"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { MetricName } from "@/components/map/LaturMap";
import { VillageIntelligenceDrawer, type VillageProperties } from "@/components/panels/VillageIntelligenceDrawer";
import { MonthlyTimelineScrubber } from "@/components/map/MonthlyTimelineScrubber";

const LaturMap = dynamic(() => import("@/components/map/LaturMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-slate-50 text-slate-500 text-sm">
      <div className="flex flex-col items-center gap-2">
        <div className="w-8 h-8 border-2 border-amber-600 border-t-transparent rounded-full animate-spin" />
        <span className="font-semibold text-slate-700">Loading Latur Fullscreen GIS Map...</span>
      </div>
    </div>
  ),
});

const METRICS: { id: MetricName; label: string }[] = [
  { id: "cdi", label: "CDI Composite Severity" },
  { id: "spi1", label: "SPI-1 (1-Mo Meteorological)" },
  { id: "spi3", label: "SPI-3 (3-Mo Agricultural)" },
  { id: "spi6", label: "SPI-6 (6-Mo Seasonal)" },
  { id: "spi12", label: "SPI-12 (12-Mo Deep Hydrology)" },
  { id: "ndvi", label: "NDVI (Green Biomass)" },
  { id: "vhi", label: "VHI (Vegetation Health)" },
  { id: "vci", label: "VCI (Condition Index)" },
  { id: "rain", label: "Rainfall (CHIRPS mm)" },
];

const TEHSILS = [
  "All",
  "Ahmadpur",
  "Ausa",
  "Chakur",
  "Deoni",
  "Jalkot",
  "Latur",
  "Nilanga",
  "Renapur",
  "Shirur-Anantpal",
  "Udgir",
];

export default function FullscreenMapPage() {
  const [metric, setMetric] = useState<MetricName>("cdi");
  const [tehsil, setTehsil] = useState<string>("All");
  const [selectedVillage, setSelectedVillage] = useState<VillageProperties | null>(null);
  const [periods, setPeriods] = useState<string[]>([]);
  const [currentPeriod, setCurrentPeriod] = useState<string>("2026-10");
  const [showGeeLayer, setShowGeeLayer] = useState<boolean>(false);
  const [geeTileUrl] = useState<string>(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
  );

  useEffect(() => {
    fetch("/data/district_monthly.json")
      .then((r) => r.json())
      .then((d) => {
        const pList = (d.series || []).map((s: any) => s.date).filter(Boolean);
        if (pList.length > 0) setPeriods(pList);
      })
      .catch(() => null);
  }, []);

  return (
    <div className="relative h-[calc(100vh-57px)] w-full overflow-hidden bg-slate-50 text-slate-900">
      {/* Top Floating Control Bar — Crisp White with Gold Accents */}
      <div className="absolute top-4 left-4 z-[900] flex flex-wrap items-center gap-2 bg-white/95 backdrop-blur-md p-2 rounded-2xl border border-slate-200 shadow-md">
        <div className="flex items-center gap-1.5 px-2 text-xs font-bold text-amber-800">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span>GIS Explorer</span>
        </div>

        {/* Metric Selector */}
        <select
          value={metric}
          onChange={(e) => setMetric(e.target.value as MetricName)}
          className="bg-slate-50 text-xs font-bold text-slate-800 px-3 py-1.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
        >
          {METRICS.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>

        {/* Tehsil Selector */}
        <select
          value={tehsil}
          onChange={(e) => setTehsil(e.target.value)}
          className="bg-slate-50 text-xs font-bold text-slate-800 px-3 py-1.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
        >
          {TEHSILS.map((t) => (
            <option key={t} value={t}>
              {t === "All" ? "All Latur (10 Tehsils)" : `${t} Tehsil`}
            </option>
          ))}
        </select>

        {/* Live GEE Satellite Toggle */}
        <button
          onClick={() => setShowGeeLayer(!showGeeLayer)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shadow-xs ${
            showGeeLayer
              ? "bg-emerald-700 text-white ring-2 ring-emerald-300 shadow-sm"
              : "bg-slate-50 text-slate-700 border border-slate-200 hover:bg-slate-100"
          }`}
          title="Toggle High-Resolution Live Satellite Imagery Overlay"
        >
          <span className={`w-2 h-2 rounded-full ${showGeeLayer ? "bg-white animate-pulse" : "bg-emerald-500"}`} />
          <span>🛰️ Live Satellite</span>
        </button>

        {/* Current Period Badge */}
        <div className="px-3 py-1 bg-amber-50 border border-amber-200 rounded-xl text-xs font-mono font-bold text-amber-900">
          {currentPeriod}
        </div>
      </div>

      {/* Main Interactive Leaflet Map */}
      <LaturMap
        metric={metric}
        tehsil={tehsil}
        currentPeriod={currentPeriod}
        showGeeLayer={showGeeLayer}
        geeTileUrl={geeTileUrl}
        selectedVillageName={selectedVillage?.village || selectedVillage?.VILLAGE || selectedVillage?.name || ""}
        onSelectVillage={(props) => setSelectedVillage(props)}
      />

      {/* Bottom Timeline Scrubber */}
      {periods.length > 0 && (
        <div className="absolute bottom-5 left-4 right-4 z-[950] max-w-2xl mx-auto">
          <MonthlyTimelineScrubber
            periods={periods}
            currentPeriod={currentPeriod}
            onPeriodChange={setCurrentPeriod}
          />
        </div>
      )}

      {/* Village Intelligence Drawer */}
      <VillageIntelligenceDrawer
        village={selectedVillage}
        onClose={() => setSelectedVillage(null)}
      />
    </div>
  );
}
