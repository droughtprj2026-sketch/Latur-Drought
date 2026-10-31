// Typed fetch wrapper for the Latur drought-monitoring API.
// Everything the frontend calls flows through the Node API (/api/v1).

export type IndexName =
  | "spi1" | "spi3" | "spi6" | "spi12"
  | "ndvi" | "evi"  | "ndmi" | "nsmi" | "vci"
  | "vhi"  | "pci"
  | "cdi" | "cdi_class";

export interface Manifest {
  district: string;
  years: number[];
  as_of: string;
  indices: Record<string, { source: string; unit: string; years: number[] }>;
}

export interface TimeseriesPoint {
  date: string;
  value: number | null;
  class: string;
  pct_area_dry?: number | null;
}

export interface LatestStatus {
  generated_at: string;
  monitoring_status: "operational" | "degraded" | string;
  sentinel2: {
    latest_observation_date?: string | null;
    latest_period_id?: string | null;
    cloud_percentage?: number | null;
    last_successful_update?: string | null;
    status?: string | null;
  };
  chirps: {
    latest_observation_date?: string | null;
    latest_period_id?: string | null;
    last_successful_update?: string | null;
    status?: string | null;
    qc?: Record<string, any> | null;
  };
  composite: {
    formula_version?: string | null;
    weights?: Record<string, number> | null;
    min_inputs?: number | null;
    spi_reference?: string | null;
  };
  region: {
    district: string;
    state: string;
    centroid_lat: number;
    centroid_lon: number;
  };
}

export type MasterRow = Record<string, string>;

const BASE = "/api/v1";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { accept: "application/json" } });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export const getManifest = () => fetchJSON<Manifest>("/manifest");
export const getTehsils  = () => fetchJSON<GeoJSON.FeatureCollection>("/tehsils");

export const getIndexGeoJSON = (name: IndexName, year: number, month: number) =>
  fetchJSON<GeoJSON.FeatureCollection>(`/indices/${name}/${year}/${month}`);

export const getVillageIndices = (name: IndexName, year: number, month: number) =>
  fetchJSON<GeoJSON.FeatureCollection>(`/village-indices/${name}/${year}/${month}`);

export const getTimeseries = (name: IndexName, from?: string, to?: string) => {
  const q = new URLSearchParams();
  if (from) q.set("from", from);
  if (to)   q.set("to", to);
  const qs = q.toString();
  return fetchJSON<TimeseriesPoint[]>(`/timeseries/${name}${qs ? `?${qs}` : ""}`);
};

export const getStatus       = () => fetchJSON<LatestStatus>("/status");
export const getAvailability = () => fetchJSON<Record<string, any>>("/availability");

export const getLatest = (tehsil = "Latur", village = "") => {
  const q = new URLSearchParams({ tehsil });
  if (village) q.set("village", village);
  return fetchJSON<MasterRow>(`/latest?${q.toString()}`);
};

export const getMaster = (opts: {
  tehsil?: string; village?: string; from?: string; to?: string;
} = {}) => {
  const q = new URLSearchParams();
  if (opts.tehsil)  q.set("tehsil",  opts.tehsil);
  if (opts.village) q.set("village", opts.village);
  if (opts.from)    q.set("from",    opts.from);
  if (opts.to)      q.set("to",      opts.to);
  const qs = q.toString();
  return fetchJSON<MasterRow[]>(`/master${qs ? `?${qs}` : ""}`);
};

export const getCompare = (index: IndexName, a: string, b: string) =>
  fetchJSON<{ a: { period: string; rows: MasterRow[] };
              b: { period: string; rows: MasterRow[] } }>(
    `/compare?index=${index}&a=${a}&b=${b}`
  );

export const getAnimation = (index: IndexName, from?: string, to?: string) => {
  const q = new URLSearchParams({ index });
  if (from) q.set("from", from);
  if (to)   q.set("to", to);
  return fetchJSON<{ index: string; count: number;
                     frames: { period: string; geojson_url: string }[] }>(
    `/animation?${q.toString()}`
  );
};
