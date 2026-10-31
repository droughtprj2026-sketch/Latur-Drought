"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import type { FeatureCollection } from "geojson";
import L from "leaflet";
import { BASEMAPS } from "./basemaps";
import { MapLegend } from "./MapLegend";
import { MapControls } from "./MapChrome";
import {
  METRICS, binFor, colorFor, formatValue, NO_DATA_COLOR,
  type ActiveVillage, type MetricName,
} from "@/lib/metrics";
import {
  activeVillage, loadBaselines, loadDistrict, loadTehsils, loadTimeseries, loadVillages,
  type Baselines, type TimeseriesById, type VillageFeatureProps,
} from "@/lib/data";

export type { MetricName };

interface Props {
  metric: MetricName;
  tehsil?: string;
  /** Polygon id of the selected village (ids are unique; names are not). */
  selectedVillageId?: number | null;
  currentPeriod: string;
  onSelectVillage?: (v: ActiveVillage) => void;
  /** Uploaded area of interest, drawn above the villages. */
  aoi?: FeatureCollection | null;
  showSatellite?: boolean;
  /** Pixels of the right edge covered by a side panel. */
  rightInset?: number;
  /** Lets the legend offer "jump to the last month that has data" for sparse layers. */
  onPeriodChange?: (period: string) => void;
  /** Slot for page controls pinned top-left. */
  topLeft?: ReactNode;
  /** Slot docked bottom, beside the legend (e.g. the timeline). */
  children?: ReactNode;
}

const LATUR_CENTER: [number, number] = [18.4088, 76.5604];
const INK = "#1d2b25";

const esc = (s: unknown) =>
  String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");

/** Imperative village layer: built once, restyled in place on every
 *  metric / month / selection change (no remount of 954 polygons). */
function VillageLayer(props: {
  data: FeatureCollection;
  records: Map<number, ActiveVillage>;
  metric: MetricName;
  tehsil: string;
  selectedId: number | null;
  onSelect?: (v: ActiveVillage) => void;
}) {
  const map = useMap();
  const layerRef = useRef<L.GeoJSON | null>(null);
  const hoverRef = useRef<number | null>(null);
  const live = useRef(props);
  live.current = props;

  const styleFor = (id: number): L.PathOptions => {
    const { records, metric, tehsil, selectedId } = live.current;
    const rec = records.get(id);
    const spec = METRICS[metric];
    const inTehsil = tehsil === "All" || rec?.tehsil.toLowerCase() === tehsil.toLowerCase();
    const selected = selectedId === id;
    const hovered = hoverRef.current === id;
    return {
      fillColor: rec ? colorFor(spec, rec) : NO_DATA_COLOR,
      fillOpacity: selected || hovered ? 0.95 : inTehsil ? 0.82 : 0.14,
      color: selected ? INK : hovered ? INK : "#ffffff",
      weight: selected ? 3 : hovered ? 2 : 0.5,
      opacity: inTehsil || selected ? 1 : 0.35,
    };
  };

  // Build once per geometry.
  useEffect(() => {
    if (!map.getPane("villages")) {
      const pane = map.createPane("villages");
      pane.style.zIndex = "450";
    }
    const layer = L.geoJSON(props.data, {
      pane: "villages",
      style: (f) => styleFor(Number(f?.properties?.id)),
      onEachFeature: (f, l) => {
        const id = Number(f.properties?.id);
        l.bindTooltip(
          () => {
            const { records, metric } = live.current;
            const rec = records.get(id);
            if (!rec) return esc(f.properties?.village);
            const spec = METRICS[metric];
            const v = spec.value(rec);
            const b = binFor(spec, v);
            const cdiBin = binFor(METRICS.cdi, rec.cdi);
            return `<div class="vt">
              <div class="vt-name">${esc(rec.village)}</div>
              <div class="vt-sub">${esc(rec.tehsil)} tehsil · ${esc(rec.period)}</div>
              <div class="vt-row"><i style="background:${b ? b.color : NO_DATA_COLOR}"></i>
                <b>${esc(spec.title.split(" (")[0])}</b>
                <span>${esc(formatValue(spec, v))}${b ? " · " + esc(b.label) : ""}</span></div>
              ${metric !== "cdi" ? `<div class="vt-row"><i style="background:${cdiBin ? cdiBin.color : NO_DATA_COLOR}"></i>
                <b>CDI</b><span>${rec.cdi != null ? rec.cdi.toFixed(3) + " · " + esc(cdiBin?.label) : "no data"}</span></div>` : ""}
            </div>`;
          },
          { sticky: false, direction: "top", offset: [0, -6], opacity: 1, className: "village-tip" },
        );
        l.on({
          mouseover: () => {
            hoverRef.current = id;
            (l as L.Path).setStyle(styleFor(id));
            (l as L.Path).bringToFront();
          },
          mouseout: () => {
            hoverRef.current = null;
            (l as L.Path).setStyle(styleFor(id));
          },
          click: () => {
            const rec = live.current.records.get(id);
            if (rec) live.current.onSelect?.(rec);
          },
        });
      },
    }).addTo(map);
    layerRef.current = layer;
    return () => { layer.remove(); layerRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, props.data]);

  // Restyle in place.
  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.eachLayer((l) => {
      const id = Number((l as any).feature?.properties?.id);
      (l as L.Path).setStyle(styleFor(id));
      if (live.current.selectedId === id) (l as L.Path).bringToFront();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.records, props.metric, props.tehsil, props.selectedId]);

  return null;
}

/** Tehsil + district outlines and the uploaded AOI. Non-interactive so they
 *  never swallow hover or click events meant for villages. */
function Overlays({ tehsils, district, aoi }: {
  tehsils: FeatureCollection | null; district: FeatureCollection | null; aoi: FeatureCollection | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (!map.getPane("outlines")) {
      const pane = map.createPane("outlines");
      pane.style.zIndex = "460";
      pane.style.pointerEvents = "none";
    }
    const made: L.Layer[] = [];
    if (tehsils) made.push(L.geoJSON(tehsils, { pane: "outlines", interactive: false,
      style: () => ({ fill: false, color: INK, weight: 1.1, opacity: 0.55, dashArray: "5 4" }) }).addTo(map));
    if (district) made.push(L.geoJSON(district, { pane: "outlines", interactive: false,
      style: () => ({ fill: false, color: INK, weight: 2.4, opacity: 0.95 }) }).addTo(map));
    return () => made.forEach((l) => l.remove());
  }, [map, tehsils, district]);

  useEffect(() => {
    if (!aoi?.features?.length) return;
    if (!map.getPane("aoi")) {
      const pane = map.createPane("aoi");
      pane.style.zIndex = "470";
      pane.style.pointerEvents = "none";
    }
    const layer = L.geoJSON(aoi, { pane: "aoi", interactive: false,
      style: () => ({ color: "#0b6e6e", weight: 3, dashArray: "8 5", fillColor: "#0b6e6e", fillOpacity: 0.08 }) }).addTo(map);
    const b = layer.getBounds();
    if (b.isValid()) map.fitBounds(b, { padding: [50, 50], maxZoom: 13 });
    return () => { layer.remove(); };
  }, [map, aoi]);
  return null;
}

