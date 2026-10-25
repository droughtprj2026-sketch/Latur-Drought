"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  LineChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
  BarChart,
  Cell,
  Area,
} from "recharts";
import type { VillageProperties } from "./VillageIntelligenceDrawer";
import { codeForCDI, colorForValue } from "@/lib/classify";
import { loadBaselines, loadDistrictMonthly, loadTehsilAnalytics, loadTimeseries, loadVillageIndex, type TimeseriesById, type VillagesByTehsil } from "@/lib/data";

interface Props {
  village: VillageProperties | null;
  selectedTehsil: string;
  selectedPeriod: string;
  onSelectTehsil: (t: string) => void;
  onSelectVillageByName?: (name: string) => void;
  summary?: { total: number; assessed: number; inDrought: number; d2plus: number; mean: number | null; means: Record<string, number | null> } | null;
}

interface TimeseriesPoint {
  p?: string;
  date?: string;
  cdi?: number | null;
  CDI?: number | null;
  composite_drought_score?: number | null;
  cls?: string;
  class?: string;
  composite_drought_class?: string;
  rain?: number | null;
  Rain_mm?: number | null;
  ndvi?: number | null;
  NDVI?: number | null;
  vhi?: number | null;
  VHI?: number | null;
  vci?: number | null;
  VCI?: number | null;
  spi1?: number | null;
  SPI1?: number | null;
  spi3?: number | null;
  SPI3?: number | null;
  spi6?: number | null;
  SPI6?: number | null;
  spi12?: number | null;
  SPI12?: number | null;
}

const SEVERITY_INFO: Record<string, { bg: string; text: string; border: string; label: string; badge: string }> = {
  None: { bg: "bg-slate-100", text: "text-slate-700", border: "border-slate-300", label: "Not in drought", badge: "bg-slate-200 text-slate-800 border-slate-300" },
  D0: { bg: "bg-yellow-50", text: "text-amber-700", border: "border-amber-200", label: "D0 · Abnormally Dry", badge: "bg-amber-100 text-amber-800 border-amber-300" },
  D1: { bg: "bg-amber-50", text: "text-amber-800", border: "border-amber-300", label: "D1 · Moderate Drought", badge: "bg-amber-200 text-amber-900 border-amber-400" },
  D2: { bg: "bg-orange-50", text: "text-orange-800", border: "border-orange-300", label: "D2 · Severe Drought", badge: "bg-orange-200 text-orange-900 border-orange-400" },
  D3: { bg: "bg-red-50", text: "text-red-800", border: "border-red-300", label: "D3 · Extreme Drought", badge: "bg-red-200 text-red-900 border-red-400" },
  D4: { bg: "bg-rose-50", text: "text-rose-900", border: "border-rose-300", label: "D4 · Exceptional Drought", badge: "bg-rose-200 text-rose-950 border-rose-400" },
};

function getAdvisory(cls?: string): string {
  switch (cls) {
    case "D4":
      return "Emergency declaration tier. Enforce critical drinking water rationing, mobilize emergency tanker supplies, and prepare cattle fodder camps. Complete ban on non-potable surface withdrawals.";
    case "D3":
      return "Extreme stress. Initiate micro-irrigation protocols, restrict surface canal diversions for non-essential use, and deploy localized groundwater recharge surveillance.";
    case "D2":
      return "Severe drought stress. Prioritize protective sprinkler irrigation for standing Kharif/Rabi crops. Mulching and moisture conservation techniques strongly advised.";
    case "D1":
      return "Moderate moisture deficit. Soil moisture below historical average. Monitor reservoir levels and advise farmers against high-water-consumption crops.";
    case "D0":
      return "Early moisture deficit warning. Ground condition abnormally dry. Prepare farm pond rainwater storage and monitor meteorological precipitation trends.";
    default:
      return "Vegetation health and precipitation indicators within normal climatological baselines. Standard agricultural practices recommended.";
  }
}

