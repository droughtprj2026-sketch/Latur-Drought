"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";
import { YearSlider } from "@/components/ui/YearSlider";
import { TehsilSelector, type TehsilName } from "@/components/ui/TehsilSelector";
import { VillageSelector } from "@/components/ui/VillageSelector";
import { DroughtStatusCard } from "@/components/panels/DroughtStatusCard";
import { IndicatorCards } from "@/components/panels/IndicatorCards";
import { SentinelPanel } from "@/components/panels/SentinelPanel";
import { ChirpsPanel } from "@/components/panels/ChirpsPanel";
import { SPIChart } from "@/components/charts/SPIChart";
import { getManifest, getMaster, type Manifest, type MasterRow } from "@/lib/api";
import { codeForCDI, D_CODES } from "@/lib/classify";
import { useLocale } from "@/components/i18n/LocaleProvider";

const LaturMap = dynamic(() => import("@/components/map/LaturMap"), {
  ssr: false,
  loading: () => (
    <div className="h-[520px] w-full animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
  ),
});

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Summary row: how many villages are in each drought class for the latest period. */
function DroughtSummary({ tehsil, village }: { tehsil: string; village: string }) {
  const { t } = useLocale();
  const [rows, setRows] = useState<MasterRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params: any = { tehsil };
    if (village) params.village = village;
    getMaster(params).then((r) => {
      setRows(r);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [tehsil, village]);

  if (loading) return null;

  // Latest period per village
  const latestByVillage = new Map<string, MasterRow>();
  for (const row of rows) {
    if (row.village === "") continue; // skip tehsil-level rows
    const period = row.observation_period;
    const existing = latestByVillage.get(row.village);
    if (!existing || period > existing.observation_period) {
      latestByVillage.set(row.village, row);
    }
  }

  const total = latestByVillage.size;
  let droughtCount = 0;
  const classCounts: Record<string, number> = {};
  for (const row of latestByVillage.values()) {
    const cls = row.composite_drought_class || "None";
    classCounts[cls] = (classCounts[cls] || 0) + 1;
    if (cls && cls !== "None" && cls !== "ND") droughtCount++;
  }

  const pct = total > 0 ? Math.round((droughtCount / total) * 100) : 0;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {t("summary.title")}
        </h3>
        <span className="text-[10px] text-slate-500">{total} villages</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div className="rounded bg-slate-50 p-3 dark:bg-slate-800">
          <div className="text-slate-500">{t("summary.drought_villages")}</div>
          <div className="font-bold text-rose-600">{droughtCount}</div>
          <div className="text-[10px] text-slate-500">{pct}% of total</div>
        </div>
        <div className="rounded bg-green-50 p-3 dark:bg-green-900/20">
          <div className="text-slate-500">{t("summary.normal_villages")}</div>
          <div className="font-bold text-green-600">{total - droughtCount}</div>
          <div className="text-[10px] text-slate-500">{total > 0 ? Math.round(((total - droughtCount) / total) * 100) : 0}% of total</div>
        </div>
        <div className="rounded bg-amber-50 p-3 dark:bg-amber-900/20">
          <div className="text-slate-500">{t("summary.d0_d1")}</div>
          <div className="font-bold text-amber-600">
            {(classCounts["D0"] || 0) + (classCounts["D1"] || 0)}
          </div>
        </div>
        <div className="rounded bg-rose-50 p-3 dark:bg-rose-900/20">
          <div className="text-slate-500">{t("summary.d2_plus")}</div>
          <div className="font-bold text-rose-600">
            {(classCounts["D2"] || 0) + (classCounts["D3"] || 0) + (classCounts["D4"] || 0)}
          </div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 md:grid-cols-6 gap-2">
        {D_CODES.map((code) => {
          const cnt = classCounts[code] || 0;
          const color = code === "None" ? "#FFFFFF" :
            code === "D0" ? "#FFFF00" :
            code === "D1" ? "#FCD37F" :
            code === "D2" ? "#FFAA00" :
            code === "D3" ? "#E60000" :
            "#730000";
          return (
            <div key={code} className="rounded bg-slate-100 p-2 dark:bg-slate-800 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full" style={{ background: color }}></span>
              <span className="text-[10px]">{code}</span>
              <span className="ml-auto text-[10px] font-mono">{cnt}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function HomePage() {
  const { t } = useLocale();
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [index, setIndex] = useState<IndexName>("cdi");
  const [year, setYear] = useState<number>(2026);
  const [month, setMonth] = useState<number>(9);
  const [tehsil, setTehsil] = useState<TehsilName>("Latur");
  const [village, setVillage] = useState<string>("");
  const [latest, setLatest] = useState(false);

  useEffect(() => {
    getManifest().then((m) => {
      setManifest(m);
      if (m.years.length) setYear(m.years[m.years.length - 1]);
    }).catch(() => undefined);
  }, []);

  const years = manifest?.years?.length ? manifest.years
    : Array.from({ length: 11 }, (_, i) => 2016 + i);
  const available: IndexName[] = manifest
    ? (Object.keys(manifest.indices) as IndexName[])
    : ["ndvi", "spi3", "vci", "vhi", "evi", "pci", "cdi", "cdi_class"];
  const effectiveTehsil = tehsil === "All" ? "Latur" : tehsil;

  return (
    <div className="space-y-6">
      <DroughtStatusCard tehsil={effectiveTehsil} village={village} />
      <DroughtSummary tehsil={effectiveTehsil} village={village} />

      {/* Controls strip */}
      <div className="grid grid-cols-1 gap-4 rounded-lg border border-slate-200
                      bg-white p-4 dark:border-slate-800 dark:bg-slate-900
                      md:grid-cols-6">
        <TehsilSelector value={tehsil} onChange={(t) => { setTehsil(t); setVillage(""); }} />
        <VillageSelector tehsil={tehsil} value={village} onChange={setVillage} />
        <IndexDropdown value={index} onChange={setIndex} available={available} />
        <div className={latest ? "opacity-40 pointer-events-none" : ""}>
          <YearSlider years={years} value={year} onChange={setYear} />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500">{t("controls.month")}</label>
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))}
                  disabled={latest}
                  className="mt-1 w-full rounded border border-slate-300 bg-transparent
                             px-2 py-1.5 text-sm dark:border-slate-700">
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
        </div>
        <label className="flex items-end gap-1 text-xs text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={latest} onChange={(e) => setLatest(e.target.checked)}
                 className="accent-blue-600" />
          {t("controls.latest")}
        </label>
      </div>

      <IndicatorCards tehsil={effectiveTehsil} village={village} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <div className="h-[560px] overflow-hidden rounded-lg border border-slate-200
                          dark:border-slate-800">
            <LaturMap index={index} year={year} month={month}
                      tehsil={tehsil} village={village} latest={latest} />
          </div>
        </div>
        <div className="lg:col-span-1 space-y-4">
          <SentinelPanel />
          <ChirpsPanel tehsil={effectiveTehsil} />
        </div>
      </div>

      <div className="h-[360px] rounded-lg border border-slate-200 p-3 dark:border-slate-800">
        <SPIChart index={index} />
      </div>
    </div>
  );
}
