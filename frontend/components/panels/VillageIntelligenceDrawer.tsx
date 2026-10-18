"use client";

import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from "recharts";

export interface VillageProperties {
  id?: number;
  village_id?: number;
  village?: string;
  VILLAGE?: string;
  name?: string;
  tehsil?: string;
  TEHSIL?: string;
  AREA_SQKM?: number;
  date?: string;
  period?: string;
  CDI?: number | null;
  CDI_class?: string;
  class?: string;
  drought_month?: boolean;
  drought_severity?: string;
  NDVI?: number | null;
  EVI?: number | null;
  VCI?: number | null;
  VHI?: number | null;
  PCI?: number | null;
  SPI1?: number | null;
  SPI3?: number | null;
  SPI6?: number | null;
  SPI12?: number | null;
  Rain_mm?: number | null;
  baseline_ndvi?: number | null;
  baseline_vci?: number | null;
  baseline_spi3?: number | null;
  composite_anomaly?: number | null;
  component_contributions?: Record<string, number>;
  composite_formula_version?: string;
}

interface Props {
  village: VillageProperties | null;
  onClose: () => void;
}

interface TimeseriesPoint {
  p: string; // YYYY-MM
  cdi: number | null;
  cls: string;
  rain: number | null;
  ndvi: number | null;
  vhi: number | null;
  vci: number | null;
  spi1?: number | null;
  spi3: number | null;
  spi6?: number | null;
  spi12?: number | null;
}