export function PermanentSidebar({
  village,
  selectedTehsil,
  selectedPeriod,
  onSelectTehsil,
  onSelectVillageByName,
  summary = null,
}: Props) {
  const [tab, setTab] = useState<"overview" | "comparisons" | "rankings" | "heatmap">("overview");
  const [chartSubMode, setChartSubMode] = useState<"spi_multiscale" | "cdi_trajectory" | "climatology_envelope">("spi_multiscale");
  const [villageTs, setVillageTs] = useState<TimeseriesPoint[]>([]);
  const [districtTs, setDistrictTs] = useState<any[]>([]);
  const [baselinesData, setBaselinesData] = useState<any>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [allTs, setAllTs] = useState<TimeseriesById | null>(null);
  const [vIndex, setVIndex] = useState<VillagesByTehsil | null>(null);
  useEffect(() => {
    loadTimeseries().then(setAllTs).catch(() => null);
    loadVillageIndex().then(setVIndex).catch(() => null);
  }, []);
  // Tehsil league table for the month on screen (replaces the frozen latest-month file).
  const ranking = useMemo(() => {
    if (!allTs || !vIndex) return null;
    return Object.entries(vIndex).map(([tehsil, vs]) => {
      let n = 0, sum = 0, drought = 0, d2 = 0;
      for (const v of vs) {
        const pt = allTs[String(v.id)]?.find((x) => x.p === selectedPeriod);
        if (!pt || pt.cdi == null) continue;
        n++; sum += pt.cdi;
        const c = codeForCDI(pt.cdi);
        if (c !== "None") drought++;
        if (c === "D2" || c === "D3" || c === "D4") d2++;
      }
      return { tehsil, villages: vs.length, assessed: n, avg_cdi: n ? sum / n : 0,
               drought_pct: n ? (100 * drought) / n : 0, d2_plus: d2 };
    }).sort((a, b) => b.avg_cdi - a.avg_cdi);
  }, [allTs, vIndex, selectedPeriod]);
  const [tsScope, setTsScope] = useState<"village" | "district">("village");
  const [loadingTs, setLoadingTs] = useState(false);

  // Load district timeseries, baselines, and analytics on mount
  useEffect(() => {
    loadDistrictMonthly()
      .then((d) => setDistrictTs(d.series || []))
      .catch((e) => console.error("Error loading district timeseries:", e));

    loadBaselines()
      .then((d) => setBaselinesData(d))
      .catch((e) => console.error("Error loading village baselines:", e));

    loadTehsilAnalytics()
      .then((d) => setAnalytics(d))
      .catch((e) => console.error("Error loading tehsil analytics:", e));
  }, []);

  // Fetch village timeseries when village selection changes
  useEffect(() => {
    if (!village) {
      setVillageTs([]);
      return;
    }
    if (village.id == null) return;
    setLoadingTs(true);
    loadTimeseries()
      .then((all) => setVillageTs(all[String(village.id)] || []))
      .catch(() => setVillageTs([]))
      .finally(() => setLoadingTs(false));
  }, [village]);

  // 1. Current District point for selectedPeriod
  const currentDistrictPoint = useMemo(() => {
    return districtTs.find((d: any) => d.date === selectedPeriod) || null;
  }, [districtTs, selectedPeriod]);

  // 2. Current Village point for selectedPeriod from villageTs
  const currentVillagePoint = useMemo(() => {
    if (!villageTs || villageTs.length === 0) return null;
    return villageTs.find((x: any) => (x.p || x.date) === selectedPeriod) || null;
  }, [villageTs, selectedPeriod]);

  // 3. Active Metrics: accurately merge village or district aggregate for selectedPeriod
  const activeMetrics = useMemo(() => {
    if (village) {
      if (currentVillagePoint) {
        return {
          cdi: currentVillagePoint.cdi ?? village.CDI ?? null,
          cls: currentVillagePoint.cls ?? village.CDI_class ?? village.class ?? "None",
          ndvi: currentVillagePoint.ndvi ?? village.NDVI ?? null,
          vhi: currentVillagePoint.vhi ?? village.VHI ?? null,
          vci: currentVillagePoint.vci ?? village.VCI ?? null,
          rain: currentVillagePoint.rain ?? village.Rain_mm ?? null,
          spi1: currentVillagePoint.spi1 ?? village.SPI1 ?? null,
          spi3: currentVillagePoint.spi3 ?? village.SPI3 ?? null,
          spi6: currentVillagePoint.spi6 ?? village.SPI6 ?? null,
          spi12: currentVillagePoint.spi12 ?? village.SPI12 ?? null,
        };
      }
      return {
        cdi: village.CDI ?? null,
        cls: village.CDI_class ?? village.class ?? "None",
        ndvi: village.NDVI ?? null,
        vhi: village.VHI ?? null,
        vci: village.VCI ?? null,
        rain: village.Rain_mm ?? null,
        spi1: village.SPI1 ?? null,
        spi3: village.SPI3 ?? null,
        spi6: village.SPI6 ?? null,
        spi12: village.SPI12 ?? null,
      };
    }

    // No village selected: describe the villages on screen (district or chosen tehsil),
    // the same population the KPI strip and the map legend count.
    if (summary && summary.assessed > 0) {
      const m = summary.means;
      return {
        cdi: summary.mean,
        cls: summary.mean != null ? codeForCDI(summary.mean) : "None",
        ndvi: m.ndvi ?? null, vhi: m.vhi ?? null, vci: m.vci ?? null, rain: m.rain ?? null,
        spi1: m.spi1 ?? null, spi3: m.spi3 ?? null, spi6: m.spi6 ?? null, spi12: m.spi12 ?? null,
      };
    }

    if (currentDistrictPoint) {
      return {
        cdi: currentDistrictPoint.composite_drought_score ?? null,
        cls: currentDistrictPoint.composite_drought_class ?? (currentDistrictPoint.composite_drought_score >= 0.2 ? "D0" : "None"),
        ndvi: currentDistrictPoint.NDVI ?? null,
        vhi: currentDistrictPoint.VHI ?? null,
        vci: currentDistrictPoint.VCI ?? null,
        rain: currentDistrictPoint.Rain_mm ?? null,
        spi1: currentDistrictPoint.SPI1 ?? null,
        spi3: currentDistrictPoint.SPI3 ?? null,
        spi6: currentDistrictPoint.SPI6 ?? null,
        spi12: currentDistrictPoint.SPI12 ?? null,
      };
    }

    return {
      cdi: null, cls: "None", ndvi: null, vhi: null, vci: null,
      rain: null, spi1: null, spi3: null, spi6: null, spi12: null,
    };
  }, [village, currentVillagePoint, currentDistrictPoint, summary]);

  // Thermal / soil-moisture readings (present once the Landsat LST + Sentinel-1 history has been backfilled).
  const thermalMetrics = useMemo(() => {
    const pt: any = currentVillagePoint;
    const v: any = village;
    const m = summary?.means;
    const t = village
      ? { tci: pt?.tci ?? v?.TCI ?? null, smi: pt?.smi ?? v?.SMI ?? null, lst: pt?.lst ?? v?.LST ?? null }
      : { tci: m?.tci ?? null, smi: m?.smi ?? null, lst: m?.lst ?? null };
    return t.tci != null || t.smi != null || t.lst != null ? t : null;
  }, [village, currentVillagePoint, summary]);

  const villageName = village?.village || village?.VILLAGE || village?.name || (selectedTehsil !== "All" ? `${selectedTehsil} Tehsil Aggregate` : "Latur District Aggregate");
  const tehsilName = village?.tehsil || village?.TEHSIL || (selectedTehsil !== "All" ? selectedTehsil : "All 10 Tehsils");
  
  // Resolve accurate drought severity class
  // Class always follows the CDI thresholds in config/composite.yaml (same as the map).
  const derived = activeMetrics.cdi != null ? codeForCDI(activeMetrics.cdi) : "None";
  const cdiClass = activeMetrics.cdi != null ? derived : "None";

  const sev = SEVERITY_INFO[cdiClass] || SEVERITY_INFO["None"];

  // Extract month integer from selectedPeriod (e.g. "10" from "2026-10")
  const currentMonthInt = useMemo(() => {
    const parts = (selectedPeriod || "2026-10").split("-");
    return parts[1] ? parseInt(parts[1], 10) : 10;
  }, [selectedPeriod]);

  // Lookup Baseline for current village or district and calendar month
  const currentBaseline = useMemo(() => {
    if (!baselinesData) return null;
    if (village) {
      const vBaselines = baselinesData.villages?.[String(village.id)];
      if (vBaselines && vBaselines[currentMonthInt]) {
        return vBaselines[currentMonthInt];
      }
    }
    // Fallback to district baseline for that month
    return baselinesData.district?.[currentMonthInt] || null;
  }, [baselinesData, village, currentMonthInt]);

  // Active timeseries data based on scope
  const chartData = useMemo(() => {
    if (tsScope === "village" && villageTs.length > 0) {
      return villageTs.map((d) => ({
        date: d.p || d.date,
        cdi: d.cdi != null ? Number(d.cdi.toFixed(2)) : null,
        rain: d.rain != null ? Number(d.rain.toFixed(1)) : 0,
        ndvi: d.ndvi != null ? Number(d.ndvi.toFixed(2)) : null,
        vhi: d.vhi != null ? Number(d.vhi.toFixed(1)) : null,
        vci: d.vci != null ? Number(d.vci.toFixed(1)) : null,
        spi1: d.spi1 != null ? Number(d.spi1.toFixed(2)) : null,
        spi3: d.spi3 != null ? Number(d.spi3.toFixed(2)) : null,
        spi6: d.spi6 != null ? Number(d.spi6.toFixed(2)) : null,
        spi12: d.spi12 != null ? Number(d.spi12.toFixed(2)) : null,
        cls: d.cls || "None",
      }));
    }
    // District series
    return districtTs.map((d: any) => ({
      date: d.date,
      cdi: d.composite_drought_score != null ? Number(d.composite_drought_score.toFixed(2)) : null,
      rain: d.Rain_mm != null ? Number(d.Rain_mm.toFixed(1)) : 0,
      ndvi: d.NDVI != null ? Number(d.NDVI.toFixed(2)) : null,
      vhi: d.VHI != null ? Number(d.VHI.toFixed(1)) : null,
      vci: d.VCI != null ? Number(d.VCI.toFixed(1)) : null,
      spi1: d.SPI1 != null ? Number(d.SPI1.toFixed(2)) : null,
      spi3: d.SPI3 != null ? Number(d.SPI3.toFixed(2)) : null,
      spi6: d.SPI6 != null ? Number(d.SPI6.toFixed(2)) : null,
      spi12: d.SPI12 != null ? Number(d.SPI12.toFixed(2)) : null,
      cls: d.composite_drought_class || "None",
    }));
  }, [tsScope, villageTs, districtTs]);

  // Compute 12-Month Climatology Envelope Curve (Normal mean vs Observed year)
  const climatologyEnvelope = useMemo(() => {
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const yr = (selectedPeriod || "2026-10").split("-")[0] || "2026";

    return monthNames.map((mName, i) => {
      const mNum = i + 1;
      const b = (baselinesData?.district && baselinesData.district[mNum]) || {};
      const dateKey = `${yr}-${String(mNum).padStart(2, "0")}`;
      const observed = chartData.find((p) => p.date === dateKey);

      return {
        month: mName,
        normal_ndvi: b.ndvi_mean ?? null,
        normal_rain: b.rain_mean ?? null,
        observed_ndvi: observed?.ndvi ?? null,
        observed_rain: observed?.rain ?? null,
        observed_cdi: observed?.cdi ?? null,
      };
    });
  }, [baselinesData, selectedPeriod, chartData]);

  // Baseline deltas and z-scores from activeMetrics
  const baselineNDVI = currentBaseline?.ndvi_mean;
  const currentNDVI = activeMetrics.ndvi;
  const ndviDeltaPct = (currentNDVI != null && baselineNDVI != null && baselineNDVI > 0)
    ? Math.round(((currentNDVI - baselineNDVI) / baselineNDVI) * 100)
    : null;
  const ndviZScore = (currentNDVI != null && baselineNDVI != null && currentBaseline?.ndvi_std && currentBaseline.ndvi_std > 0)
    ? Number(((currentNDVI - baselineNDVI) / currentBaseline.ndvi_std).toFixed(2))
    : null;

  const baselineRain = currentBaseline?.rain_mean;
  const currentRain = activeMetrics.rain;
  const rainDeltaPct = (currentRain != null && baselineRain != null && baselineRain > 0)
    ? Math.round(((currentRain - baselineRain) / baselineRain) * 100)
    : null;


  return (
    <aside className="w-full h-full flex flex-col bg-white border-l border-slate-200 text-slate-900 shadow-sm overflow-hidden select-text">
      {/* Sidebar Header & Tab Navigation */}
      <div className="border-b border-slate-200 bg-slate-50/80 px-4 pt-3 pb-0">
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500 ring-4 ring-amber-100" />
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800">
              Intelligence & Scientific Baselines
            </h2>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-100 text-amber-900 font-bold border border-amber-200">
            {selectedPeriod}
          </span>
        </div>

        {/* 4 Dedicated Tabs */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setTab("overview")}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-all ${
              tab === "overview"
                ? "border-amber-600 text-amber-700 bg-white rounded-t-md"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-100/60"
            }`}
          >
            Profile & Baselines
          </button>
          <button
            onClick={() => setTab("comparisons")}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-all ${
              tab === "comparisons"
                ? "border-amber-600 text-amber-700 bg-white rounded-t-md"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-100/60"
            }`}
          >
            Comparison Charts
          </button>
          <button
            onClick={() => setTab("rankings")}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-all ${
              tab === "rankings"
                ? "border-amber-600 text-amber-700 bg-white rounded-t-md"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-100/60"
            }`}
          >
            Tehsil Rankings
          </button>
          <button
            onClick={() => setTab("heatmap")}
            className={`px-3 py-2 text-xs font-bold border-b-2 transition-all ${
              tab === "heatmap"
                ? "border-amber-600 text-amber-700 bg-white rounded-t-md"
                : "border-transparent text-slate-500 hover:text-slate-800 hover:bg-slate-100/60"
            }`}
          >
            Heatmap & Matrix
          </button>
        </div>
      </div>

      {/* Main Tab Content Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* TAB 1: VILLAGE / REGION PROFILE & SCIENTIFIC BASELINES */}
        {tab === "overview" && (
          <div className="space-y-4 animate-fadeIn">
            {/* Village Title Banner */}
            <div className="p-3.5 rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white shadow-xs">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    {village ? `${tehsilName} tehsil · revenue village` : selectedTehsil !== "All" ? `${tehsilName} tehsil` : "District"}
                  </span>
                  <h3 className="text-base font-extrabold text-slate-900 leading-tight">
                    {villageName}
                  </h3>
                  {village?.AREA_SQKM && (
                    <span className="text-[11px] text-slate-500 font-mono">
                      Area: {Number(village.AREA_SQKM).toFixed(2)} km²
                    </span>
                  )}
                </div>

                <div className={`px-2.5 py-1 rounded-lg border text-xs font-bold shadow-xs ${sev.badge}`}>
                  {sev.label}
                </div>
              </div>
            </div>

            {/* SCIENTIFIC CLIMATOLOGICAL BASELINE & ANOMALY ASSESSMENT */}
            <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/40 space-y-3">
              <div className="flex items-center justify-between border-b border-amber-200/80 pb-2">
                <div>
                  <span className="text-xs font-extrabold text-amber-950 uppercase tracking-wider">
                    Climatological Normal & Anomaly Departure
                  </span>
                  <div className="text-[10px] text-amber-800">
                    10-Year Historical Baseline for Month {currentMonthInt} vs Observed ({selectedPeriod})
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-200/60 text-amber-900 font-bold">
                  μ ± σ Climatology
                </span>
              </div>

              {/* Baseline vs Actual Comparisons */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                {/* NDVI Baseline Anomaly */}
                <div className="p-2.5 rounded-lg border border-slate-200 bg-white shadow-2xs">
                  <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold uppercase mb-1">
                    <span>NDVI Vegetation</span>
                    <span className="font-mono text-slate-700">Baseline μ: {baselineNDVI ?? "n/a"}</span>
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-base font-black font-mono text-slate-900">
                      {currentNDVI != null ? Number(currentNDVI).toFixed(3) : "—"}
                    </span>
                    {ndviDeltaPct != null && (
                      <span className={`text-[11px] font-extrabold font-mono px-1.5 py-0.5 rounded ${
                        ndviDeltaPct < -10 ? "bg-rose-100 text-rose-800" : ndviDeltaPct > 5 ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
                      }`}>
                        {ndviDeltaPct > 0 ? `+${ndviDeltaPct}%` : `${ndviDeltaPct}%`}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1 flex justify-between">
                    <span>Z-Score Departure:</span>
                    <span className="font-mono font-bold text-amber-800">
                      {ndviZScore != null ? `${ndviZScore > 0 ? "+" : ""}${ndviZScore} σ` : "—"}
                    </span>
                  </div>
                </div>

                {/* Rainfall Baseline Anomaly */}
                <div className="p-2.5 rounded-lg border border-slate-200 bg-white shadow-2xs">
                  <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold uppercase mb-1">
                    <span>CHIRPS Rain</span>
                    <span className="font-mono text-slate-700">Baseline μ: {baselineRain ?? "n/a"} mm</span>
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-base font-black font-mono text-blue-900">
                      {currentRain != null ? `${Number(currentRain).toFixed(1)}` : "—"} <span className="text-xs font-normal">mm</span>
                    </span>
                    {rainDeltaPct != null && (
                      <span className={`text-[11px] font-extrabold font-mono px-1.5 py-0.5 rounded ${
                        rainDeltaPct < -25 ? "bg-rose-100 text-rose-800" : rainDeltaPct > 10 ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"
                      }`}>
                        {rainDeltaPct > 0 ? `+${rainDeltaPct}%` : `${rainDeltaPct}%`}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1 flex justify-between">
                    <span>Precipitation Status:</span>
                    <span className="font-semibold text-slate-800">
                      {rainDeltaPct && rainDeltaPct < -50 ? "Severe Deficit" : rainDeltaPct && rainDeltaPct < -20 ? "Deficit" : "Normal"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Situation summary, computed from the villages on screen */}
            <div className="rounded-lg border border-ink/15 bg-paper p-3 shadow-card">
              <div className="font-mono text-[10px] uppercase tracking-wider text-ink/55">
                {selectedTehsil === "All" ? "Latur district" : `${selectedTehsil} tehsil`} · {selectedPeriod}
              </div>
              {summary && summary.assessed > 0 ? (
                <p className="mt-1 text-[12px] leading-relaxed text-ink">
                  <strong>{summary.inDrought}</strong> of <strong>{summary.assessed}</strong> assessed villages are in
                  drought (D0–D4); <strong>{summary.d2plus}</strong> are severe or worse (D2–D4).
                  {summary.total > summary.assessed && (
                    <> {summary.total - summary.assessed} of {summary.total} villages have no composite score this month (cloud cover or missing inputs).</>
                  )}
                </p>
              ) : (
                <p className="mt-1 text-[12px] text-ink/70">No composite scores are available for this month.</p>
              )}
            </div>

            {/* Current rainfall condition. Long-term SPIs live in the disclosure below: they accumulate
                3-12 months of rain, change only when a new month is published, and are not weekly
                indicators, so they do not belong in the headline numbers of a near-real-time view. */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center justify-between">
                <span>Rainfall this month</span>
                <span className="text-[9px] font-mono text-slate-400">CHIRPS · monthly</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="p-2 rounded-xl border border-slate-200 bg-white shadow-2xs">
                  <div className="text-[9px] font-bold text-slate-500 uppercase">SPI-1</div>
                  <div className="text-sm font-black font-mono text-slate-900">
                    {activeMetrics.spi1 != null ? Number(activeMetrics.spi1).toFixed(2) : <span className="text-[10px] text-slate-400 font-sans">not yet published</span>}
                  </div>
                  <div className="text-[8px] text-slate-400">rain vs normal, this month</div>
                </div>
                <div className="p-2 rounded-xl border border-slate-200 bg-white shadow-2xs">
                  <div className="text-[9px] font-bold text-slate-500 uppercase">Rainfall</div>
                  <div className="text-sm font-black font-mono text-slate-900">
                    {activeMetrics.rain != null ? `${Number(activeMetrics.rain).toFixed(1)} mm` : <span className="text-[10px] text-slate-400 font-sans">not yet published</span>}
                  </div>
                  <div className="text-[8px] text-slate-400">month total</div>
                </div>
              </div>
              {activeMetrics.spi1 == null && (
                <div className="text-[10px] text-amber-800 mt-1.5 font-medium">
                  CHIRPS rainfall for {selectedPeriod} has not been published yet. Vegetation indices for this month are current.
                </div>
              )}

              <details className="mt-2 rounded-xl border border-slate-200 bg-slate-50/60 px-3 py-2">
                <summary className="cursor-pointer text-[11px] font-bold text-slate-700">
                  Long-term rainfall deficit (SPI-3, 6, 12) · updated monthly
                </summary>
                <p className="mt-1.5 text-[10px] leading-snug text-slate-600">
                  These add up rainfall over the last 3, 6 and 12 months, so they move slowly and only when a new
                  month of CHIRPS is published. They describe accumulated deficit (soil moisture, tank and
                  groundwater storage), not week-to-week change.
                </p>
                <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                  {([["SPI-3", activeMetrics.spi3, "3 months"], ["SPI-6", activeMetrics.spi6, "6 months"], ["SPI-12", activeMetrics.spi12, "12 months"]] as const).map(([lbl, v, win]) => (
                    <div key={lbl} className="p-2 rounded-lg border border-slate-200 bg-white">
                      <div className="text-[9px] font-bold text-slate-500 uppercase">{lbl}</div>
                      <div className="text-sm font-black font-mono text-slate-900">
                        {v != null ? Number(v).toFixed(2) : <span className="text-[10px] text-slate-400 font-sans">–</span>}
                      </div>
                      <div className="text-[8px] text-slate-400">window {win}</div>
                    </div>
                  ))}
                </div>
              </details>
            </div>

            {thermalMetrics && (
              <div className="grid grid-cols-3 gap-2 text-center">
                {([["LST", thermalMetrics.lst, "°C day", 1], ["TCI", thermalMetrics.tci, "temp. condition", 1], ["SMI", thermalMetrics.smi, "soil moisture", 1]] as const).map(([lbl, v, note, d]) => (
                  <div key={lbl} className="p-2 rounded-xl border border-slate-200 bg-white shadow-2xs">
                    <div className="text-[9px] font-bold text-slate-500 uppercase">{lbl}</div>
                    <div className="text-sm font-black text-slate-900 font-mono">{v != null ? Number(v).toFixed(d) : "—"}</div>
                    <div className="text-[8px] text-slate-500">{note}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Key Spectral Indices (NDVI, VHI, VCI, CDI) */}
            <div className="grid grid-cols-4 gap-2 text-center">
              <div className="p-2 rounded-xl border border-amber-200 bg-amber-50/50">
                <div className="text-[9px] font-bold text-amber-700 uppercase">CDI Score</div>
                <div className="text-sm font-black text-amber-900 font-mono">
                  {activeMetrics.cdi != null ? Number(activeMetrics.cdi).toFixed(3) : "—"}
                </div>
                <div className="text-[8px] text-amber-700">Composite</div>
              </div>

              <div className="p-2 rounded-xl border border-slate-200 bg-white shadow-2xs">
                <div className="text-[9px] font-bold text-slate-500 uppercase">NDVI</div>
                <div className="text-sm font-black text-slate-900 font-mono">
                  {activeMetrics.ndvi != null ? Number(activeMetrics.ndvi).toFixed(3) : "—"}
                </div>
                <div className="text-[8px] text-emerald-600">Greenness</div>
              </div>

              <div className="p-2 rounded-xl border border-slate-200 bg-white shadow-2xs">
                <div className="text-[9px] font-bold text-slate-500 uppercase">VHI</div>
                <div className="text-sm font-black text-slate-900 font-mono">
                  {activeMetrics.vhi != null ? Number(activeMetrics.vhi).toFixed(1) : "—"}
                </div>
                <div className="text-[8px] text-slate-500">Health</div>
              </div>

              <div className="p-2 rounded-xl border border-slate-200 bg-white shadow-2xs">
                <div className="text-[9px] font-bold text-slate-500 uppercase">VCI</div>
                <div className="text-sm font-black text-slate-900 font-mono">
                  {activeMetrics.vci != null ? Number(activeMetrics.vci).toFixed(1) : "—"}
                </div>
                <div className="text-[8px] text-slate-500">Condition</div>
              </div>
            </div>

            {/* Actionable Agricultural Directive */}
            <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/70">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-amber-900 font-extrabold text-xs uppercase tracking-wider">
                  Agronomic Advisory · Tier {cdiClass}
                </span>
              </div>
              <p className="text-xs text-amber-950 leading-relaxed font-medium">
                {getAdvisory(cdiClass)}
              </p>
            </div>
          </div>
        )}

        {/* TAB 2: COMPARISON CHARTS (MULTI-SCALE SPI, TRAJECTORY, & CLIMATOLOGY ENVELOPE) */}
        {tab === "comparisons" && (
          <div className="space-y-4 animate-fadeIn">
            {/* Scope Toggle (Village vs District) */}
            <div className="flex items-center justify-between bg-slate-100 p-1 rounded-xl">
              <button
                onClick={() => setTsScope("village")}
                disabled={!village}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  tsScope === "village" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-800"
                } ${!village ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                {village ? `${villageName} Series` : "Select a Village"}
              </button>
              <button
                onClick={() => setTsScope("district")}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all ${
                  tsScope === "district" ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Latur District 10-Yr Aggregate
              </button>
            </div>

            {/* Comparison Mode Sub-Tabs */}
            <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-xl border border-slate-200">
              <button
                onClick={() => setChartSubMode("spi_multiscale")}
                className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition-all ${
                  chartSubMode === "spi_multiscale" ? "bg-amber-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                SPI 1, 3, 6, 12 Comparison
              </button>
              <button
                onClick={() => setChartSubMode("climatology_envelope")}
                className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition-all ${
                  chartSubMode === "climatology_envelope" ? "bg-amber-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                Baseline Climatology
              </button>
              <button
                onClick={() => setChartSubMode("cdi_trajectory")}
                className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition-all ${
                  chartSubMode === "cdi_trajectory" ? "bg-amber-600 text-white shadow-xs" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                CDI vs Rain
              </button>
            </div>

            {/* COMPARISON CHART 1: MULTI-SCALE SPI (SPI-1, SPI-3, SPI-6, SPI-12) */}
            {chartSubMode === "spi_multiscale" && (
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-800">
                      Multi-Scale Standardized Precipitation Index (2016–2026)
                    </span>
                    <p className="text-[10px] text-slate-500">
                      Synchronized comparison of Meteorological (SPI-1), Agricultural (SPI-3), and Hydrological (SPI-6/12) drought cycles.
                    </p>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">{chartData.length} pts</span>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 9 }} interval={Math.floor(chartData.length / 8)} />
                      <YAxis domain={[-3, 3]} tick={{ fill: "#64748b", fontSize: 9 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", fontSize: "11px", borderRadius: "8px" }} />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      {/* WMO Drought Reference Thresholds */}
                      <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} label={{ value: "Normal (0)", fill: "#94a3b8", fontSize: 9 }} />
                      <ReferenceLine y={-1.0} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: "Mod. Drought (-1.0)", fill: "#f59e0b", fontSize: 9 }} />
                      <ReferenceLine y={-1.5} stroke="#dc2626" strokeDasharray="3 3" label={{ value: "Sev. Drought (-1.5)", fill: "#dc2626", fontSize: 9 }} />
                      <ReferenceLine y={-2.0} stroke="#7f1d1d" strokeDasharray="3 3" label={{ value: "Extr. Drought (-2.0)", fill: "#7f1d1d", fontSize: 9 }} />

                      <Line type="monotone" dataKey="spi1" stroke="#06b6d4" strokeWidth={1.2} dot={false} name="SPI-1 (1-Mo)" />
                      <Line type="monotone" dataKey="spi3" stroke="#2563eb" strokeWidth={2.0} dot={false} name="SPI-3 (3-Mo)" />
                      <Line type="monotone" dataKey="spi6" stroke="#4f46e5" strokeWidth={1.5} dot={false} name="SPI-6 (6-Mo)" />
                      <Line type="monotone" dataKey="spi12" stroke="#9333ea" strokeWidth={1.8} dot={false} strokeDasharray="2 2" name="SPI-12 (Annual)" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* COMPARISON CHART 2: CLIMATOLOGICAL BASELINE ENVELOPE (Observed vs 10-Yr Normal) */}
            {chartSubMode === "climatology_envelope" && (
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-slate-800">
                      Annual Climatological Cycle vs 10-Year Normal
                    </span>
                    <p className="text-[10px] text-slate-500">
                      Comparing the 12-month expected vegetation greenness baseline against observed values.
                    </p>
                  </div>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={climatologyEnvelope} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} />
                      <YAxis domain={[0, 0.7]} tick={{ fill: "#64748b", fontSize: 10 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", fontSize: "11px", borderRadius: "8px" }} />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      <Line type="monotone" dataKey="normal_ndvi" stroke="#94a3b8" strokeWidth={2.5} strokeDasharray="4 4" dot={true} name="10-Yr Normal Baseline (μ)" />
                      <Line type="monotone" dataKey="observed_ndvi" stroke="#059669" strokeWidth={2.5} dot={{ r: 4, fill: "#059669" }} name="Observed NDVI" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* COMPARISON CHART 3: CDI VS RAINFALL & VEGETATION */}
            {chartSubMode === "cdi_trajectory" && (
              <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">
                    Composite Drought Score (CDI) vs Precipitation
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">{chartData.length} periods</span>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 9 }} interval={Math.floor(chartData.length / 8)} />
                      <YAxis yAxisId="cdi" domain={[0, 1]} tick={{ fill: "#d97706", fontSize: 9 }} />
                      <YAxis yAxisId="rain" orientation="right" tick={{ fill: "#3b82f6", fontSize: 9 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", fontSize: "11px", borderRadius: "8px" }} />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      <ReferenceLine yAxisId="cdi" y={0.5} stroke="#ef4444" strokeDasharray="3 3" label={{ value: "D2 Severe", fill: "#ef4444", fontSize: 9 }} />
                      <Bar yAxisId="rain" dataKey="rain" fill="#93c5fd" name="Rain (mm)" opacity={0.7} />
                      <Line yAxisId="cdi" type="monotone" dataKey="cdi" stroke="#d97706" strokeWidth={2.2} dot={false} name="CDI Score" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: TEHSIL RANKINGS & COMPARISON */}
        {tab === "rankings" && (
          <div className="space-y-4 animate-fadeIn">
            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
              <div className="text-xs font-bold text-slate-800 mb-2">
                Tehsil Drought Stress Ranking ({selectedPeriod})
              </div>
              <div className="h-56 w-full">
                {ranking ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={ranking}
                      layout="vertical"
                      margin={{ top: 5, right: 20, left: 35, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                      <XAxis type="number" domain={[0, 1]} tick={{ fill: "#64748b", fontSize: 10 }} />
                      <YAxis dataKey="tehsil" type="category" tick={{ fill: "#0f172a", fontSize: 10, fontWeight: 600 }} />
                      <Tooltip
                        formatter={(val: any) => [`${Number(val).toFixed(3)} CDI`, "Average Score"]}
                        contentStyle={{ backgroundColor: "#ffffff", borderColor: "#e2e8f0", fontSize: "11px" }}
                      />
                      <Bar dataKey="avg_cdi" radius={[0, 4, 4, 0]}>
                        {ranking.map((entry: any, index: number) => {
                          const color = colorForValue(entry.avg_cdi, "cdi");
                          return <Cell key={`cell-${index}`} fill={color} />;
                        })}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-full flex items-center justify-center text-xs text-slate-400">
                    Loading tehsil rankings...
                  </div>
                )}
              </div>
            </div>

            {/* Tehsil Comparison Table */}
            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs overflow-x-auto">
              <table className="w-full text-[11px] text-left">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-1.5 font-bold">Tehsil</th>
                    <th className="py-1.5 font-bold">Villages</th>
                    <th className="py-1.5 font-bold">Avg CDI</th>
                    <th className="py-1.5 font-bold">Drought %</th>
                    <th className="py-1.5 font-bold">D2+</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ranking?.map((t: any) => (
                    <tr
                      key={t.tehsil}
                      onClick={() => onSelectTehsil(t.tehsil)}
                      className={`cursor-pointer hover:bg-amber-50/60 transition-colors ${
                        selectedTehsil === t.tehsil ? "bg-amber-100/50 font-bold" : ""
                      }`}
                    >
                      <td className="py-2 text-slate-900 font-semibold">{t.tehsil}</td>
                      <td className="py-2 font-mono text-slate-600">{t.assessed}/{t.villages}</td>
                      <td className="py-2 font-mono font-bold text-amber-700">{t.avg_cdi.toFixed(3)}</td>
                      <td className="py-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          t.drought_pct > 75 ? "bg-rose-100 text-rose-800" : t.drought_pct > 50 ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"
                        }`}>
                          {t.drought_pct.toFixed(0)}%
                        </span>
                      </td>
                      <td className="py-2 font-mono text-rose-700 font-bold">{t.d2_plus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: HEATMAP & CORRELATION */}
        {tab === "heatmap" && (
          <div className="space-y-4 animate-fadeIn">
            {/* Year x Month Drought Heatmap Table */}
            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-slate-800">
                  CDI Intensity Heatmap Matrix (2016–2026)
                </span>
                <span className="text-[10px] text-slate-500 font-mono">0.0 (pale) → 1.0 (dark red), CDI classes</span>
              </div>

              <div className="overflow-x-auto">
                <table className="border-separate border-spacing-0.5 text-[10px] w-full">
                  <thead>
                    <tr>
                      <th className="w-8 text-left text-slate-400 font-semibold">Yr</th>
                      {["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"].map((m) => (
                        <th key={m} className="w-6 py-1 text-center font-normal text-slate-400">
                          {m}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from(new Set(districtTs.map((d: any) => Number(String(d.date).slice(0, 4))))).sort().map((y) => (
                      <tr key={y}>
                        <th className="pr-1 text-right font-mono font-bold text-slate-500">{y}</th>
                        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
                          const dateKey = `${y}-${String(m).padStart(2, "0")}`;
                          const match = districtTs.find((d: any) => d.date === dateKey);
                          const val = match?.composite_drought_score ?? null;

                          // Same palette and thresholds as the map legend (lib/classify.ts).
                          const bg = val != null ? colorForValue(val, "cdi") : "#f1f5f9";
                          const text = val == null ? "#94a3b8" : val >= 0.65 ? "#ffffff" : "#1d2b25";

                          return (
                            <td
                              key={m}
                              style={{ backgroundColor: bg, color: text }}
                              className="h-5 text-center font-mono text-[9px] rounded-xs font-semibold"
                              title={`${dateKey}: ${val != null ? val.toFixed(2) : "No data"}`}
                            >
                              {val != null ? val.toFixed(1) : "—"}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 8x8 Correlation Matrix */}
            <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs">
              <div className="text-xs font-bold text-slate-800 mb-1">
                Index Pairwise Correlation Matrix
              </div>
              <p className="text-[10px] text-slate-500 mb-2">
                Calculated across 94,472 Latur observations (2016–2026). Strong negative correlation between VHI/SPI-3 and CDI confirms physical drought synchronization.
              </p>

              {(() => {
                const cm = analytics?.correlation_matrix;
                if (!cm) return null;

                if (Array.isArray(cm) && cm.length > 0) {
                  const headers = Object.keys(cm[0]).filter((k) => k !== "index");
                  return (
                    <div className="overflow-x-auto">
                      <table className="border-collapse text-[10px] w-full text-center font-mono">
                        <thead>
                          <tr className="border-b border-slate-200 text-slate-500">
                            <th className="p-1 text-left">Index</th>
                            {headers.map((h) => (
                              <th key={h} className="p-1 font-semibold">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {cm.map((row: any, rI: number) => (
                            <tr key={row.index || rI} className="border-b border-slate-100">
                              <td className="p-1 text-left font-bold text-slate-700">{row.index}</td>
                              {headers.map((h) => {
                                const cellVal = row[h];
                                if (cellVal == null) return <td key={h} className="p-1 text-slate-300">—</td>;
                                let bg = "#ffffff";
                                let textColor = "#0f172a";
                                if (cellVal < -0.5) { bg = "#fee2e2"; textColor = "#991b1b"; }
                                else if (cellVal < 0) { bg = "#ffedd5"; textColor = "#9a3412"; }
                                else if (cellVal > 0.5) { bg = "#dcfce7"; textColor = "#166534"; }
                                else if (cellVal > 0) { bg = "#f0fdf4"; textColor = "#15803d"; }
                                return (
                                  <td
                                    key={h}
                                    style={{ backgroundColor: bg, color: textColor }}
                                    className="p-1 font-semibold"
                                  >
                                    {Number(cellVal).toFixed(2)}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                }

                if (cm.indices && cm.matrix) {
                  return (
                    <div className="overflow-x-auto">
                      <table className="border-collapse text-[10px] w-full text-center font-mono">
                        <thead>
                          <tr className="border-b border-slate-200 text-slate-500">
                            <th className="p-1 text-left">Index</th>
                            {cm.indices.map((idx: string) => (
                              <th key={idx} className="p-1 font-semibold">{idx}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {cm.indices.map((rowIdx: string, rI: number) => (
                            <tr key={rowIdx} className="border-b border-slate-100">
                              <td className="p-1 text-left font-bold text-slate-700">{rowIdx}</td>
                              {(cm.matrix[rI] || []).map((cellVal: number, cI: number) => {
                                let bg = "#ffffff";
                                let textColor = "#0f172a";
                                if (cellVal < -0.5) { bg = "#fee2e2"; textColor = "#991b1b"; }
                                else if (cellVal < 0) { bg = "#ffedd5"; textColor = "#9a3412"; }
                                else if (cellVal > 0.5) { bg = "#dcfce7"; textColor = "#166534"; }
                                else if (cellVal > 0) { bg = "#f0fdf4"; textColor = "#15803d"; }
                                return (
                                  <td
                                    key={cI}
                                    style={{ backgroundColor: bg, color: textColor }}
                                    className="p-1 font-semibold"
                                  >
                                    {cellVal != null ? Number(cellVal).toFixed(2) : "—"}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                }

                return null;
              })()}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
