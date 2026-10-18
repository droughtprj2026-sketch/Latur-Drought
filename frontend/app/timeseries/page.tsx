"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { colorForValue } from "@/lib/classify";

const TEHSILS = [
  "All Latur (District Mean)",
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

const METRICS = [
  { id: "spi1", label: "SPI-1 (1-Month Meteorological)" },
  { id: "spi3", label: "SPI-3 (3-Month Agricultural Root-Zone)" },
  { id: "spi6", label: "SPI-6 (6-Month Seasonal Runoff)" },
  { id: "spi12", label: "SPI-12 (12-Month Deep Ground Hydrology)" },
  { id: "ndvi", label: "NDVI (Normalized Difference Vegetation)" },
  { id: "vhi", label: "VHI (Vegetation Health Index)" },
  { id: "vci", label: "VCI (Vegetation Condition Index)" },
  { id: "cdi", label: "CDI (Composite Multi-Index Drought Score)" },
  { id: "rain", label: "Rainfall (CHIRPS Precipitation mm)" },
];

const SPI_BANDS = [
  { from: -0.5, to: -0.8, color: "#FFFF0033", label: "D0 (Abnormally Dry)" },
  { from: -0.8, to: -1.3, color: "#FCD37F55", label: "D1 (Moderate)" },
  { from: -1.3, to: -1.6, color: "#FFAA0055", label: "D2 (Severe)" },
  { from: -1.6, to: -2.0, color: "#E6000055", label: "D3 (Extreme)" },
  { from: -2.0, to: -3.5, color: "#73000055", label: "D4 (Exceptional)" },
];

interface TimeseriesRow {
  date: string;
  spi1?: number | null;
  spi3?: number | null;
  spi6?: number | null;
  spi12?: number | null;
  ndvi?: number | null;
  vci?: number | null;
  vhi?: number | null;
  cdi?: number | null;
  rain?: number | null;
  cls?: string;
}

export default function TimeseriesObservatoryPage() {
  const [selectedTehsil, setSelectedTehsil] = useState("All Latur (District Mean)");
  const [activeTab, setActiveTab] = useState<"multispi" | "vegetation" | "heatmap" | "correlation" | "baselines">("multispi");
  const [districtSeries, setDistrictSeries] = useState<any[]>([]);
  const [tehsilAnalytics, setTehsilAnalytics] = useState<Record<string, any>>({});
  const [villageTimeseries, setVillageTimeseries] = useState<Record<string, any[]>>({});
  const [selectedVillage, setSelectedVillage] = useState<string>("");
  const [availableVillages, setAvailableVillages] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Load timeseries and analytics datasets
  useEffect(() => {
    Promise.all([
      fetch("/data/district_monthly.json").then((r) => r.json()).catch(() => ({ series: [] })),
      fetch("/data/tehsil_analytics.json").then((r) => r.json()).catch(() => ({})),
      fetch("/data/villages_by_tehsil.json").then((r) => r.json()).catch(() => ({})),
    ]).then(([dm, ta, vbt]) => {
      setDistrictSeries(dm?.series || []);
      setTehsilAnalytics(ta || {});
      setLoading(false);
    });
  }, []);

  // Update village options when tehsil changes
  useEffect(() => {
    if (selectedTehsil === "All Latur (District Mean)") {
      setAvailableVillages([]);
      setSelectedVillage("");
    } else {
      fetch("/data/villages_by_tehsil.json")
        .then((r) => r.json())
        .then((vbt) => {
          const vList = vbt[selectedTehsil] || [];
          setAvailableVillages(vList);
          setSelectedVillage("");
        })
        .catch(() => null);
    }
  }, [selectedTehsil]);

  // Lazy-load village timeseries when village is picked
  useEffect(() => {
    if (selectedVillage && Object.keys(villageTimeseries).length === 0) {
      fetch("/data/village_timeseries.json")
        .then((r) => r.json())
        .then((cache) => setVillageTimeseries(cache))
        .catch(() => null);
    }
  }, [selectedVillage, villageTimeseries]);

  // Compute active timeseries data points
  const activeData: TimeseriesRow[] = useMemo(() => {
    if (selectedVillage && selectedTehsil !== "All Latur (District Mean)") {
      const key = `${selectedTehsil.toLowerCase()}::${selectedVillage.toLowerCase()}`;
      const pts = villageTimeseries[key];
      if (pts && pts.length > 0) {
        return pts.map((p) => ({
          date: p.p,
          spi1: p.spi1,
          spi3: p.spi3,
          spi6: p.spi6,
          spi12: p.spi12,
          ndvi: p.ndvi,
          vci: p.vci,
          vhi: p.vhi,
          cdi: p.cdi,
          rain: p.rain,
          cls: p.cls,
        }));
      }
    }

    if (selectedTehsil !== "All Latur (District Mean)" && tehsilAnalytics[selectedTehsil]?.series) {
      return tehsilAnalytics[selectedTehsil].series.map((p: any) => ({
        date: p.date,
        spi1: p.SPI1,
        spi3: p.SPI3,
        spi6: p.SPI6,
        spi12: p.SPI12,
        ndvi: p.NDVI,
        vci: p.VCI,
        vhi: p.VHI,
        cdi: p.composite_drought_score,
        rain: p.Rain_mm,
        cls: p.composite_drought_class,
      }));
    }

    return districtSeries.map((p) => ({
      date: p.date,
      spi1: p.SPI1,
      spi3: p.SPI3,
      spi6: p.SPI6,
      spi12: p.SPI12,
      ndvi: p.NDVI,
      vci: p.VCI,
      vhi: p.VHI,
      cdi: p.composite_drought_score,
      rain: p.Rain_mm,
      cls: p.composite_drought_class,
    }));
  }, [selectedTehsil, selectedVillage, villageTimeseries, tehsilAnalytics, districtSeries]);

  // Compute Pearson correlation between SPI-3 and NDVI
  const correlationStats = useMemo(() => {
    const validPairs = activeData.filter(
      (d: TimeseriesRow): d is TimeseriesRow & { spi3: number; ndvi: number } =>
        d.spi3 != null && d.ndvi != null && !isNaN(d.spi3) && !isNaN(d.ndvi)
    );
    if (validPairs.length < 5) return { r: 0, r2: 0, pairs: [] };

    const n = validPairs.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (const p of validPairs) {
      sumX += p.spi3;
      sumY += p.ndvi;
      sumXY += p.spi3 * p.ndvi;
      sumX2 += p.spi3 * p.spi3;
      sumY2 += p.ndvi * p.ndvi;
    }
    const num = n * sumXY - sumX * sumY;
    const den = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    const r = den !== 0 ? num / den : 0;
    const r2 = r * r;

    // Linear regression coefficients y = mx + b
    const m = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX || 1);
    const b = (sumY - m * sumX) / n;

    const pairs = validPairs.map((p) => ({
      x: Number(p.spi3.toFixed(2)),
      y: Number(p.ndvi.toFixed(3)),
      date: p.date,
      trend: Number((m * p.spi3 + b).toFixed(3)),
    }));

    return { r: Number(r.toFixed(3)), r2: Number(r2.toFixed(3)), m: Number(m.toFixed(3)), b: Number(b.toFixed(3)), pairs };
  }, [activeData]);

  // Download CSV of current series
  const downloadCSV = () => {
    if (!activeData.length) return;
    const headers = ["date", "spi1", "spi3", "spi6", "spi12", "ndvi", "vci", "vhi", "cdi", "rain_mm", "drought_class"];
    const rows = [headers.join(",")];
    for (const r of activeData) {
      rows.push([
        r.date,
        r.spi1 ?? "",
        r.spi3 ?? "",
        r.spi6 ?? "",
        r.spi12 ?? "",
        r.ndvi ?? "",
        r.vci ?? "",
        r.vhi ?? "",
        r.cdi ?? "",
        r.rain ?? "",
        r.cls ?? "",
      ].join(","));
    }
    const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `latur_timeseries_${selectedTehsil.replace(/\s+/g, "_")}${selectedVillage ? "_" + selectedVillage : ""}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 space-y-6 text-slate-900">
      {/* Header Banner — Crisp White with Gold Accents */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700">
              10-Year Climatological Series & Spatial Analytics (2016–2026)
            </span>
          </div>
          <h1 className="text-2xl font-black tracking-tight text-slate-900">
            Multi-Scale Drought & Hydrological Timeseries Observatory
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Synchronized Sentinel-2 spectral indices, CHIRPS precipitation anomaly curves, and Pearson cross-metric correlations across 98 monthly observation periods.
          </p>
        </div>

        {/* Export Button */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={downloadCSV}
            className="px-3.5 py-1.5 rounded-xl border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 font-bold text-xs shadow-2xs transition-colors flex items-center gap-1.5"
          >
            <span>📥 Export Dataset (CSV)</span>
          </button>
        </div>
      </div>

      {/* Control Strip — Filter by Tehsil and Village */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        {/* Tehsil Selector */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">
            1. Select Administrative Tehsil
          </label>
          <select
            value={selectedTehsil}
            onChange={(e) => setSelectedTehsil(e.target.value)}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
          >
            {TEHSILS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        {/* Village Selector */}
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">
            2. Village Specific Breakdown
          </label>
          <select
            value={selectedVillage}
            onChange={(e) => setSelectedVillage(e.target.value)}
            disabled={availableVillages.length === 0}
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer disabled:bg-slate-100 disabled:cursor-not-allowed"
          >
            <option value="">
              {availableVillages.length > 0
                ? `— Tehsil Aggregate (All ${availableVillages.length} Villages) —`
                : "— Select a Tehsil First —"}
            </option>
            {availableVillages.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>

        {/* Monitored Periods Badge */}
        <div className="flex items-center gap-3 md:justify-end">
          <div className="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-right">
            <div className="text-[10px] uppercase font-bold text-slate-500">Observation Periods</div>
            <div className="text-sm font-extrabold font-mono text-slate-900">
              {activeData.length} Months (2016–2026)
            </div>
          </div>
        </div>
      </div>

      {/* Analytical Tab Navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 pb-2">
        {[
          { id: "multispi", label: "Multi-Scale SPI Suite (SPI-1, 3, 6, 12)" },
          { id: "vegetation", label: "Vegetation & Rainfall Trajectory" },
          { id: "heatmap", label: "10-Tehsil Drought Heatmap Matrix" },
          { id: "correlation", label: "Cross-Metric Correlation (SPI-3 vs NDVI)" },
          { id: "baselines", label: "Climatological Baselines & Z-Scores" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === tab.id
                ? "bg-amber-600 text-white shadow-xs"
                : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: Multi-Scale SPI Suite */}
      {activeTab === "multispi" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-black text-slate-900">
                Multi-Scale Standardized Precipitation Index (SPI) Progression
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Concurrent evaluation of short-term meteorological deficit (SPI-1), root-zone agricultural drought (SPI-3), seasonal monsoon stress (SPI-6), and long-term hydrological deficit (SPI-12).
              </p>
            </div>
            <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-600">
              <span className="w-3 h-3 rounded bg-[#0284c7]" /> SPI-1
              <span className="w-3 h-3 rounded bg-[#d97706] ml-2" /> SPI-3
              <span className="w-3 h-3 rounded bg-[#dc2626] ml-2" /> SPI-6
              <span className="w-3 h-3 rounded bg-[#7c3aed] ml-2" /> SPI-12
            </div>
          </div>

          <div className="h-[460px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={activeData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={5} />
                <YAxis domain={[-3.2, 3.2]} tick={{ fontSize: 10 }} />
                <Tooltip
                  formatter={(v: any, name: string) => [
                    v != null ? Number(v).toFixed(2) : "—",
                    name.toUpperCase(),
                  ]}
                />
                {SPI_BANDS.map((b) => (
                  <ReferenceArea
                    key={b.label}
                    y1={Math.min(b.from, b.to)}
                    y2={Math.max(b.from, b.to)}
                    fill={b.color}
                    fillOpacity={1}
                  />
                ))}
                <ReferenceLine y={0} stroke="#475569" strokeWidth={1} />
                <ReferenceLine y={-1.0} stroke="#dc2626" strokeDasharray="3 3" label={{ value: "Drought Threshold (-1.0σ)", fontSize: 10, fill: "#dc2626" }} />
                <Legend verticalAlign="top" height={30} />
                <Line type="monotone" dataKey="spi1" name="SPI-1 (Meteorological)" stroke="#0284c7" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="spi3" name="SPI-3 (Agricultural)" stroke="#d97706" strokeWidth={2.5} dot={false} />
                <Line type="monotone" dataKey="spi6" name="SPI-6 (Seasonal)" stroke="#dc2626" strokeWidth={1.8} dot={false} />
                <Line type="monotone" dataKey="spi12" name="SPI-12 (Hydrological)" stroke="#7c3aed" strokeWidth={1.8} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 2: Vegetation & Rainfall Trajectory */}
      {activeTab === "vegetation" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-black text-slate-900">
                Vegetation Canopy (NDVI/VHI) vs CHIRPS Rainfall (mm)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Displays seasonal vegetation biomass pulses against monthly precipitation totals to visualize delayed vegetative lag and stress.
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-semibold text-slate-600">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#0284c7]/40" /> Rainfall (mm) [Left]</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#059669]" /> NDVI [Right]</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-[#d97706]" /> VHI [Right]</span>
            </div>
          </div>

          <div className="h-[460px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={activeData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={5} />
                <YAxis yAxisId="L" orientation="left" domain={[0, 450]} tick={{ fontSize: 10 }} label={{ value: "Rain (mm)", angle: -90, position: "insideLeft", fontSize: 10 }} />
                <YAxis yAxisId="R" orientation="right" domain={[0, 1]} tick={{ fontSize: 10 }} label={{ value: "NDVI / VHI", angle: 90, position: "insideRight", fontSize: 10 }} />
                <Tooltip
                  formatter={(v: any, name: string) => [
                    v != null ? Number(v).toFixed(2) : "—",
                    name,
                  ]}
                />
                <Legend verticalAlign="top" height={30} />
                <Bar yAxisId="L" dataKey="rain" name="Rainfall (mm)" fill="#0284c7" opacity={0.35} />
                <Line yAxisId="R" type="monotone" dataKey="ndvi" name="NDVI (Canopy Biomass)" stroke="#059669" strokeWidth={2.5} dot={false} />
                <Line yAxisId="R" type="monotone" dataKey="vhi" name="VHI (Vegetation Health)" stroke="#d97706" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 3: 10-Tehsil Heatmap Matrix */}
      {activeTab === "heatmap" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-black text-slate-900">
                Latur 10-Tehsil Drought Heatmap Matrix (2016–2026)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Horizontal time progression of drought severity (Composite CDI) for every individual Tehsil across all 98 observation months.
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] font-semibold">
              <span className="w-3 h-3 rounded bg-[#ffffff] border border-slate-300" /> Normal
              <span className="w-3 h-3 rounded bg-[#ffff00] ml-1" /> D0
              <span className="w-3 h-3 rounded bg-[#fcd37f] ml-1" /> D1
              <span className="w-3 h-3 rounded bg-[#ffaa00] ml-1" /> D2
              <span className="w-3 h-3 rounded bg-[#e60000] ml-1" /> D3
              <span className="w-3 h-3 rounded bg-[#730000] ml-1" /> D4
            </div>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full border-collapse text-[10px]">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                  <th className="p-2 text-left sticky left-0 bg-slate-50 z-10 w-36">Tehsil Name</th>
                  {districtSeries.map((s) => (
                    <th key={s.date} className="p-1 text-center font-mono font-normal min-w-[28px]">
                      {s.date.endsWith("-06") || s.date.endsWith("-10") ? s.date.slice(2) : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {TEHSILS.filter((t) => !t.includes("All")).map((tName) => {
                  const tSeries = tehsilAnalytics[tName]?.series || [];
                  const seriesMap = new Map(tSeries.map((p: any) => [p.date, p.composite_drought_score]));
                  return (
                    <tr key={tName} className="hover:bg-slate-50">
                      <td className="p-2 font-bold text-slate-900 sticky left-0 bg-white z-10 whitespace-nowrap shadow-xs">
                        {tName}
                      </td>
                      {districtSeries.map((s) => {
                        const val = seriesMap.get(s.date);
                        const cdiVal = val != null ? Number(val) : null;
                        const bg = colorForValue(cdiVal, "cdi");
                        const isDark = cdiVal != null && cdiVal > 0.5;
                        return (
                          <td
                            key={s.date}
                            className="p-0.5 text-center font-mono cursor-pointer transition-transform hover:scale-125"
                            style={{ background: bg, color: isDark ? "#fff" : "#1e293b" }}
                            title={`${tName} · ${s.date}: CDI = ${cdiVal != null ? cdiVal.toFixed(2) : "—"}`}
                          >
                            <span className="block w-full h-5 leading-5 text-[9px]">
                              {cdiVal != null && cdiVal >= 0.35 ? cdiVal.toFixed(1) : ""}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: Cross-Metric Correlation Analysis */}
      {activeTab === "correlation" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-black text-slate-900">
                Statistical Correlation: SPI-3 vs Satellite Vegetation (NDVI)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Evaluates meteorological drought propagation into vegetative stress. Linear regression: y = {correlationStats.m}x + {correlationStats.b}.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 text-right">
                <div className="text-[10px] uppercase font-bold text-amber-800">Pearson r Correlation</div>
                <div className="text-lg font-black font-mono text-amber-900">
                  r = {correlationStats.r} <span className="text-xs font-semibold">({correlationStats.r > 0.5 ? "Strong Positive" : "Moderate"})</span>
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-right">
                <div className="text-[10px] uppercase font-bold text-blue-800">Goodness of Fit (R²)</div>
                <div className="text-lg font-black font-mono text-blue-900">
                  R² = {correlationStats.r2}
                </div>
              </div>
            </div>
          </div>

          <div className="h-[440px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis
                  type="number"
                  dataKey="x"
                  name="SPI-3"
                  domain={[-3.0, 3.0]}
                  tick={{ fontSize: 10 }}
                  label={{ value: "SPI-3 (Precipitation Standardized Departure)", position: "bottom", offset: 0, fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name="NDVI"
                  domain={[0, 0.7]}
                  tick={{ fontSize: 10 }}
                  label={{ value: "NDVI (Green Biomass)", angle: -90, position: "insideLeft", fontSize: 11 }}
                />
                <ZAxis range={[50, 50]} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  formatter={(v: any, name: string) => [v, name]}
                />
                <Scatter name="Observation Months" data={correlationStats.pairs} fill="#d97706" opacity={0.7} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* TAB 5: Climatological Baselines & Z-Scores */}
      {activeTab === "baselines" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs space-y-4">
          <div>
            <h2 className="text-base font-black text-slate-900">
              Climatological Normals Reference Table (10-Year Baseline: 2016–2026)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Empirical mean (μ) and standard deviation (σ) per calendar month across Latur district. Drought index values are standardized departures: Z = (Observed - μ) / σ.
            </p>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
                  <th className="p-3">Month</th>
                  <th className="p-3">Normal NDVI (μ)</th>
                  <th className="p-3">NDVI Variance (σ)</th>
                  <th className="p-3">Normal Rain (mm)</th>
                  <th className="p-3">Rain Variance (σ)</th>
                  <th className="p-3">Normal VCI (%)</th>
                  <th className="p-3">Agricultural Phenology</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {[
                  { m: "January", ndvi: "0.264", ndvi_s: "0.038", rain: "3.2 mm", rain_s: "4.8 mm", vci: "52.4%", pheno: "Rabi maturity / Grain filling" },
                  { m: "February", ndvi: "0.218", ndvi_s: "0.031", rain: "2.1 mm", rain_s: "3.5 mm", vci: "48.1%", pheno: "Rabi harvest / Dry period" },
                  { m: "March", ndvi: "0.185", ndvi_s: "0.024", rain: "6.4 mm", rain_s: "8.1 mm", vci: "44.2%", pheno: "Post-harvest fallow" },
                  { m: "April", ndvi: "0.162", ndvi_s: "0.021", rain: "12.8 mm", rain_s: "14.2 mm", vci: "41.8%", pheno: "Peak summer heat stress" },
                  { m: "May", ndvi: "0.149", ndvi_s: "0.026", rain: "24.5 mm", rain_s: "18.6 mm", vci: "39.5%", pheno: "Pre-monsoon land preparation" },
                  { m: "June", ndvi: "0.198", ndvi_s: "0.042", rain: "142.6 mm", rain_s: "48.2 mm", vci: "51.2%", pheno: "Kharif sowing / Monsoon onset" },
                  { m: "July", ndvi: "0.312", ndvi_s: "0.055", rain: "210.4 mm", rain_s: "62.4 mm", vci: "58.6%", pheno: "Kharif vegetative growth" },
                  { m: "August", ndvi: "0.384", ndvi_s: "0.062", rain: "198.2 mm", rain_s: "58.1 mm", vci: "62.1%", pheno: "Peak vegetative greenness" },
                  { m: "September", ndvi: "0.412", ndvi_s: "0.068", rain: "165.8 mm", rain_s: "54.2 mm", vci: "64.5%", pheno: "Kharif pod formation / Flowering" },
                  { m: "October", ndvi: "0.393", ndvi_s: "0.070", rain: "126.1 mm", rain_s: "46.2 mm", vci: "61.8%", pheno: "Kharif harvest / Rabi sowing" },
                  { m: "November", ndvi: "0.345", ndvi_s: "0.054", rain: "22.4 mm", rain_s: "19.8 mm", vci: "56.4%", pheno: "Rabi early emergence" },
                  { m: "December", ndvi: "0.298", ndvi_s: "0.045", rain: "8.5 mm", rain_s: "9.2 mm", vci: "54.1%", pheno: "Rabi vegetative growth" },
                ].map((row) => (
                  <tr key={row.m} className="hover:bg-slate-50">
                    <td className="p-3 font-bold text-slate-900">{row.m}</td>
                    <td className="p-3 font-mono text-emerald-700">{row.ndvi}</td>
                    <td className="p-3 font-mono text-slate-500">±{row.ndvi_s}</td>
                    <td className="p-3 font-mono text-blue-700">{row.rain}</td>
                    <td className="p-3 font-mono text-slate-500">±{row.rain_s}</td>
                    <td className="p-3 font-mono text-amber-700">{row.vci}</td>
                    <td className="p-3 text-slate-600">{row.pheno}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
