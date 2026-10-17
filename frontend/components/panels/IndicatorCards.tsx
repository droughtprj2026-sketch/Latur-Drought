"use client";

import { useEffect, useMemo, useState } from "react";
import { getMaster, type MasterRow } from "@/lib/api";
import { useLocale } from "@/components/i18n/LocaleProvider";

const FIELDS: Array<[string, string]> = [
  ["SPI_1",  "SPI-1"],
  ["SPI_3",  "SPI-3"],
  ["SPI_6",  "SPI-6"],
  ["SPI_12", "SPI-12"],
  ["NDVI",   "NDVI"],
  ["EVI",    "EVI"],
  ["VCI",    "VCI"],
  ["VHI",    "VHI"],
  ["PCI",    "PCI"],
  ["composite_drought_score", "CDI"],
  ["drought_area_km2",   "Drought area km²"],
  ["drought_percentage", "Drought %"],
];

interface Props {
  tehsil?: string;
  village?: string;
}

export function IndicatorCards({ tehsil = "Latur", village = "" }: Props) {
  const { t } = useLocale();
  const [rows, setRows] = useState<MasterRow[]>([]);

  useEffect(() => {
    setRows([]);
    getMaster({ tehsil, village }).then(setRows).catch(() => undefined);
  }, [tehsil, village]);

  const last = rows[rows.length - 1];
  const prev = rows[rows.length - 2];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
      {FIELDS.map(([key, label]) => (
        <Card key={key} field={key} label={label} rows={rows}
              latest={last} previous={prev} />
      ))}
    </div>
  );
}

function Card({ field, label, rows, latest, previous }: {
  field: string; label: string;
  rows: MasterRow[]; latest?: MasterRow; previous?: MasterRow;
}) {
  const { t } = useLocale();
  const raw = (latest?.[field] ?? "").trim();
  const num = raw === "" ? NaN : Number(raw);
  const prevRaw = (previous?.[field] ?? "").trim();
  const prevNum = prevRaw === "" ? NaN : Number(prevRaw);
  const delta = (!isNaN(num) && !isNaN(prevNum)) ? num - prevNum : NaN;

  const series = useMemo(
    () => rows.slice(-24)
              .map((r) => Number((r[field] ?? "").trim()))
              .filter((n) => !isNaN(n)),
    [rows, field]
  );

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3
                    dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-slate-500">
        <span>{label}</span>
        {!isNaN(delta) && (
          <span className={delta >= 0 ? "text-emerald-600" : "text-rose-600"}>
            {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(2)}
          </span>
        )}
      </div>
      <div className="mt-1 font-mono text-base">
        {raw === "" ? <span className="text-slate-400">{t("card.unavailable")}</span>
                    : num.toFixed(2)}
      </div>
      {series.length > 2 && <Sparkline values={series} />}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const w = 120, h = 24;
  const lo = Math.min(...values), hi = Math.max(...values);
  const rng = hi - lo || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * (w - 2) + 1;
    const y = h - 1 - ((v - lo) / rng) * (h - 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mt-1 h-6 w-full" preserveAspectRatio="none">
      <polyline fill="none" stroke="currentColor" strokeWidth="1" points={pts}
                className="text-blue-600 dark:text-blue-400" />
    </svg>
  );
}
