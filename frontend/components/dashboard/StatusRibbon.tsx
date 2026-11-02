"use client";

import { useEffect, useState } from "react";
import { loadStatus } from "@/lib/data";
import { onFallback, remoteBase, usingFallback } from "@/lib/dataSource";
import { useLocale } from "@/components/i18n/LocaleProvider";

type Tone = "ok" | "warn" | "bad";

/** Reads /api/v1/status and shows what the pipeline has actually delivered.
 *  Never claims "live": it states the last observation date per source. */
export function StatusRibbon() {
  const { t } = useLocale();
  const [s, setS] = useState<any | null | undefined>(undefined);
  const [snapshot, setSnapshot] = useState(false);
  useEffect(() => { loadStatus().then(setS).catch(() => setS(null)); }, []);
  // Supabase configured but unreachable: say the numbers are the bundled snapshot.
  useEffect(() => { setSnapshot(usingFallback()); return onFallback(() => setSnapshot(true)); }, []);

  if (s === undefined) return <span className="font-mono text-[11px] text-ink/50">{t("ribbon.checking")}</span>;
  if (s === null) return <Chip tone="bad" text={t("ribbon.unavailable")} />;

  const s2 = s.sentinel2?.latest_period_id as string | null | undefined;
  const ch = s.chirps?.latest_period_id as string | null | undefined;
  const now = new Date();
  const cur = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
  const lag = (p?: string | null) => {
    if (!p) return null;
    const [y, m] = p.split("-").map(Number);
    return (now.getUTCFullYear() - y) * 12 + (now.getUTCMonth() + 1 - m);
  };
  const lagS2 = lag(s2), lagCh = lag(ch);
  const worst = Math.max(lagS2 ?? 99, lagCh ?? 99);
  // Age of the last pipeline run. The scheduler runs weekly, so more than ~10 days means it has stopped.
  const ageDays = s.generated_at ? Math.floor((now.getTime() - new Date(s.generated_at).getTime()) / 86_400_000) : null;
  const stalled = ageDays == null || ageDays > 10;
  const tone: Tone = s.monitoring_status === "operational" && worst <= 1 ? "ok" : worst <= 2 ? "warn" : "bad";
  const label = tone === "ok" ? t("ribbon.up_to_date") : tone === "warn" ? t("ribbon.behind") : t("ribbon.incomplete");

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <Chip tone={tone} text={label} />
      {s.synthetic_input && <Chip tone="bad" text={t("ribbon.synthetic")} />}
      {stalled && <Chip tone="bad" text={ageDays == null ? t("ribbon.no_run") : t("ribbon.stalled").replace("{n}", String(ageDays))} />}
      {remoteBase && snapshot && <Chip tone="warn" text={t("ribbon.snapshot")} />}
      <span className="font-mono text-[11px] text-ink/70" title={`Today is ${cur}`}>
        {t("ribbon.s2_to")} <b>{s2 ?? t("ribbon.none")}</b> · {t("ribbon.chirps_to")} <b>{ch ?? t("ribbon.none")}</b>
        {s.thermal && <> · {t("ribbon.lst_to")} <b>{s.thermal.last_lst ?? t("ribbon.none")}</b> · {t("ribbon.s1_to")} <b>{s.thermal.last_vv ?? t("ribbon.none")}</b></>}
        {ageDays != null && <> · {ageDays === 0 ? t("ribbon.checked_today") : t("ribbon.checked_ago").replace("{n}", String(ageDays))}</>}
      </span>
    </div>
  );
}

function Chip({ tone, text }: { tone: Tone; text: string }) {
  const c = tone === "ok" ? "bg-teal text-paper" : tone === "warn" ? "bg-d1 text-ink" : "bg-d3 text-paper";
  return <span className={`rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${c}`}>{text}</span>;
}
