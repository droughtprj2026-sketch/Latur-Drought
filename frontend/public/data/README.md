# frontend/public/data

Static vector files the dashboard fetches directly in the browser.

| File | What | Replace with |
| ---- | ---- | ------------ |
| `latur_district.geojson` | District outline | Real Survey of India shapefile → GeoJSON (EPSG:4326) |
| `latur_tehsils.geojson`  | 10-tehsil overlay | Real tehsil shapefile → GeoJSON (property `TEHSIL` for the name) |
| `latur_villages.geojson` | Village points (optional, large) | Village point layer; property `VILLAGE` for the name |

**All current files are placeholders** with rectangular bounding boxes
drawn around approximate centroids. Replace them with the real
shapefiles converted to GeoJSON — e.g.

```bash
ogr2ogr -f GeoJSON -t_srs EPSG:4326 \
    latur_tehsils.geojson your_shapefile.shp
```

The map code only cares about the property keys shown above; the
features themselves can be MultiPolygon and have any extra attributes
you like.
