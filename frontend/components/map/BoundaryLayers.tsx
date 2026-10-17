"use client";

import { useEffect, useState } from "react";
import { GeoJSON } from "react-leaflet";
import type { FeatureCollection } from "geojson";

interface Props {
  showDistrict?: boolean;
  showTehsils?: boolean;
  showVillages?: boolean;
}

/**
 * Loads the three boundary layers that give the Latur map its default
 * context: district outline, tehsil subdivisions, and (optionally)
 * village points / polygons.
 *
 * Files expected under /public/data/ :
 *     latur_district.geojson   (one Polygon)
 *     latur_tehsils.geojson    (10 tehsils)
 *     latur_villages.geojson   (point layer; optional, large)
 *
 * The map still renders when a file is missing — only that overlay is
 * skipped and a one-line note appears in the browser console.
 */
export function BoundaryLayers({
  showDistrict = true,
  showTehsils = true,
  showVillages = false,
}: Props) {
  const [district, setDistrict] = useState<FeatureCollection | null>(null);
  const [tehsils, setTehsils] = useState<FeatureCollection | null>(null);
  const [villages, setVillages] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    if (showDistrict) {
      fetch("/data/latur_district.geojson")
        .then((r) => (r.ok ? r.json() : null))
        .then(setDistrict)
        .catch(() => console.info("latur_district.geojson not found; skipping district outline"));
    }
    if (showTehsils) {
      fetch("/data/latur_tehsils.geojson")
        .then((r) => (r.ok ? r.json() : null))
        .then(setTehsils)
        .catch(() => console.info("latur_tehsils.geojson not found; skipping tehsil overlay"));
    }
    if (showVillages) {
      fetch("/data/latur_villages.geojson")
        .then((r) => (r.ok ? r.json() : null))
        .then(setVillages)
        .catch(() => console.info("latur_villages.geojson not found; skipping villages"));
    }
  }, [showDistrict, showTehsils, showVillages]);

  return (
    <>
      {district && (
        <GeoJSON
          data={district}
          style={{ color: "#0f172a", weight: 2.5, fillOpacity: 0 }}
          interactive={false}
        />
      )}
      {tehsils && (
        <GeoJSON
          data={tehsils}
          style={{ color: "#1e40af", weight: 1, dashArray: "4 3", fillOpacity: 0 }}
          onEachFeature={(f, layer) => {
            const name = f.properties?.TEHSIL || f.properties?.name || "";
            if (name) layer.bindTooltip(name, { sticky: true, direction: "center" });
          }}
        />
      )}
      {villages && (
        <GeoJSON
          data={villages}
          pointToLayer={(_f, latlng) => {
            const L = require("leaflet");
            return L.circleMarker(latlng, {
              radius: 2,
              color: "#64748b",
              weight: 0.5,
              fillOpacity: 0.6,
            });
          }}
          onEachFeature={(f, layer) => {
            const name = f.properties?.VILLAGE || f.properties?.name || "";
            if (name) layer.bindTooltip(name, { direction: "top" });
          }}
        />
      )}
    </>
  );
}
