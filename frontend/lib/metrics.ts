// One definition per mappable metric. The map fill colour, the legend
// swatches, the hover tooltip and the "drought definition" panel all read
// from this table, so they cannot drift apart.
//
// Drought-class bins for CDI / SPI come from lib/classify.ts, which mirrors
// scripts/common/classify.py and config/composite.yaml.

import { D_COLORS, D_LABELS } from "./classify";

export type MetricName =
  | "cdi"
  | "spi1" | "spi3" | "spi6" | "spi12"
  | "ndvi" | "vci" | "vhi" | "pci" | "rain"
  | "tci" | "smi" | "lst"
  | "base_ndvi" | "base_rain" | "z_ndvi" | "z_rain";

/** A half-open interval [lo, hi). */
export interface Bin {
  lo: number;
  hi: number;
  color: string;
  label: string;
  /** Short range text shown beside the swatch, e.g. "-1.3 to -0.8". */
  range: string;
}

export interface MetricSpec {
  id: MetricName;
  label: string;
  group: "Drought" | "Rainfall" | "Vegetation" | "Thermal & soil" | "Baseline" | "Long-term";
  /** How often the value can change. The pipeline is checked weekly but every input is a monthly product. */
  cadence: "monthly";
  unit: string;
  decimals: number;
  title: string;          // legend heading
  definition: string;     // one-line plain-language definition
  bins: Bin[];            // ordered ascending by lo
  /** Pull the raw value out of an active-village record. */
  value: (p: ActiveVillage) => number | null | undefined;
}

/** What the map knows about one village for the selected month. */
export interface ActiveVillage {
  id: number;
  village: string;
  tehsil: string;
  period: string;
  cdi?: number | null;
  cls?: string | null;
  ndvi?: number | null;
  evi?: number | null;
  vci?: number | null;
  vhi?: number | null;
  pci?: number | null;
  tci?: number | null;
  smi?: number | null;
  lst?: number | null;
  vv?: number | null;
  rain?: number | null;
  spi1?: number | null;
  spi3?: number | null;
  spi6?: number | null;
  spi12?: number | null;
  /** Calendar-month climatology for this village (null if unavailable). */
  base?: { ndvi_mean?: number | null; ndvi_std?: number | null;
           rain_mean?: number | null; rain_std?: number | null } | null;
  area_sqkm?: number;
}

const NO_DATA = "#A39F90";
export const NO_DATA_COLOR = NO_DATA;

const bin = (lo: number, hi: number, color: string, label: string, range: string): Bin =>
  ({ lo, hi, color, label, range });

const INF = Infinity;

// D-class colours indexed 0..5 = None, D0..D4
const [C_NONE, C_D0, C_D1, C_D2, C_D3, C_D4] = D_COLORS;
const WET = ["#9CC9D9", "#4C97BE", "#1F5E92"];

// ---- CDI (0..1 intensity) — thresholds from config/composite.yaml --------
const CDI_BINS: Bin[] = [
  bin(-INF, 0.20, C_NONE, "Not in drought",         "< 0.20"),
  bin(0.20, 0.35, C_D0,   "D0 Abnormally dry",      "0.20 – 0.35"),
  bin(0.35, 0.50, C_D1,   "D1 Moderate",            "0.35 – 0.50"),
  bin(0.50, 0.65, C_D2,   "D2 Severe",              "0.50 – 0.65"),
  bin(0.65, 0.80, C_D3,   "D3 Extreme",             "0.65 – 0.80"),
  bin(0.80, INF,  C_D4,   "D4 Exceptional",         "≥ 0.80"),
];

// ---- SPI (McKee 1993 + US-DM drought classes) ----------------------------
const SPI_BINS: Bin[] = [
  bin(-INF, -2.0, C_D4,  "D4 Exceptional",    "≤ -2.0"),
  bin(-2.0, -1.6, C_D3,  "D3 Extreme",        "-2.0 to -1.6"),
  bin(-1.6, -1.3, C_D2,  "D2 Severe",         "-1.6 to -1.3"),
  bin(-1.3, -0.8, C_D1,  "D1 Moderate",       "-1.3 to -0.8"),
  bin(-0.8, -0.5, C_D0,  "D0 Abnormally dry", "-0.8 to -0.5"),
  bin(-0.5,  1.0, C_NONE,"Near normal",       "-0.5 to +1.0"),
  bin( 1.0,  2.0, WET[1],"Wet",               "+1.0 to +2.0"),
  bin( 2.0,  INF, WET[2],"Very wet",          "≥ +2.0"),
];