const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string; label: string }> = {
  None: { bg: "bg-emerald-50", text: "text-emerald-800", border: "border-emerald-200", label: "Normal (No Drought)" },
  D0: { bg: "bg-yellow-50", text: "text-yellow-800", border: "border-yellow-200", label: "D0 · Abnormally Dry" },
  D1: { bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-200", label: "D1 · Moderate Drought" },
  D2: { bg: "bg-orange-50", text: "text-orange-800", border: "border-orange-200", label: "D2 · Severe Drought" },
  D3: { bg: "bg-red-50", text: "text-red-800", border: "border-red-200", label: "D3 · Extreme Drought" },
  D4: { bg: "bg-rose-100", text: "text-rose-900", border: "border-rose-300", label: "D4 · Exceptional Drought" },
  ND: { bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200", label: "Pending Optical Pass" },
};

function getAdvisory(cls?: string): string {
  switch (cls) {
    case "D4":
      return "Emergency declaration tier. Enforce critical drinking water rationing, mobilize emergency tanker supplies, and prepare cattle fodder camps. Complete ban on industrial surface withdrawals.";
    case "D3":
      return "Extreme stress. Initiate micro-irrigation protocols, restrict surface canal diversions for non-essential use, and deploy localized groundwater recharge surveillance.";
    case "D2":
      return "Severe drought stress. Prioritize protective sprinkler irrigation for standing Kharif/Rabi crops. Mulching and moisture conservation techniques strongly advised.";
    case "D1":
      return "Moderate moisture deficit. Soil moisture below historical average. Monitor reservoir levels and advise farmers against high-water-consumption cash crops.";
    case "D0":
      return "Early moisture deficit warning. Ground condition abnormally dry. Prepare farm pond rainwater storage and monitor meteorological precipitation trends.";
    default:
      return "Vegetation health and precipitation indicators within normal climatological baselines. Standard agricultural operations recommended.";
  }
}

export function VillageIntelligenceDrawer({ village, onClose }: Props) {
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [loadingTs, setLoadingTs] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "history" | "breakdown">("overview");

  const villageName = village?.village || village?.VILLAGE || village?.name || "Unknown Village";
  const tehsilName = village?.tehsil || village?.TEHSIL || "Unknown Tehsil";
  const cdiClass = village?.CDI_class || village?.class || "None";
  const severityStyle = SEVERITY_COLORS[cdiClass] || SEVERITY_COLORS.None;

  // Fetch full village 10-year timeseries
  useEffect(() => {
    if (!village) return;
    setLoadingTs(true);
    fetch(`/api/v1/timeseries?tehsil=${encodeURIComponent(tehsilName)}&village=${encodeURIComponent(villageName)}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data: TimeseriesPoint[]) => {
        setTimeseries(data || []);
        setLoadingTs(false);
      })
      .catch((err) => {
        console.error("Failed to fetch village timeseries:", err);
        setTimeseries([]);
        setLoadingTs(false);
      });
  }, [village, villageName, tehsilName]);

  if (!village) return null;

  return (
    <aside
      className="fixed inset-y-0 right-0 z-[1100] w-full max-w-lg bg-white/95 backdrop-blur-xl
                 border-l border-slate-200 shadow-2xl flex flex-col transition-transform duration-300 ease-in-out text-slate-900"
    >
      {/* Top Header */}
      <div className="p-5 border-b border-slate-200 flex items-start justify-between bg-slate-50">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-wider font-bold text-amber-700">
              {tehsilName} Tehsil
            </span>
            <span className="text-slate-300">·</span>
            <span className="text-xs text-slate-500 font-medium">
              {village.AREA_SQKM ? `${village.AREA_SQKM.toFixed(2)} km²` : "Latur District"}
            </span>
          </div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">{villageName}</h2>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
          title="Close Drawer"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Severity Status Banner */}
      <div className={`mx-5 mt-4 p-4 rounded-xl border ${severityStyle.border} ${severityStyle.bg} flex items-center justify-between shadow-sm`}>
        <div>
          <div className="text-[11px] uppercase tracking-wider font-bold opacity-75">
            Drought Condition ({village.period || "Current"})
          </div>
          <div className={`text-base font-extrabold ${severityStyle.text}`}>
            {severityStyle.label}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500 uppercase font-semibold">CDI Score</div>
          <div className="text-2xl font-black font-mono text-slate-900">
            {village.CDI != null ? village.CDI.toFixed(3) : "—"}
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-200 px-5 mt-4 gap-4 text-xs font-bold text-slate-500">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-2.5 transition-colors border-b-2 ${
            activeTab === "overview" ? "border-amber-600 text-amber-900" : "border-transparent hover:text-slate-800"
          }`}
        >
          Indices & Metrics
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`pb-2.5 transition-colors border-b-2 ${
            activeTab === "history" ? "border-amber-600 text-amber-900" : "border-transparent hover:text-slate-800"
          }`}
        >
          10-Year Trajectory
        </button>
        <button
          onClick={() => setActiveTab("breakdown")}
          className={`pb-2.5 transition-colors border-b-2 ${
            activeTab === "breakdown" ? "border-amber-600 text-amber-900" : "border-transparent hover:text-slate-800"
          }`}
        >
          Advisory & Weights
        </button>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {activeTab === "overview" && (
          <>
            {/* Multi-Scale SPI Suite (CHIRPS) */}
            <div>
              <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Multi-Scale SPI (CHIRPS Precipitation)</span>
                <span className="text-[10px] font-mono text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded border border-cyan-200">
                  Continuous 2016–2026
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex justify-between">
                    <span className="font-semibold text-slate-700">SPI-1</span>
                    <span className="text-[10px] text-slate-400">Monthly</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.SPI1 != null ? village.SPI1.toFixed(2) : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Immediate Moisture</div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex justify-between">
                    <span className="font-semibold text-slate-700">SPI-3</span>
                    <span className="text-[10px] text-slate-400">Seasonal</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.SPI3 != null ? village.SPI3.toFixed(2) : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Baseline: {village.baseline_spi3 != null ? village.baseline_spi3.toFixed(2) : "0.43"}
                  </div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex justify-between">
                    <span className="font-semibold text-slate-700">SPI-6</span>
                    <span className="text-[10px] text-slate-400">Biannual</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.SPI6 != null ? village.SPI6.toFixed(2) : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Medium-term Hydrology</div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex justify-between">
                    <span className="font-semibold text-slate-700">SPI-12</span>
                    <span className="text-[10px] text-slate-400">Annual</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.SPI12 != null ? village.SPI12.toFixed(2) : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Deep Aquifer/Storage</div>
                </div>
              </div>
            </div>

            {/* Earth Observation Spectral Indices (Sentinel-2) */}
            <div>
              <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Vegetation & Stress Indices</span>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Sentinel-2 L2A
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex items-center justify-between">
                    <span className="font-semibold text-slate-700">NDVI</span>
                    <span className="text-[10px] text-slate-400">-1 to +1</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.NDVI != null ? village.NDVI.toFixed(3) : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Baseline: {village.baseline_ndvi != null ? village.baseline_ndvi.toFixed(3) : "—"}
                    {village.NDVI != null && village.baseline_ndvi != null && (
                      <span className={village.NDVI < village.baseline_ndvi ? " text-rose-600 ml-1 font-bold" : " text-emerald-600 ml-1 font-bold"}>
                        ({(village.NDVI - village.baseline_ndvi > 0 ? "+" : "") + (village.NDVI - village.baseline_ndvi).toFixed(3)})
                      </span>
                    )}
                  </div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex items-center justify-between">
                    <span className="font-semibold text-slate-700">VCI</span>
                    <span className="text-[10px] text-slate-400">0 to 100%</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.VCI != null ? `${village.VCI.toFixed(1)}%` : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Baseline: {village.baseline_vci != null ? `${village.baseline_vci.toFixed(1)}%` : "—"}
                  </div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex items-center justify-between">
                    <span className="font-semibold text-slate-700">VHI (Stress)</span>
                    <span className="text-[10px] text-slate-400">0 to 100</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.VHI != null ? village.VHI.toFixed(1) : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Vegetation Health Index</div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="text-[11px] text-slate-500 flex items-center justify-between">
                    <span className="font-semibold text-slate-700">Monthly Rain</span>
                    <span className="text-[10px] text-slate-400">CHIRPS</span>
                  </div>
                  <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                    {village.Rain_mm != null ? `${village.Rain_mm.toFixed(1)} mm` : "—"}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Precipitation Total</div>
                </div>
              </div>
            </div>

            {/* Anomaly Gauge */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-bold text-slate-800">Composite Drought Anomaly</span>
                <span className="text-xs font-mono font-bold text-amber-700">
                  {village.composite_anomaly != null ? `${village.composite_anomaly.toFixed(2)} σ` : "—"}
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    (village.CDI || 0) > 0.5 ? "bg-gradient-to-r from-amber-500 to-rose-600" : "bg-emerald-500"
                  }`}
                  style={{ width: `${Math.min(Math.max((village.CDI || 0) * 100, 5), 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                <span>0.0 (Normal)</span>
                <span>0.5 (Severe)</span>
                <span>1.0 (Critical)</span>
              </div>
            </div>
          </>
        )}

        {activeTab === "history" && (
          <div className="space-y-4">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-bold text-slate-900 mb-1">
                Historical CDI & Rainfall Trend (2016–2026)
              </div>
              <div className="text-[11px] text-slate-500 mb-4">
                Full 10-year monthly trajectory tracking drought intensity and rainfall anomalies.
              </div>

              {loadingTs ? (
                <div className="h-64 flex items-center justify-center text-xs text-slate-500">
                  Loading 10-year trajectory data...
                </div>
              ) : timeseries.length === 0 ? (
                <div className="h-64 flex items-center justify-center text-xs text-slate-500">
                  No historical records found for this village.
                </div>
              ) : (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={timeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="p"
                        tick={{ fill: "#64748b", fontSize: 10 }}
                        tickFormatter={(v) => v.slice(0, 4)}
                        interval={12}
                      />
                      <YAxis
                        yAxisId="cdi"
                        domain={[0, 1]}
                        tick={{ fill: "#b45309", fontSize: 10 }}
                        tickFormatter={(v) => v.toFixed(1)}
                      />
                      <YAxis
                        yAxisId="rain"
                        orientation="right"
                        domain={[0, "auto"]}
                        tick={{ fill: "#0284c7", fontSize: 10 }}
                        tickFormatter={(v) => `${v}`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          borderColor: "#cbd5e1",
                          borderRadius: "0.5rem",
                          fontSize: "11px",
                          boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                      <ReferenceLine yAxisId="cdi" y={0.5} stroke="#ef4444" strokeDasharray="3 3" label="Severe" />
                      <Bar yAxisId="rain" dataKey="rain" name="Rain (mm)" fill="#0284c7" opacity={0.35} />
                      <Line
                        yAxisId="cdi"
                        type="monotone"
                        dataKey="cdi"
                        name="CDI Score"
                        stroke="#b45309"
                        strokeWidth={2}
                        dot={false}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "breakdown" && (
          <div className="space-y-4">
            {/* Component Contributions */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-bold text-slate-900 mb-1">
                Composite Drought Index Weights
              </div>
              <div className="text-[11px] text-slate-500 mb-4">
                Formula version: {village.composite_formula_version || "cdi-v2026.10"}
              </div>

              <div className="space-y-3">
                {[
                  { name: "Precipitation Condition (PCI · CHIRPS)", weight: 0.50, desc: "Primary moisture departure indicator (GoI Manual 2016 Trigger 1)" },
                  { name: "Vegetation Condition (VCI · Sentinel-2)", weight: 0.25, desc: "Canopy photosynthetic stress scaled against 10-year extremes" },
                  { name: "Thermal Condition (TCI · LST)", weight: 0.25, desc: "Evaporative surface thermal deficit" },
                ].map((item) => (
                  <div key={item.name}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-slate-800 font-bold">{item.name}</span>
                      <span className="font-mono text-amber-800 font-extrabold">{Math.round(item.weight * 100)}%</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="h-full bg-amber-600 rounded-full"
                        style={{ width: `${item.weight * 100}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{item.desc}</div>
                  </div>
                ))}
              </div>

              {/* Satellite Availability Note */}
              <div className="mt-4 p-3 bg-amber-50/70 rounded-lg border border-amber-200 text-[11px] text-slate-700">
                <div className="font-bold text-amber-900 mb-0.5 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-600" />
                  Sentinel-2 Image Availability Audit
                </div>
                <p className="text-[10px] text-slate-600 leading-relaxed">
                  Based on <span className="font-mono font-semibold">drought_image_availability.xlsx</span>, 83 optical passes (2016–2026) have high-quality cloud-free Sentinel-2 data. During monsoon cloud peaks, the system activates <span className="font-mono font-semibold text-cyan-800">chirps_only</span> mode to prevent artificial cloud shadow distortion.
                </p>
              </div>
            </div>

            {/* Field Advisory */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-bold text-slate-900 mb-2 flex items-center gap-2">
                <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Agronomic Management Advisory
              </div>
              <p className="text-xs text-slate-700 leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
                {getAdvisory(cdiClass)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Drawer Footer */}
      <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
        <span>Data: Sentinel-2 & CHIRPS (GEE)</span>
        <span className="font-mono text-[11px] font-bold text-slate-700">Village ID #{village.id || village.village_id}</span>
      </div>
    </aside>
  );
}
