"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";
import { YearSlider } from "@/components/ui/YearSlider";
import { getManifest } from "@/lib/api";

const LaturMap = dynamic(() => import("@/components/map/LaturMap"), { ssr: false });

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export default function MapPage() {
  const [index, setIndex] = useState<IndexName>("ndvi");
  const [year, setYear] = useState<number>(2026);
  const [month, setMonth] = useState<number>(9);
  const [years, setYears] = useState<number[]>(
    Array.from({ length: 11 }, (_, i) => 2016 + i)
  );

  useEffect(() => {
    getManifest().then((m) => {
      if (m.years.length) {
        setYears(m.years);
        setYear(m.years[m.years.length - 1]);
      }
    }).catch(() => undefined);
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 rounded-lg border border-slate-200
                      bg-white p-4 dark:border-slate-800 dark:bg-slate-900
                      md:grid-cols-[1fr,2fr,auto]">
        <IndexDropdown value={index} onChange={setIndex} />
        <YearSlider years={years} value={year} onChange={setYear} />
        <div>
          <label className="block text-xs font-medium text-slate-500">Month</label>
          <select value={month} onChange={(e) => setMonth(Number(e.target.value))}
                  className="mt-1 w-36 rounded border border-slate-300 bg-transparent
                             px-2 py-1.5 text-sm dark:border-slate-700">
            {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
          </select>
        </div>
      </div>
      <div className="h-[80vh] overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
        <LaturMap index={index} year={year} month={month} />
      </div>
    </div>
  );
}