// ---- Kogan thresholds for VCI / VHI / PCI (0..100, low = stressed) -------
const KOGAN_BINS: Bin[] = [
  bin(-INF, 10, C_D4,  "Extreme stress", "< 10"),
  bin(10, 20,  C_D3,   "Severe stress",  "10 – 20"),
  bin(20, 30,  C_D2,   "Moderate stress","20 – 30"),
  bin(30, 40,  C_D1,   "Mild stress",    "30 – 40"),
  bin(40, 60,  C_NONE, "Fair",           "40 – 60"),
  bin(60, INF, "#7DB36B", "Favourable",  "≥ 60"),
];

const NDVI_BINS: Bin[] = [
  bin(-INF, 0.15, "#B98B52", "Bare / senescent", "< 0.15"),
  bin(0.15, 0.25, "#E3C877", "Sparse",           "0.15 – 0.25"),
  bin(0.25, 0.35, "#BFD37A", "Moderate",         "0.25 – 0.35"),
  bin(0.35, 0.45, "#7DB36B", "Healthy",          "0.35 – 0.45"),
  bin(0.45, INF,  "#2F7D4F", "Dense",            "≥ 0.45"),
];

const RAIN_BINS: Bin[] = [
  bin(-INF, 5,   "#F3E7C9", "Dry",           "< 5 mm"),
  bin(5, 25,     "#CFE3E8", "Light",         "5 – 25 mm"),
  bin(25, 75,    "#9CC9D9", "Moderate",      "25 – 75 mm"),
  bin(75, 150,   "#4C97BE", "Heavy",         "75 – 150 mm"),
  bin(150, INF,  "#1F5E92", "Very heavy",    "≥ 150 mm"),
];

// ---- Land-surface temperature, deg C (warm = stress) ------------------------
const LST_BINS: Bin[] = [
  bin(-INF, 25, "#F1E9D2", "Cool",       "< 25 °C"),
  bin(25, 30,   "#F6D9A0", "Warm",       "25 – 30 °C"),
  bin(30, 35,   "#F0A860", "Hot",        "30 – 35 °C"),
  bin(35, 40,   "#D9602F", "Very hot",   "35 – 40 °C"),
  bin(40, INF,  "#8E2418", "Extreme",    "≥ 40 °C"),
];

// ---- Departure from the village's own 2016-26 calendar-month normal ------
const Z_BINS: Bin[] = [
  bin(-INF, -2.0, C_D4,  "Far below normal",  "z ≤ -2.0"),
  bin(-2.0, -1.5, C_D3,  "Well below normal", "-2.0 to -1.5"),
  bin(-1.5, -1.0, C_D2,  "Below normal",      "-1.5 to -1.0"),
  bin(-1.0, -0.5, C_D0,  "Slightly below",    "-1.0 to -0.5"),
  bin(-0.5,  0.5, C_NONE,"Near normal",       "-0.5 to +0.5"),
  bin( 0.5,  1.0, "#9CC9D9", "Slightly above","+0.5 to +1.0"),
  bin( 1.0,  INF, "#4C97BE", "Well above",    "≥ +1.0"),
];

const PCT_BINS: Bin[] = [
  bin(-INF, 25,  C_D4,  "Far below normal",  "< 25 %"),
  bin(25, 50,    C_D3,  "Well below normal", "25 – 50 %"),
  bin(50, 75,    C_D1,  "Below normal",      "50 – 75 %"),
  bin(75, 125,   C_NONE,"Near normal",       "75 – 125 %"),
  bin(125, 200,  "#9CC9D9", "Above normal",  "125 – 200 %"),
  bin(200, INF,  "#4C97BE", "Far above",     "≥ 200 %"),
];

