"use client";

import { useLocale } from "@/components/i18n/LocaleProvider";

interface Props {
  index: string;
  year: number;
  month: number;
  getMapRoot: () => HTMLElement | null;
}

/**
 * PNG export: rasterises the Leaflet DOM into a PNG via html-to-image
 * on demand (lazy-loaded so it doesn't bloat first paint).
 * GeoTIFF export: hits the Go backend; the server has the raster already.
 */
export function MapExportButtons({ index, year, month, getMapRoot }: Props) {
  const { t } = useLocale();

  const exportPNG = async () => {
    const node = getMapRoot();
    if (!node) return;
    const htmlToImage = await import("html-to-image").catch(() => null);
    if (!htmlToImage) {
      alert("html-to-image not installed. Run: pnpm add html-to-image");
      return;
    }
    const url = await htmlToImage.toPng(node, { cacheBust: true });
    const a = document.createElement("a");
    a.href = url;
    a.download = `latur_${index}_${year}-${String(month).padStart(2, "0")}.png`;
    a.click();
  };

  const exportGeoTIFF = () => {
    // Backend-rendered export: /api/v1/export/geotiff/:index/:y/:m
    const u = `/api/v1/export/geotiff/${index}/${year}/${month}`;
    const a = document.createElement("a");
    a.href = u;
    a.download = `latur_${index}_${year}-${String(month).padStart(2, "0")}.tif`;
    a.click();
  };

  return (
    <div className="absolute right-3 top-16 z-[400] flex flex-col gap-1">
      <button onClick={exportPNG}
              className="rounded bg-white/90 px-2 py-1 text-xs shadow dark:bg-slate-900/90">
        PNG
      </button>
      <button onClick={exportGeoTIFF}
              className="rounded bg-white/90 px-2 py-1 text-xs shadow dark:bg-slate-900/90">
        GeoTIFF
      </button>
    </div>
  );
}
