"use client";

import { useEffect, useState } from "react";
import { getStatus, type LatestStatus } from "@/lib/api";
import { useLocale } from "@/components/i18n/LocaleProvider";

export function SentinelPanel() {
  const { t } = useLocale();
  const [s, setS] = useState<LatestStatus | null>(null);
  useEffect(() => { getStatus().then(setS).catch(() => undefined); }, []);
  const sen = s?.sentinel2 ?? {};

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4
                        dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-sm font-semibold">{t("panels.sentinel.title")}</h3>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <Row label="Latest observation" value={sen.latest_observation_date} />
        <Row label="Latest period"       value={sen.latest_period_id} />
        <Row label="Cloud %"              value={sen.cloud_percentage != null ? `${sen.cloud_percentage}` : ""} />
        <Row label="Last successful run"  value={sen.last_successful_update?.slice(0, 19).replace("T", " ")} />
        <Row label="Status"               value={sen.status} />
        <Row label="Derived layers"       value="NDVI · EVI · VHI" />
      </dl>
      <p className="mt-3 text-[11px] text-slate-500">
        Source: Copernicus Sentinel-2 L2A, via Google Earth Engine
        (<code>COPERNICUS/S2_SR_HARMONIZED</code>).
      </p>
    </section>
  );
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  const { t } = useLocale();
  const v = (value ?? "").toString().trim();
  return (
    <>
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-mono">{v || <span className="text-slate-400">{t("card.unavailable")}</span>}</dd>
    </>
  );
}