const zOf = (v?: number | null, mu?: number | null, sd?: number | null) =>
  v == null || mu == null || !sd ? null : (v - mu) / sd;

export const METRICS: Record<MetricName, MetricSpec> = {
  cdi: {
    id: "cdi", label: "Composite drought (CDI)", group: "Drought", cadence: "monthly", unit: "0–1", decimals: 3,
    title: "Composite Drought Index",
    definition: "Weighted blend of SPI-3, VHI, VCI, NDVI, EVI and PCI (config/composite.yaml). Higher = drier.",
    bins: CDI_BINS, value: (p) => p.cdi,
  },
  spi1:  { id: "spi1", label: "SPI-1 · last month", group: "Rainfall", cadence: "monthly", unit: "σ", decimals: 2,
    title: "SPI-1 (meteorological)", definition: "Standardised rainfall for the month against the CHIRPS 1991–2020 gamma fit.",
    bins: SPI_BINS, value: (p) => p.spi1 },
  spi3:  { id: "spi3", label: "SPI-3 · 3-month accumulated", group: "Long-term", cadence: "monthly", unit: "σ", decimals: 2,
    title: "SPI-3 (long-term)", definition: "Rainfall accumulated over the last 3 months, standardised. A slow indicator: it changes only when a new month of CHIRPS is published.",
    bins: SPI_BINS, value: (p) => p.spi3 },
  spi6:  { id: "spi6", label: "SPI-6 · 6-month accumulated", group: "Long-term", cadence: "monthly", unit: "σ", decimals: 2,
    title: "SPI-6 (long-term)", definition: "Rainfall accumulated over the last 6 months, standardised. A slow indicator of runoff and tank storage; changes monthly.",
    bins: SPI_BINS, value: (p) => p.spi6 },
  spi12: { id: "spi12", label: "SPI-12 · 12-month accumulated", group: "Long-term", cadence: "monthly", unit: "σ", decimals: 2,
    title: "SPI-12 (long-term)", definition: "Rainfall accumulated over the last 12 months, standardised. A slow indicator of groundwater and reservoirs; changes monthly.",
    bins: SPI_BINS, value: (p) => p.spi12 },
  rain: { id: "rain", label: "Rainfall (CHIRPS)", group: "Rainfall", cadence: "monthly", unit: "mm", decimals: 1,
    title: "Monthly rainfall", definition: "CHIRPS monthly total averaged over the village polygon.",
    bins: RAIN_BINS, value: (p) => p.rain },
  ndvi: { id: "ndvi", label: "NDVI · greenness", group: "Vegetation", cadence: "monthly", unit: "index", decimals: 3,
    title: "NDVI", definition: "Sentinel-2 (B8−B4)/(B8+B4), village mean. Season-dependent: compare with the baseline layers.",
    bins: NDVI_BINS, value: (p) => p.ndvi },
  vci: { id: "vci", label: "VCI · vegetation condition", group: "Vegetation", cadence: "monthly", unit: "0–100", decimals: 1,
    title: "Vegetation Condition Index", definition: "NDVI position between the month's historical min and max. Below 40 means vegetation stress.",
    bins: KOGAN_BINS, value: (p) => p.vci },
  vhi: { id: "vhi", label: "VHI · vegetation health", group: "Vegetation", cadence: "monthly", unit: "0–100", decimals: 1,
    title: "Vegetation Health Index", definition: "0.5·VCI + 0.5·TCI (Kogan). Where no land-surface temperature is available it equals VCI. Below 40 means stress.",
    bins: KOGAN_BINS, value: (p) => p.vhi },
  pci: { id: "pci", label: "PCI · precipitation condition", group: "Rainfall", cadence: "monthly", unit: "0–100", decimals: 1,
    title: "Precipitation Condition Index", definition: "Month's rainfall position between its historical min and max. Below 40 means deficit.",
    bins: KOGAN_BINS, value: (p) => p.pci },
  tci: { id: "tci", label: "TCI · temperature condition", group: "Thermal & soil", cadence: "monthly", unit: "0–100", decimals: 1,
    title: "Temperature Condition Index", definition: "Where this month's Landsat land-surface temperature sits between the village's coolest and hottest value for the calendar month. Low = hotter than usual = thermal stress.",
    bins: KOGAN_BINS, value: (p) => p.tci },
  smi: { id: "smi", label: "SMI · soil moisture", group: "Thermal & soil", cadence: "monthly", unit: "0–100", decimals: 1,
    title: "Soil Moisture Index", definition: "Sentinel-1 radar (VV, 10 m) backscatter relative to the village's own lowest and highest value for the calendar month. Radar returns rise with soil wetness, so low = drier. A relative index, not volumetric soil moisture.",
    bins: KOGAN_BINS, value: (p) => p.smi },
  lst: { id: "lst", label: "Land-surface temperature", group: "Thermal & soil", cadence: "monthly", unit: "°C", decimals: 1,
    title: "Land-surface temperature (day)", definition: "Landsat 8/9 surface temperature (30 m), clear-sky daytime observations, monthly mean over the village polygon.",
    bins: LST_BINS, value: (p) => p.lst },
  base_ndvi: { id: "base_ndvi", label: "Normal NDVI for this month", group: "Baseline", cadence: "monthly", unit: "index", decimals: 3,
    title: "Baseline NDVI (μ)", definition: "Mean NDVI for this calendar month across 2016–2026: what the village normally looks like.",
    bins: NDVI_BINS, value: (p) => p.base?.ndvi_mean },
  base_rain: { id: "base_rain", label: "Normal rainfall for this month", group: "Baseline", cadence: "monthly", unit: "mm", decimals: 1,
    title: "Baseline rainfall (μ)", definition: "Mean CHIRPS rainfall for this calendar month across 2016–2026.",
    bins: RAIN_BINS, value: (p) => p.base?.rain_mean },
  z_ndvi: { id: "z_ndvi", label: "NDVI departure from normal", group: "Baseline", cadence: "monthly", unit: "z", decimals: 2,
    title: "NDVI anomaly (z-score)", definition: "(NDVI − μ) / σ for this village and calendar month. Below −1 is a moderate deficit.",
    bins: Z_BINS, value: (p) => zOf(p.ndvi, p.base?.ndvi_mean, p.base?.ndvi_std) },
  z_rain: { id: "z_rain", label: "Rainfall as % of normal", group: "Baseline", cadence: "monthly", unit: "% of μ", decimals: 0,
    title: "Rainfall vs normal", definition: "Month's rainfall as a percentage of the village's 2016–2026 mean for this calendar month.",
    bins: PCT_BINS, value: (p) => (p.rain != null && p.base?.rain_mean ? (100 * p.rain) / p.base.rain_mean : null) },
};