function Framing({ data, tehsil, selectedId }: {
  data: FeatureCollection | null; tehsil: string; selectedId: number | null;
}) {
  const map = useMap();
  // Reserve room for the controls (top), the legend/timeline dock (bottom) and
  // the basemap/zoom stack (right) so framed polygons are never hidden behind them.
  const pad = { paddingTopLeft: L.point(24, 64), paddingBottomRight: L.point(80, 190) };
  useEffect(() => {
    if (!data) return;
    const fit = (g: any, maxZoom: number) => map.fitBounds(L.geoJSON(g).getBounds(), { ...pad, maxZoom });
    if (selectedId != null) {
      const f = data.features.find((x) => Number(x.properties?.id) === selectedId);
      if (f) return void fit(f, 13);
    }
    if (tehsil !== "All") {
      const fs = data.features.filter(
        (x) => String(x.properties?.tehsil).toLowerCase() === tehsil.toLowerCase());
      if (fs.length) return void fit({ type: "FeatureCollection", features: fs }, 12);
    }
    fit(data, 11);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, tehsil, selectedId, map]);
  return null;
}

export default function LaturMap({
  metric = "cdi", tehsil = "All", selectedVillageId = null, currentPeriod,
  onSelectVillage, aoi = null, showSatellite = false, rightInset = 0, onPeriodChange, topLeft, children,
}: Props) {
  const [basemapId, setBasemapId] = useState("osm");
  const [villages, setVillages] = useState<FeatureCollection | null>(null);
  const [tehsils, setTehsils] = useState<FeatureCollection | null>(null);
  const [district, setDistrict] = useState<FeatureCollection | null>(null);
  const [ts, setTs] = useState<TimeseriesById | null>(null);
  const [baselines, setBaselines] = useState<Baselines | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([loadVillages(), loadTimeseries(), loadBaselines()])
      .then(([v, t, b]) => { if (alive) { setVillages(v); setTs(t); setBaselines(b); } })
      .catch((e) => alive && setError(String(e)));
    loadTehsils().then((d) => alive && setTehsils(d)).catch(() => null);
    loadDistrict().then((d) => alive && setDistrict(d)).catch(() => null);
    return () => { alive = false; };
  }, []);

  const records = useMemo(() => {
    const m = new Map<number, ActiveVillage>();
    if (!villages) return m;
    for (const f of villages.features) {
      const p = f.properties as unknown as VillageFeatureProps;
      m.set(Number(p.id), activeVillage(p, ts, baselines, currentPeriod));
    }
    return m;
  }, [villages, ts, baselines, currentPeriod]);

  const spec = METRICS[metric];
  const legend = useMemo(() => {
    const counts = spec.bins.map(() => 0);
    let noData = 0, total = 0;
    records.forEach((r) => {
      if (tehsil !== "All" && r.tehsil.toLowerCase() !== tehsil.toLowerCase()) return;
      total++;
      const b = binFor(spec, spec.value(r));
      if (!b) noData++; else counts[spec.bins.indexOf(b)]++;
    });
    return { counts, noData, total };
  }, [records, spec, tehsil]);

  // Newest month in which at least half the villages carry a value for this layer.
  const lastWithData = useMemo(() => {
    if (!ts || !villages || legend.total === 0 || legend.noData / legend.total <= 0.5) return null;
    const counts = new Map<string, number>();
    for (const pts of Object.values(ts)) {
      for (const pt of pts) {
        const rec = { ...pt, id: 0, village: "", tehsil: "", period: pt.p } as unknown as ActiveVillage;
        // baseline layers need the village record; only plain layers are scanned here
        if (spec.group === "Baseline") return null;
        if (spec.value(rec) != null) counts.set(pt.p, (counts.get(pt.p) ?? 0) + 1);
      }
    }
    const ok = [...counts].filter(([, n]) => n >= 0.5 * Object.keys(ts).length).map(([p]) => p).sort();
    return ok.length ? ok[ok.length - 1] : null;
  }, [ts, villages, spec, legend]);

  const basemap = BASEMAPS.find((b) => b.id === basemapId) ?? BASEMAPS[0];

  return (
    <div className="relative h-full w-full overflow-hidden bg-[#e9e6dc]">
      {!villages && !error && (
        <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-paper/80">
          <p className="font-mono text-xs text-ink/70">Loading village polygons…</p>
        </div>
      )}
      {error && (
        <div className="absolute inset-x-0 top-16 z-[1000] mx-auto w-fit rounded border border-d4/40 bg-paper px-3 py-2 text-xs text-d4 shadow-card">
          Could not load map data: {error}
        </div>
      )}

      <MapContainer
        center={LATUR_CENTER} zoom={9} minZoom={8} maxZoom={15}
        zoomControl={false} scrollWheelZoom className="h-full w-full"
      >
        <TileLayer key={basemap.id} url={basemap.url} attribution={basemap.attribution} maxZoom={basemap.maxZoom ?? 19} />
        {showSatellite && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            opacity={0.55}
            attribution="Imagery &copy; Esri, Maxar, Earthstar Geographics"
          />
        )}
        {villages && (
          <VillageLayer
            data={villages} records={records} metric={metric} tehsil={tehsil}
            selectedId={selectedVillageId} onSelect={onSelectVillage}
          />
        )}
        <Overlays tehsils={tehsils} district={district} aoi={aoi} />
        <Framing data={villages} tehsil={tehsil} selectedId={selectedVillageId} />
        <MapControls basemapId={basemapId} onBasemap={setBasemapId} rightInset={rightInset} />
      </MapContainer>

      {topLeft && (
        <div className="pointer-events-none absolute left-3 top-3 z-[600] max-w-[calc(100%-250px-24px)]">
          <div className="pointer-events-auto">{topLeft}</div>
        </div>
      )}

      {/* Bottom dock: legend and timeline sit side by side, never on top of each other. */}
      <div
        className="pointer-events-none absolute bottom-7 left-3 z-[600] flex flex-col items-stretch gap-3 transition-[right] duration-200 md:flex-row md:items-end"
        style={{ right: 12 + rightInset }}
      >
        <MapLegend
          spec={spec} counts={legend.counts} noData={legend.noData} total={legend.total}
          period={currentPeriod} tehsilLabel={tehsil === "All" ? "all tehsils" : tehsil}
          jumpTo={lastWithData && onPeriodChange ? { period: lastWithData, go: () => onPeriodChange(lastWithData) } : null}
        />
        {children && <div className="pointer-events-auto min-w-0 flex-1">{children}</div>}
      </div>
    </div>
  );
}
