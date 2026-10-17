"use client";

import { useEffect, useState } from "react";
import { getLatest, type MasterRow } from "@/lib/api";
import { codeForCDI, colorForCode, D_LABELS, D_CODES } from "@/lib/classify";
import { useLocale } from "@/components/i18n/LocaleProvider";

interface Props {
  tehsil?: string;
  village?: string;
}

/**
 * Headline "final verdict" card. Classification comes from the composite
 * CDI (not from any learned classifier). Hovering the score reveals the
 * component contributions written into the master CSV.
 */
export function DroughtStatusCard({ tehsil = "Latur", village = "" }: Props) {
  const { t } = useLocale();
  const [row, setRow] = useState<MasterRow | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null); setRow(null);
    getLatest(tehsil, village).then(setRow).catch((e) => setErr(String(e)));
  }, [tehsil, village]);

  if (err) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700
                      dark:border-red-900 dark:bg-red-950/40">
        {err}
      </div>
    );
  }

  const scoreRaw = row?.["composite_drought_score"];
  const score = scoreRaw ? Number(scoreRaw) : NaN;
  const isPendingSentinel = Number.isNaN(score) || row?.["data_quality_status"] === "spi_verified_sentinel_pending";
  const code = (row?.["composite_drought_class"] || codeForCDI(Number.isNaN(score) ? null : score)) as string;
  const label = isPendingSentinel ? "Pending Sentinel-2 Processing" : (code === "ND" ? "No data" : (D_LABELS[D_CODES.indexOf(code as any)] ?? code));
  const dark = ["D2", "D3", "D4"].includes(code);
  const txt  = isPendingSentinel ? "#334155" : (dark ? "#ffffff" : "#1f2937");
  const bg   = isPendingSentinel ? "#f1f5f9" : colorForCode(code);

  const contrib: Record<string, number> = (() => {
    try { return JSON.parse(row?.["component_contributions"] || "{}"); }
    catch { return {}; }
  })();

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm
                    dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>{village ? `${village}, ${tehsil}` : tehsil} · {row?.["observation_period"] ?? "—"}</span>
            {isPendingSentinel && (
              <span className="rounded bg-sky-100 px-2 py-0.5 text-[10px] font-medium text-sky-800 dark:bg-sky-950 dark:text-sky-300">
                CHIRPS SPI Verified
              </span>
            )}
          </div>
          <div className="mt-1 flex items-baseline gap-3">
            <span className="rounded-md px-3 py-1 text-lg font-semibold"
                  style={{ background: bg, color: txt }}>
              {isPendingSentinel ? "Pending Sentinel Ingest" : (code === "None" ? t("status.no_drought") : label)}
            </span>
            <span className="font-mono text-sm text-slate-600 dark:text-slate-300"
                  title={Object.entries(contrib)
                                .map(([k, v]) => `${k}: ${v}`)
                                .join("  ·  ")}>
              CDI = {Number.isNaN(score) ? "Pending" : score.toFixed(3)}
            </span>
          </div>
        </div>
        <div className="text-right text-[11px] text-slate-500">
          <div>Obs. {row?.["sentinel2_observation_date"] || "—"}</div>
          <div>CHIRPS {row?.["chirps_data_through"] || "—"}</div>
          <div>Proc. {row?.["processing_timestamp"]?.slice(0, 10) || "—"}</div>
          <div>Formula {row?.["composite_formula_version"] || "—"}</div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={t("card.drought_area") + " (km²)"} value={row?.["drought_area_km2"]} />
        <Stat label={t("card.drought_percentage") + " %"} value={row?.["drought_percentage"]} />
        <Stat label="Formula version" value={row?.["composite_formula_version"]} />
        <Stat label={t("card.tehsil_area") + " (km²)"} value={row?.["total_polygon_area_km2"]} />
      </div>

      {Object.keys(contrib).length > 0 && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-wide text-slate-500">
            Component contributions (sum = CDI)
          </div>
          <div className="mt-1 h-3 w-full overflow-hidden rounded bg-slate-100 dark:bg-slate-800">
            {Object.entries(contrib).map(([k, v], i) => (
              <span key={k} title={`${k}: ${v}`}
                    className="inline-block h-full"
                    style={{
                      width: `${Math.max(0, Number(v)) * 100}%`,
                      background: ["#1d4ed8","#059669","#d97706","#dc2626","#7c3aed","#0891b2"][i % 6],
                    }} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value?: string }) {
  const { t } = useLocale();
  const v = (value ?? "").trim();
  return (
    <div className="rounded border border-slate-200 p-2 dark:border-slate-700">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 font-mono text-sm">
        {v === "" ? <span className="text-slate-400">{t("card.unavailable")}</span> : v}
      </div>
    </div>
  );
}
