"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { IndexDropdown, type IndexName } from "@/components/ui/IndexDropdown";
import { YearSlider } from "@/components/ui/YearSlider";

const ComparisonSlider = dynamic(
  () => import("@/components/compare/ComparisonSlider").then((m) => m.ComparisonSlider),
  { ssr: false },
);

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const YEARS = Array.from({ length: 11 }, (_, i) => 2016 + i);

export default function ComparePage() {
  const [index, setIndex] = useState<IndexName>("cdi");
  const [ay, setAY] = useState(2019); const [am, setAM] = useState(5);
  const [by, setBY] = useState(2026); const [bm, setBM] = useState(9);

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-200 bg-white p-4
                      dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          <IndexDropdown value={index} onChange={setIndex} />
          <PeriodPicker label="Period A (older)" y={ay} m={am} setY={setAY} setM={setAM} />
          <PeriodPicker label="Period B (newer)" y={by} m={bm} setY={setBY} setM={setBM} />
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Drag the center handle to reveal period A under period B.
        </p>
      </div>
      <ComparisonSlider index={index} a={{ year: ay, month: am }} b={{ year: by, month: bm }} />
    </div>
  );
}

function PeriodPicker({
  label, y, m, setY, setM,
}: { label: string; y: number; m: number;
     setY: (n: number) => void; setM: (n: number) => void }) {
  return (
    <div className="col-span-2">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-1 flex gap-2">
        <select value={y} onChange={(e) => setY(Number(e.target.value))}
                className="w-24 rounded border border-slate-300 bg-transparent px-2 py-1 text-sm
                           dark:border-slate-700">
          {YEARS.map((yy) => <option key={yy} value={yy}>{yy}</option>)}
        </select>
        <select value={m} onChange={(e) => setM(Number(e.target.value))}
                className="w-28 rounded border border-slate-300 bg-transparent px-2 py-1 text-sm
                           dark:border-slate-700">
          {MONTHS.map((mm, i) => <option key={mm} value={i + 1}>{mm}</option>)}
        </select>
      </div>
    </div>
  );
}
