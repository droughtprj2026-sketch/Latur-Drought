"use client";

import { useEffect, useState } from "react";
import { getStatus, type LatestStatus } from "@/lib/api";
import { useLocale } from "@/components/i18n/LocaleProvider";

function fmt(d?: string | null) {
  if (!d) return "—";
  return d.length >= 10 ? d.slice(0, 10) : d;
}

/**
 * Dashboard header strip. Reads /status (never hardcoded) and listens for
 * a `latur:latlon` custom event dispatched by the map on hover so the
 * centre field always shows the pointer's current coordinates.
 */
export function StatusHeader() {
  const { t } = useLocale();
  const [status, setStatus] = useState<LatestStatus | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then(setStatus).catch((e) => setErr(String(e)));
    const handler = (e: Event) => {
      const d = (e as CustomEvent<{ lat: number; lon: number }>).detail;
      if (d) setCoords(d);
    };
    window.addEventListener("latur:latlon", handler as EventListener);
    return () => window.removeEventListener("latur:latlon", handler as EventListener);
  }, []);

  const stKind = status?.monitoring_status ?? "";
  const chipLabel =
    stKind === "operational" ? t("status.operational")
    : stKind === "degraded"  ? t("status.degraded")
    : stKind === "processing" ? "Processing"
    : "—";
  const chipColor =
    stKind === "operational" ? { bg: "#dcfce7", fg: "#065f46", dot: "#16a34a" }
    : stKind === "processing" ? { bg: "#dbeafe", fg: "#1e3a8a", dot: "#2563eb" }
    : stKind === "degraded"  ? { bg: "#fee2e2", fg: "#7f1d1d", dot: "#dc2626" }
    : { bg: "#f1f5f9", fg: "#334155", dot: "#64748b" };

  const centroid = coords
    ? `${coords.lat.toFixed(4)}° N · ${coords.lon.toFixed(4)}° E`
    : status?.region
    ? `${status.region.centroid_lat.toFixed(3)}° N · ${status.region.centroid_lon.toFixed(3)}° E`
    : "—";

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs md:grid-cols-5">
      <Field label={t("header.status")}>
        <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium"
              style={{ background: chipColor.bg, color: chipColor.fg }}
              title={err ?? ""}>
          <span className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ background: chipColor.dot }} />
          {chipLabel}
        </span>
      </Field>
      <Field label={t("header.last_processing")}>{fmt(status?.generated_at)}</Field>
      <Field label={t("header.latest_s2")}>{fmt(status?.sentinel2?.latest_observation_date)}</Field>
      <Field label={t("header.latest_chirps")}>{fmt(status?.chirps?.latest_observation_date)}</Field>
      <Field label={t("header.coords")}>{centroid}</Field>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-slate-500">{label}</span>
      <span className="font-mono text-slate-800 dark:text-slate-200">{children}</span>
    </div>
  );
}
