"use client";

import dynamic from "next/dynamic";
import { useEffect, useState, useMemo } from "react";
import type { MetricName } from "@/components/map/LaturMap";
import { PermanentSidebar } from "@/components/panels/PermanentSidebar";
import { MonthlyTimelineScrubber } from "@/components/map/MonthlyTimelineScrubber";
import type { VillageProperties } from "@/components/panels/VillageIntelligenceDrawer";

const LaturMap = dynamic(() => import("@/components/map/LaturMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-slate-50 text-slate-500 text-sm">
      <div className="flex flex-col items-center gap-2">
        <div className="w-8 h-8 border-2 border-amber-600 border-t-transparent rounded-full animate-spin" />
        <span className="font-semibold text-slate-700">Initializing Latur Google Terrain Map Engine...</span>
      </div>
    </div>
  ),
});

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

const METRICS: { id: MetricName; label: string; desc: string }[] = [
  { id: "cdi", label: "CDI Composite", desc: "Multi-Index Severity (0..1)" },
  { id: "ndvi", label: "NDVI", desc: "Normalized Difference Veg" },
  { id: "evi", label: "EVI", desc: "Enhanced Vegetation Index" },
  { id: "vhi", label: "VHI", desc: "Vegetation Health Index" },
  { id: "vci", label: "VCI", desc: "Condition Index (0..100)" },
  { id: "spi1", label: "SPI-1", desc: "1-Mo Meteorological" },
  { id: "spi3", label: "SPI-3", desc: "3-Mo Agricultural" },
  { id: "spi6", label: "SPI-6", desc: "6-Mo Hydrological" },
  { id: "spi12", label: "SPI-12", desc: "12-Mo Deep Ground" },
  { id: "rain", label: "Rainfall", desc: "CHIRPS Precipitation (mm)" },
];

const MONTHS = [
  { id: "01", label: "Jan" },
  { id: "02", label: "Feb" },
  { id: "03", label: "Mar" },
  { id: "04", label: "Apr" },
  { id: "05", label: "May" },
  { id: "06", label: "Jun" },
  { id: "07", label: "Jul" },
  { id: "08", label: "Aug" },
  { id: "09", label: "Sep" },
  { id: "10", label: "Oct" },
  { id: "11", label: "Nov" },
  { id: "12", label: "Dec" },
];

