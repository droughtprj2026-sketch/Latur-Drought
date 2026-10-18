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

  const [customSeries, setCustomSeries] = useState<any[] | null>(null);
  const [baselinesData, setBaselinesData] = useState<any>(null);
  const [corrX, setCorrX] = useState<string>("spi3");
  const [corrY, setCorrY] = useState<string>("ndvi");

  // Load timeseries, baselines, and analytics datasets via API
  useEffect(() => {
    Promise.all([
      fetch("/api/v1/district-timeseries").then((r) => r.json()).catch(() => ({ series: [] })),
      fetch("/api/v1/tehsil-analytics").then((r) => r.json()).catch(() => ({})),
      fetch("/data/villages_by_tehsil.json").then((r) => r.json()).catch(() => ({})),
      fetch("/api/v1/baselines").then((r) => r.json()).catch(() => ({})),
    ]).then(([dm, ta, vbt, bData]) => {
      setDistrictSeries(dm?.series || []);
      setTehsilAnalytics(ta || {});
      setBaselinesData(bData || {});
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

  // Fetch dynamic timeseries whenever selectedTehsil or selectedVillage changes
  useEffect(() => {
    if (selectedTehsil === "All Latur (District Mean)") {
      setCustomSeries(null);
      return;
    }
    const t = selectedTehsil.trim();
    const v = selectedVillage.trim();
    const url = v
      ? `/api/v1/timeseries?tehsil=${encodeURIComponent(t)}&village=${encodeURIComponent(v)}`
      : `/api/v1/timeseries?tehsil=${encodeURIComponent(t)}`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setCustomSeries(data);
        } else {
          setCustomSeries(null);
        }
      })
      .catch(() => setCustomSeries(null));
  }, [selectedTehsil, selectedVillage]);

  // Compute active timeseries data points
  const activeData: TimeseriesRow[] = useMemo(() => {
    if (customSeries && customSeries.length > 0) {
      return customSeries.map((p) => ({
        date: p.p || p.date,
        spi1: p.spi1 ?? p.SPI1 ?? null,
        spi3: p.spi3 ?? p.SPI3 ?? null,
        spi6: p.spi6 ?? p.SPI6 ?? null,
        spi12: p.spi12 ?? p.SPI12 ?? null,
        ndvi: p.ndvi ?? p.NDVI ?? null,
        vci: p.vci ?? p.VCI ?? null,
        vhi: p.vhi ?? p.VHI ?? null,
        vhi_scaled: p.vhi != null ? p.vhi / 100 : (p.VHI != null ? p.VHI / 100 : null),
        cdi: p.cdi ?? p.composite_drought_score ?? null,
        rain: p.rain ?? p.Rain_mm ?? 0,
        cls: p.cls ?? p.composite_drought_class ?? "None",
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
      vhi_scaled: p.VHI != null ? p.VHI / 100 : null,
      cdi: p.composite_drought_score,
      rain: p.Rain_mm,
      cls: p.composite_drought_class,
    }));
  }, [customSeries, districtSeries]);

  const tehsilMatrix: Record<string, Record<string, number>> = useMemo(() => {
    return tehsilAnalytics?.monthly_matrix || {};
  }, [tehsilAnalytics]);

  // Compute Pearson correlation between selected corrX and corrY
  const correlationStats = useMemo(() => {
    const validPairs = activeData.filter((d: any) => {
      const vx = d[corrX];
      const vy = d[corrY];
      return vx != null && vy != null && !isNaN(vx) && !isNaN(vy);
    });
    if (validPairs.length < 5) return { r: 0, r2: 0, m: 0, b: 0, pairs: [] };

    const n = validPairs.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (const p of validPairs) {
      const vx = Number((p as any)[corrX]);
      const vy = Number((p as any)[corrY]);
      sumX += vx;
      sumY += vy;
      sumXY += vx * vy;
      sumX2 += vx * vx;
      sumY2 += vy * vy;
    }
    const num = n * sumXY - sumX * sumY;
    const den = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    const r = den !== 0 ? num / den : 0;
    const r2 = r * r;

    // Linear regression coefficients y = mx + b
    const m = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX || 1);
    const b = (sumY - m * sumX) / n;

    const pairs = validPairs.map((p: any) => ({
      x: Number(Number(p[corrX]).toFixed(2)),
      y: Number(Number(p[corrY]).toFixed(3)),
      date: p.date,
      trend: Number((m * Number(p[corrX]) + b).toFixed(3)),
    }));

    return {
      r: Number(r.toFixed(3)),
      r2: Number(r2.toFixed(3)),
      m: Number(m.toFixed(3)),
      b: Number(b.toFixed(3)),
      pairs,
    };
  }, [activeData, corrX, corrY]);

  // Dynamic Climatological Baselines (10-Year Empirical μ, σ and Z-Scores)
  const dynamicBaselines = useMemo(() => {
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    const phenology = [
      "Rabi maturity / Grain filling",
      "Rabi harvest / Dry period",
      "Post-harvest fallow",
      "Peak summer heat stress",
      "Pre-monsoon land preparation",
      "Kharif sowing / Monsoon onset",
      "Kharif vegetative growth",
      "Peak vegetative greenness",
      "Kharif pod formation / Flowering",
      "Kharif harvest / Rabi sowing",
      "Rabi early emergence",
      "Rabi vegetative growth"
    ];

    return monthNames.map((name, i) => {
      const mNum = String(i + 1).padStart(2, "0");
      const monthObs = activeData.filter((d: any) => d.date && d.date.endsWith(`-${mNum}`));
      
      const ndviVals = monthObs.map((d: any) => Number(d.ndvi)).filter((v: number) => !isNaN(v) && v > 0);
      const rainVals = monthObs.map((d: any) => Number(d.rain)).filter((v: number) => !isNaN(v) && v >= 0);
      const vciVals = monthObs.map((d: any) => Number(d.vci)).filter((v: number) => !isNaN(v) && v >= 0);

      const calcStats = (vals: number[]) => {
        if (!vals.length) return { mean: 0, std: 0 };
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        const variance = vals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / vals.length;
        return { mean, std: Math.sqrt(variance) };
      };

      const ndviStats = calcStats(ndviVals);
      const rainStats = calcStats(rainVals);
      const vciStats = calcStats(vciVals);

      const latestObs = monthObs.length ? monthObs[monthObs.length - 1] : null;
      let zScoreNdvi: number | null = null;
      if (latestObs && latestObs.ndvi != null && ndviStats.std > 0) {
        zScoreNdvi = (Number(latestObs.ndvi) - ndviStats.mean) / ndviStats.std;
      }

      return {
        m: name,
        monthNum: mNum,
        pheno: phenology[i],
        count: monthObs.length,
        ndvi_mean: ndviStats.mean > 0 ? ndviStats.mean.toFixed(3) : "—",
        ndvi_std: ndviStats.std > 0 ? ndviStats.std.toFixed(3) : "—",
        rain_mean: rainStats.mean > 0 ? `${rainStats.mean.toFixed(1)} mm` : "—",
        rain_std: rainStats.std > 0 ? `±${rainStats.std.toFixed(1)}` : "—",
        vci_mean: vciStats.mean > 0 ? `${(vciStats.mean * (vciStats.mean <= 1 ? 100 : 1)).toFixed(1)}%` : "—",
        latestYear: latestObs?.date?.split("-")[0] ?? "—",
        latestNdvi: latestObs?.ndvi != null ? Number(latestObs.ndvi).toFixed(3) : "—",
        latestRain: latestObs?.rain != null ? `${Number(latestObs.rain).toFixed(1)} mm` : "—",
        zScore: zScoreNdvi != null ? Number(zScoreNdvi.toFixed(2)) : null,
      };
    });
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
                <YAxis yAxisId="R" orientation="right" domain={[0, 1]} tick={{ fontSize: 10 }} label={{ value: "NDVI / VHI (0..1)", angle: 90, position: "insideRight", fontSize: 10 }} />
                <Tooltip
                  formatter={(v: any, name: string) => [
                    name.includes("VHI") && v != null
                      ? `${(Number(v) * 100).toFixed(1)}%`
                      : v != null
                      ? Number(v).toFixed(3)
                      : "—",
                    name,
                  ]}
                />
                <Legend verticalAlign="top" height={30} />
                <Bar yAxisId="L" dataKey="rain" name="Rainfall (mm)" fill="#0284c7" opacity={0.35} />
                <Line yAxisId="R" type="monotone" dataKey="ndvi" name="NDVI (Canopy Biomass)" stroke="#059669" strokeWidth={2.5} dot={false} />
                <Line yAxisId="R" type="monotone" dataKey="vhi_scaled" name="VHI (Vegetation Health %)" stroke="#d97706" strokeWidth={2} dot={false} />
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
                  const tMap = tehsilMatrix[tName] || {};
                  const isSelected = selectedTehsil === tName;
                  return (
                    <tr key={tName} className={`hover:bg-amber-50/40 transition-colors ${isSelected ? "bg-amber-50/70" : ""}`}>
                      <td
                        onClick={() => {
                          setSelectedTehsil(tName);
                          setSelectedVillage("");
                        }}
                        className="p-2 font-bold text-slate-900 sticky left-0 bg-white z-10 whitespace-nowrap shadow-xs cursor-pointer hover:text-amber-700"
                        title={`Click to filter timeseries to ${tName} Tehsil`}
                      >
                        <div className="flex items-center gap-1.5">
                          {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />}
                          <span>{tName}</span>
                        </div>
                      </td>
                      {districtSeries.map((s) => {
                        const rawVal = tMap[s.date];
                        const cdiVal = rawVal != null ? Number(rawVal) : null;
                        const bg = colorForValue(cdiVal, "cdi");
                        const isDark = cdiVal != null && cdiVal > 0.5;
                        return (
                          <td
                            key={s.date}
                            onClick={() => {
                              setSelectedTehsil(tName);
                              setSelectedVillage("");
                            }}
                            className="p-0.5 text-center font-mono cursor-pointer transition-transform hover:scale-125 hover:z-20 relative"
                            style={{ background: bg, color: isDark ? "#fff" : "#1e293b" }}
                            title={`${tName} · ${s.date}: CDI = ${cdiVal != null ? cdiVal.toFixed(3) : "ND (No Data)"}`}
                          >
                            <span className="block w-full h-5 leading-5 text-[9px] font-semibold">
                              {cdiVal != null && cdiVal >= 0.20 ? cdiVal.toFixed(1) : ""}
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
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-base font-black text-slate-900">
                  Statistical Correlation: {corrX.toUpperCase()} vs {corrY.toUpperCase()}
                </h2>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                  {selectedTehsil}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Linear regression: y = {correlationStats.m}x + {correlationStats.b}. Evaluates physiological and hydrological lag dynamics.
              </p>
            </div>

            {/* Metric Selectors */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-xl border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500">X-Axis:</span>
                <select
                  value={corrX}
                  onChange={(e) => setCorrX(e.target.value)}
                  className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
                >
                  <option value="spi3">SPI-3 (Agri Root-Zone)</option>
                  <option value="spi1">SPI-1 (Meteorological)</option>
                  <option value="spi6">SPI-6 (Seasonal)</option>
                  <option value="spi12">SPI-12 (Hydrological)</option>
                  <option value="rain">CHIRPS Rain (mm)</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-xl border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500">Y-Axis:</span>
                <select
                  value={corrY}
                  onChange={(e) => setCorrY(e.target.value)}
                  className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
                >
                  <option value="ndvi">NDVI (Canopy Biomass)</option>
                  <option value="vhi">VHI (Vegetation Health)</option>
                  <option value="vci">VCI (Condition Index)</option>
                  <option value="cdi">CDI (Drought Score)</option>
                </select>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-xl px-3 py-1 text-right">
                <div className="text-[9px] uppercase font-bold text-amber-800">Pearson r</div>
                <div className="text-sm font-black font-mono text-amber-900">
                  r = {correlationStats.r}
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-xl px-3 py-1 text-right">
                <div className="text-[9px] uppercase font-bold text-blue-800">R² Fit</div>
                <div className="text-sm font-black font-mono text-blue-900">
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
                  name={corrX.toUpperCase()}
                  tick={{ fontSize: 10 }}
                  label={{ value: `${corrX.toUpperCase()} Departure`, position: "bottom", offset: 0, fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  name={corrY.toUpperCase()}
                  tick={{ fontSize: 10 }}
                  label={{ value: corrY.toUpperCase(), angle: -90, position: "insideLeft", fontSize: 11 }}
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
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-black text-slate-900">
                Climatological Normals & Standardized Departures (2016–2026 Baseline)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Empirical mean (μ) and standard deviation (σ) computed directly from the active series for {selectedVillage ? `${selectedVillage} village` : `${selectedTehsil} tehsil`}. Standardized Z-Score: Z = (Observed - μ) / σ.
              </p>
            </div>
            <div className="text-xs font-bold text-amber-700 bg-amber-50 px-3 py-1.5 rounded-lg border border-amber-200">
              Active Scope: {selectedTehsil} {selectedVillage ? `→ ${selectedVillage}` : "(All Villages)"}
            </div>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase text-[10px]">
                  <th className="p-3">Month</th>
                  <th className="p-3">Normal NDVI (μ ± σ)</th>
                  <th className="p-3">Normal Rain (μ ± σ)</th>
                  <th className="p-3">Normal VCI (μ)</th>
                  <th className="p-3">Latest Obs (NDVI)</th>
                  <th className="p-3">Latest Obs (Rain)</th>
                  <th className="p-3">NDVI Z-Score</th>
                  <th className="p-3">Agricultural Phenology</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {dynamicBaselines.map((row) => {
                  const z = row.zScore;
                  let zBadge = <span className="text-slate-400 font-mono">—</span>;
                  if (z !== null) {
                    if (z <= -1.5) {
                      zBadge = <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 font-mono">Z = {z} (Severe Deficit)</span>;
                    } else if (z <= -0.5) {
                      zBadge = <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 font-mono">Z = {z} (Mild Deficit)</span>;
                    } else if (z >= 1.0) {
                      zBadge = <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 font-mono">Z = +{z} (Surplus/Vigor)</span>;
                    } else {
                      zBadge = <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 font-mono">Z = {z >= 0 ? `+${z}` : z} (Normal)</span>;
                    }
                  }

                  return (
                    <tr key={row.m} className="hover:bg-slate-50 transition-colors">
                      <td className="p-3 font-bold text-slate-900">{row.m}</td>
                      <td className="p-3 font-mono text-emerald-700">{row.ndvi_mean} <span className="text-slate-400 text-[10px]">±{row.ndvi_std}</span></td>
                      <td className="p-3 font-mono text-blue-700">{row.rain_mean} <span className="text-slate-400 text-[10px]">{row.rain_std}</span></td>
                      <td className="p-3 font-mono text-amber-700">{row.vci_mean}</td>
                      <td className="p-3 font-mono text-slate-800">{row.latestNdvi} <span className="text-[10px] text-slate-400">({row.latestYear})</span></td>
                      <td className="p-3 font-mono text-slate-800">{row.latestRain}</td>
                      <td className="p-3">{zBadge}</td>
                      <td className="p-3 text-slate-600 text-[11px]">{row.pheno}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