export const METRIC_GROUPS: MetricSpec["group"][] = ["Drought", "Rainfall", "Vegetation", "Thermal & soil", "Baseline", "Long-term"];

export function binFor(spec: MetricSpec, v: number | null | undefined): Bin | null {
  if (v == null || Number.isNaN(v)) return null;
  for (const b of spec.bins) if (v >= b.lo && v < b.hi) return b;
  return spec.bins[spec.bins.length - 1];
}

export function colorFor(spec: MetricSpec, p: ActiveVillage): string {
  const b = binFor(spec, spec.value(p));
  return b ? b.color : NO_DATA;
}

export function formatValue(spec: MetricSpec, v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "no data";
  return `${v.toFixed(spec.decimals)} ${spec.unit === "σ" || spec.unit === "z" || spec.unit === "index" || spec.unit === "0–1" || spec.unit === "0–100" ? "" : spec.unit}`.trim();
}

export { D_LABELS };

/** Map the API / dropdown index name onto a metric spec. */
export function specForIndex(index: string): MetricSpec {
  const key = index === "cdi_class" ? "cdi" : index;
  return (METRICS as Record<string, MetricSpec>)[key] ?? METRICS.cdi;
}

export function colorForIndex(index: string, v: number | null | undefined): string {
  const b = binFor(specForIndex(index), v);
  return b ? b.color : NO_DATA_COLOR;
}