export default function HomePage() {
  const [metric, setMetric] = useState<MetricName>("cdi");
  const [tehsil, setTehsil] = useState<string>("All");
  const [selectedVillageName, setSelectedVillageName] = useState<string>("");
  const [selectedVillage, setSelectedVillage] = useState<VillageProperties | null>(null);
  const [villagesByTehsil, setVillagesByTehsil] = useState<Record<string, string[]>>({});
  const [periods, setPeriods] = useState<string[]>([]);
  const [currentPeriod, setCurrentPeriod] = useState<string>("2026-10");
  const [year, setYear] = useState<number>(2026);
  const [month, setMonth] = useState<string>("10");

  const [stats, setStats] = useState<{
    total: number;
    droughtCount: number;
    d2PlusCount: number;
    avgCdi: number;
  }>({ total: 0, droughtCount: 0, d2PlusCount: 0, avgCdi: 0 });

  const [timeseriesCache, setTimeseriesCache] = useState<Record<string, any[]> | null>(null);

  // Load Tehsil village registry via API (reads fresh data, not stale static files)
  useEffect(() => {
    fetch("/api/v1/tehsil-analytics")
      .then((res) => res.json())
      .then((data) => {
        // tehsil_analytics.json has tehsil_ranking, not villages_by_tehsil
        // Fallback to static file for village registry mapping
        fetch("/data/villages_by_tehsil.json")
          .then((res2) => res2.json())
          .then((data2) => setVillagesByTehsil(data2))
          .catch(() => null);
      })
      .catch(() => {
        fetch("/data/villages_by_tehsil.json")
          .then((res2) => res2.json())
          .then((data2) => setVillagesByTehsil(data2))
          .catch(() => null);
      });

    fetch("/data/village_timeseries.json")
      .then((res) => res.json())
      .then((data) => setTimeseriesCache(data))
      .catch(() => null);
  }, []);

  // Load continuous observation periods from district timeseries via API
  useEffect(() => {
    fetch("/api/v1/district-timeseries")
      .then((r) => r.json())
      .then((d) => {
        const pList = (d.series || []).map((s: any) => s.date).filter(Boolean);
        if (pList.length > 0) {
          setPeriods(pList);
        }
      })
      .catch(() => {
        // Fallback to static file
        fetch("/data/district_monthly.json")
          .then((r2) => r2.json())
          .then((d2) => {
            const pList = (d2.series || []).map((s: any) => s.date).filter(Boolean);
            if (pList.length > 0) setPeriods(pList);
          })
          .catch((e) => console.error("Error loading periods:", e));
      });
  }, []);

  // Dynamically compute real-time statistics whenever currentPeriod, tehsil, or timeseriesCache changes
  useEffect(() => {
    if (!timeseriesCache) {
      fetch("/api/v1/villages")
        .then((res) => res.json())
        .then((gj) => {
          const features = gj.features || [];
          const total = features.length;
          let droughtCount = 0;
          let d2PlusCount = 0;
          let cdiSum = 0;
          let cdiCount = 0;

          for (const f of features) {
            const p = f.properties || {};
            const cdi = p.CDI;
            const cls = p.CDI_class || p.class || "";
            if (cdi != null) {
              cdiSum += cdi;
              cdiCount++;
              if (cdi >= 0.20 || (cls && cls !== "None" && cls !== "ND")) {
                droughtCount++;
              }
              if (["D2", "D3", "D4"].includes(cls)) {
                d2PlusCount++;
              }
            }
          }

          setStats({
            total,
            droughtCount,
            d2PlusCount,
            avgCdi: cdiCount > 0 ? cdiSum / cdiCount : 0,
          });
        })
        .catch(() => null);
      return;
    }

    let total = 0;
    let droughtCount = 0;
    let d2PlusCount = 0;
    let cdiSum = 0;
    let cdiCount = 0;

    for (const [key, pts] of Object.entries(timeseriesCache)) {
      if (!Array.isArray(pts)) continue;
      if (tehsil !== "All") {
        const [t] = key.split("::");
        if (t.toLowerCase() !== tehsil.toLowerCase()) continue;
      }
      total++;
      const match = pts.find((x: any) => (x.p || x.date) === currentPeriod);
      if (match) {
        const cdi = match.cdi;
        const cls = match.cls || "";
        if (cdi != null && !isNaN(cdi)) {
          cdiSum += cdi;
          cdiCount++;
          if (cdi >= 0.20 || (cls && cls !== "None" && cls !== "ND")) {
            droughtCount++;
          }
          if (["D2", "D3", "D4"].includes(cls)) {
            d2PlusCount++;
          }
        }
      }
    }

    setStats({
      total,
      droughtCount,
      d2PlusCount,
      avgCdi: cdiCount > 0 ? cdiSum / cdiCount : 0,
    });
  }, [currentPeriod, tehsil, timeseriesCache]);

  // Keep selected village in sync with currentPeriod
  useEffect(() => {
    if (!selectedVillageName || !timeseriesCache) return;
    const keyMatch = Object.entries(timeseriesCache).find(([k, pts]) => {
      if (!Array.isArray(pts)) return false;
      const parts = k.split("::");
      if (parts.length < 2) return false;
      return parts[1].toLowerCase() === selectedVillageName.toLowerCase();
    });
    if (keyMatch) {
      const [key, pts] = keyMatch;
      const [tName] = key.split("::");
      if (Array.isArray(pts)) {
        const match = pts.find((x: any) => (x.p || x.date) === currentPeriod);
        if (match) {
          setSelectedVillage((prev) => ({
            ...(prev || {}),
            ...match,
            village: selectedVillageName,
            tehsil: prev?.tehsil || tName,
            CDI: match.cdi,
            CDI_class: match.cls,
            NDVI: match.ndvi,
            VHI: match.vhi,
            VCI: match.vci,
            Rain_mm: match.rain,
            SPI1: match.spi1,
            SPI3: match.spi3,
            SPI6: match.spi6,
            SPI12: match.spi12,
          }));
        }
      }
    }
  }, [currentPeriod, selectedVillageName, timeseriesCache]);

  // Filter available villages based on selected Tehsil
  const availableVillages = useMemo(() => {
    if (tehsil !== "All" && villagesByTehsil[tehsil]) {
      return villagesByTehsil[tehsil];
    }
    const all: string[] = [];
    for (const vList of Object.values(villagesByTehsil)) {
      all.push(...vList);
    }
    return Array.from(new Set(all)).sort();
  }, [tehsil, villagesByTehsil]);

  // Handler when user selects a village from the top dropdown or search
  const handleSelectVillageByName = (vName: string) => {
    setSelectedVillageName(vName);
    if (!vName) {
      setSelectedVillage(null);
      return;
    }
    fetch("/data/latur_villages_latest.geojson")
      .then((res) => res.json())
      .then((gj) => {
        const match = (gj.features || []).find((f: any) => {
          const p = f.properties || {};
          const name = p.village || p.VILLAGE || p.name || "";
          return name.toLowerCase() === vName.toLowerCase();
        });
        if (match) {
          let props = match.properties;
          if (timeseriesCache) {
            const t = (props.tehsil || props.TEHSIL || "").trim().toLowerCase();
            const v = (props.village || props.VILLAGE || props.name || "").trim().toLowerCase();
            const key = `${t}::${v}`;
            const pts = timeseriesCache[key];
            if (Array.isArray(pts)) {
              const cur = pts.find((x: any) => (x.p || x.date) === currentPeriod);
              if (cur) {
                props = {
                  ...props,
                  ...cur,
                  CDI: cur.cdi,
                  CDI_class: cur.cls,
                  NDVI: cur.ndvi,
                  VHI: cur.vhi,
                  VCI: cur.vci,
                  Rain_mm: cur.rain,
                  SPI1: cur.spi1,
                  SPI3: cur.spi3,
                  SPI6: cur.spi6,
                  SPI12: cur.spi12,
                };
              }
            }
          }
          setSelectedVillage(props);
        }
      })
      .catch(() => null);
  };

  // Synchronize period from timeline scrubber
  const handlePeriodChange = (p: string) => {
    setCurrentPeriod(p);
    const [y, m] = p.split("-");
    if (y && m) {
      setYear(parseInt(y, 10));
      setMonth(m);
    }
  };

  // Synchronize period from Year & Month selects
  const handleYearMonthSelect = (newYear: number, newMonth: string) => {
    setYear(newYear);
    setMonth(newMonth);
    const candidate = `${newYear}-${newMonth}`;
    if (periods.includes(candidate)) {
      setCurrentPeriod(candidate);
    } else {
      // Find nearest period in the same year or fallback
      const match = periods.find((p) => p.startsWith(String(newYear))) || candidate;
      setCurrentPeriod(match);
    }
  };

  // Reset to latest observation period (2026-10)
  const setLatestPeriod = () => {
    setYear(2026);
    setMonth("10");
    setCurrentPeriod("2026-10");
  };

  return (
    <div className="flex flex-col h-[calc(100vh-57px)] overflow-hidden bg-slate-50 text-slate-900">
      {/* Executive Command Controls Header — Crisp White with Gold Accents */}
      <header className="px-5 py-2.5 border-b border-slate-200 bg-white shadow-xs flex flex-wrap items-center justify-between gap-3 z-20">
        {/* Left Side: System State & Old Dashboard Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 pr-2 border-r border-slate-200">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 leading-none">
                Live Sentinel-2 · GEE Operational
              </div>
              <div className="text-xs font-bold text-slate-900 leading-tight">
                Latur District Observatory
              </div>
            </div>
          </div>

          {/* 1. Tehsil Selector */}
          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Tehsil:</span>
            <select
              value={tehsil}
              onChange={(e) => {
                setTehsil(e.target.value);
                setSelectedVillageName("");
                setSelectedVillage(null);
              }}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              {TEHSILS.map((t) => (
                <option key={t} value={t}>
                  {t === "All" ? "All Latur (10 Tehsils)" : `${t} Tehsil`}
                </option>
              ))}
            </select>
          </div>

          {/* 2. Village Selector Dropdown */}
          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Village:</span>
            <select
              value={selectedVillageName}
              onChange={(e) => handleSelectVillageByName(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-800 focus:outline-none max-w-[170px] truncate cursor-pointer"
            >
              <option value="">— Select Village ({availableVillages.length}) —</option>
              {availableVillages.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          {/* 3. Metric Dropdown with full SPI 1, 3, 6, 12 Suite */}
          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Index:</span>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value as MetricName)}
              className="bg-transparent text-xs font-bold text-amber-700 focus:outline-none cursor-pointer"
            >
              {METRICS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label} ({m.desc})
                </option>
              ))}
            </select>
          </div>

          {/* 4. Year & Month Timeline Controls */}
          <div className="flex items-center gap-2 bg-slate-50 px-2.5 py-1 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-500 uppercase">Period:</span>
            <select
              value={year}
              onChange={(e) => handleYearMonthSelect(Number(e.target.value), month)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              {[2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>

            <select
              value={month}
              onChange={(e) => handleYearMonthSelect(year, e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
            >
              {MONTHS.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>

            {/* Quick Set Latest Button in Gold Accent */}
            <button
              onClick={setLatestPeriod}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition-all ${
                currentPeriod === "2026-10"
                  ? "bg-amber-600 text-white shadow-xs"
                  : "bg-amber-100 text-amber-800 hover:bg-amber-200"
              }`}
              title="Jump to latest operational observation (2026-10)"
            >
              Latest (2026-10)
            </button>
          </div>
        </div>

        {/* Right Side: High-Level Executive KPI Chips */}
        <div className="hidden 2xl:flex items-center gap-2">
          <div className="px-3 py-1 bg-white rounded-lg border border-slate-200 shadow-2xs text-right">
            <div className="text-[9px] text-slate-500 uppercase font-bold">Monitored Villages</div>
            <div className="text-xs font-extrabold font-mono text-slate-900">{stats.total} Villages</div>
          </div>
          <div className="px-3 py-1 bg-amber-50 rounded-lg border border-amber-200 shadow-2xs text-right">
            <div className="text-[9px] text-amber-800 uppercase font-bold">In Drought (D0-D4)</div>
            <div className="text-xs font-extrabold font-mono text-amber-900">
              {stats.droughtCount} <span className="text-[10px] font-semibold text-amber-700">({Math.round((stats.droughtCount / stats.total) * 100)}%)</span>
            </div>
          </div>
          <div className="px-3 py-1 bg-rose-50 rounded-lg border border-rose-200 shadow-2xs text-right">
            <div className="text-[9px] text-rose-800 uppercase font-bold">Critical (D2-D4)</div>
            <div className="text-xs font-extrabold font-mono text-rose-900">{stats.d2PlusCount} Villages</div>
          </div>
          <div className="px-3 py-1 bg-amber-500 rounded-lg shadow-xs text-right text-white">
            <div className="text-[9px] uppercase font-bold text-amber-100">District CDI</div>
            <div className="text-xs font-extrabold font-mono">{stats.avgCdi.toFixed(3)}</div>
          </div>
        </div>
      </header>

      {/* Main Split Layout: Map on the Left (62%) + Permanent Dedicated Sidebar on the Right (38%) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Section: Interactive Google Terrain Choropleth Map with Monthly Timeline Scrubber */}
        <main className="flex-1 h-full relative flex flex-col">
          <div className="flex-1 relative">
            <LaturMap
              metric={metric}
              tehsil={tehsil}
              selectedVillageName={selectedVillageName}
              currentPeriod={currentPeriod}
              timeseriesCache={timeseriesCache}
              onSelectVillage={(props) => {
                setSelectedVillage(props);
                const name = props.village || props.VILLAGE || props.name || "";
                setSelectedVillageName(name);
              }}
            />

            {/* Continuous Monthly Historical Timeline Scrubber Overlay */}
            {periods.length > 0 && (
              <div className="absolute bottom-5 left-4 right-4 z-[950] max-w-2xl mx-auto">
                <MonthlyTimelineScrubber
                  periods={periods}
                  currentPeriod={currentPeriod}
                  onPeriodChange={handlePeriodChange}
                />
              </div>
            )}
          </div>
        </main>

        {/* Right Section: PERMANENT DEDICATED SIDEBAR (Never collapses) */}
        <div className="w-[450px] xl:w-[490px] 2xl:w-[530px] h-full flex-shrink-0">
          <PermanentSidebar
            village={selectedVillage}
            selectedTehsil={tehsil}
            selectedPeriod={currentPeriod}
            onSelectTehsil={(t) => {
              setTehsil(t);
              setSelectedVillageName("");
              setSelectedVillage(null);
            }}
            onSelectVillageByName={handleSelectVillageByName}
            stats={stats}
          />
        </div>
      </div>
    </div>
  );
}
