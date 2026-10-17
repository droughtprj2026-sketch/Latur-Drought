"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar, Brush, CartesianGrid, ComposedChart, Legend, Line,
  ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getTimeseries, type IndexName, type TimeseriesPoint } from "@/lib/api";
import { HISTORICAL_DROUGHTS } from "@/lib/classify";

interface Props {
  index: IndexName;
  secondary?: IndexName;             // optional overlay index (dual axis)
}

const BAND_COLORS: Record<string, { from: number; to: number; color: string; label: string }[]> = {
  spi: [
    { from: -0.5, to: -0.8, color: "#FFFF0033", label: "D0" },
    { from: -0.8, to: -1.3, color: "#FCD37F55", label: "D1" },
    { from: -1.3, to: -1.6, color: "#FFAA0055", label: "D2" },
    { from: -1.6, to: -2.0, color: "#E6000055", label: "D3" },
    { from: -2.0, to: -3.5, color: "#73000055", label: "D4" },
  ],
  cdi: [
    { from: 0.20, to: 0.35, color: "#FFFF0033", label: "D0" },
    { from: 0.35, to: 0.50, color: "#FCD37F55", label: "D1" },
    { from: 0.50, to: 0.65, color: "#FFAA0055", label: "D2" },
    { from: 0.65, to: 0.80, color: "#E6000055", label: "D3" },
    { from: 0.80, to: 1.01, color: "#73000055", label: "D4" },
  ],
};

function bandsFor(index: IndexName) {
  if (index.startsWith("cdi")) return BAND_COLORS.cdi;
  if (index.startsWith("spi")) return BAND_COLORS.spi;
  return [];
}

export function SPIChart({ index, secondary }: Props) {
  const [primary, setPrimary] = useState<TimeseriesPoint[]>([]);
  const [second, setSecond] = useState<TimeseriesPoint[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const svgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setErr(null);
    getTimeseries(index).then(setPrimary).catch((e) => setErr(String(e)));
  }, [index]);
  useEffect(() => {
    if (!secondary) { setSecond([]); return; }
    getTimeseries(secondary).then(setSecond).catch(() => setSecond([]));
  }, [secondary]);

  const data = useMemo(() => {
    const bySec = new Map(second.map((p) => [p.date, p]));
    return primary.map((p) => ({
      date: p.date,
      value: p.value,
      value2: bySec.get(p.date)?.value ?? null,
      class: p.class,
    }));
  }, [primary, second]);

  const bands = bandsFor(index);
  const [yMin, yMax] = index.startsWith("cdi") ? [0, 1] : [-3.2, 3.2];

  const downloadCSV = () => {
    const rows = ["date,value,class" + (secondary ? ",value_secondary" : "")];
    for (const d of data) {
      rows.push([d.date, d.value ?? "", d.class, secondary ? (d.value2 ?? "") : ""]
                .filter((x) => x !== undefined).join(","));
    }
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `latur_${index}${secondary ? "_vs_" + secondary : ""}_timeseries.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const downloadPNG = async () => {
    const node = svgRef.current;
    if (!node) return;
    const htmlToImage = await import("html-to-image").catch(() => null);
    if (!htmlToImage) {
      alert("html-to-image not installed. Run: pnpm add html-to-image");
      return;
    }
    const url = await htmlToImage.toPng(node);
    const a = document.createElement("a");
    a.href = url;
    a.download = `latur_${index}_timeseries.png`;
    a.click();
  };

  if (err) return <p className="text-xs text-red-600">{err}</p>;
  if (!data.length) return <p className="text-xs text-slate-500">loading {index.toUpperCase()} …</p>;

  return (
    <div className="h-full w-full">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">
          District-mean {index.toUpperCase()}
          {secondary && <> vs {secondary.toUpperCase()}</>}  ·{" "}
          {data[0].date} – {data[data.length - 1].date}
        </h3>
        <div className="flex gap-1 text-xs">
          <button onClick={downloadCSV}
                  className="rounded border border-slate-300 px-2 py-0.5 dark:border-slate-700">
            CSV
          </button>
          <button onClick={downloadPNG}
                  className="rounded border border-slate-300 px-2 py-0.5 dark:border-slate-700">
            PNG
          </button>
        </div>
      </div>

      <div ref={svgRef} className="h-[88%] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={5} />
            <YAxis yAxisId="L" domain={[yMin, yMax]} tick={{ fontSize: 10 }} />
            {secondary && (
              <YAxis yAxisId="R" orientation="right" tick={{ fontSize: 10 }} />
            )}
            <Tooltip formatter={(v: number) => (v == null ? "—" : v.toFixed(2))} />
            {bands.map((b) => (
              <ReferenceArea key={b.label} yAxisId="L"
                             y1={Math.min(b.from, b.to)} y2={Math.max(b.from, b.to)}
                             fill={b.color} fillOpacity={1} />
            ))}
            {HISTORICAL_DROUGHTS.map(({ year, label }) => (
              <ReferenceLine key={`${year}-${label}`} yAxisId="L"
                             x={`${year}-01`}
                             stroke="#64748b" strokeDasharray="2 3"
                             label={{ value: year, position: "top", fontSize: 10, fill: "#64748b" }} />
            ))}
            <ReferenceLine yAxisId="L" y={0} stroke="#000" strokeWidth={0.5} />
            <Legend verticalAlign="top" height={24} />
            <Bar yAxisId="L" dataKey="value" name={index.toUpperCase()}
                 fill="#1d4ed8" opacity={0.9} />
            {secondary && (
              <Line yAxisId="R" type="monotone" dataKey="value2"
                    name={secondary.toUpperCase()} stroke="#dc2626"
                    strokeWidth={1.5} dot={false} />
            )}
            <Brush dataKey="date" height={16} travellerWidth={6} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
