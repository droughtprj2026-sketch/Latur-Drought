"use client";

import { useEffect, useState } from "react";
import { getLatest, getStatus, type LatestStatus, type MasterRow } from "@/lib/api";
import { useLocale } from "@/components/i18n/LocaleProvider";

export function ChirpsPanel({ tehsil = "Latur" }: { tehsil?: string }) {
  const { t } = useLocale();
  const [s, setS] = useState<LatestStatus | null>(null);
  const [row, setRow] = useState<MasterRow | null>(null);

  useEffect(() => { getStatus().then(setS).catch(() => undefined); }, []);
  useEffect(() => { getLatest(tehsil).then(setRow).catch(() => undefined); }, [tehsil]);

  const ch = s?.chirps ?? {};
  const refPeriod = s?.composite?.spi_reference ?? "1991-2020";
  const rain = row?.["monthly_rainfall_mm"];
  const qcCoverage = (ch.qc as any)?.spatial_coverage_pct;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4
                        dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-sm font-semibold">{t("panels.chirps.title")}</h3>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <Row label="Latest CHIRPS obs."  value={ch.latest_observation_date} />
        <Row label="Latest completed month" value={ch.latest_period_id} />
        <Row label="Monthly rainfall (mm)"  value={rain} />
        <Row label="SPI reference"         value={refPeriod} />
        <Row label="Spatial coverage %"    value={qcCoverage != null ? `${qcCoverage}` : ""} />
        <Row label="Last successful run"   value={ch.last_successful_update?.slice(0, 19).replace("T", " ")} />
      </dl>
      <p className="mt-3 text-[11px] text-slate-500">
        Source: UCSB CHG CHIRPS v2.0 monthly precipitation
        (<code>UCSB-CHG/CHIRPS/monthly</code>), native ~5 km, clipped to the
        Latur study area.
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
