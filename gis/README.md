# GIS / network-sourcing pipeline

This is Stage 0 — where `network/routetunisraw.net.xml` came from, and the
QGIS-side spatial analysis, kept separate from the SUMO simulation files.

## Pipeline order

1. **`export.json`** — raw Overpass API query result (OSM data for the
   corridor), pulled 2025-12-14.
2. **`json_to_osm.py`** — converts `export.json` into standard OSM XML.
   Run: `python json_to_osm.py` → produces `routetunis_raw.osm`.
3. **`routetunis_raw.osm`** — standard OSM file, then imported into
   NetEdit/netconvert to build `../network/routetunisraw.net.xml`.

## QGIS project

- **`RouteDeTunis_Complete.qgz`** — the QGIS project file tying the layers
  below together.
- **`RouteDeTunis_Line.*`** (shp/shx/dbf/prj) — corridor centerline, used
  for spatial reference (e.g. distance markers).
- **`RouteDeTunis_TAZ.gpkg`**, **`RouteDeTunis_TAZ_buffered.*`** — TAZ zone
  geometries (buffered version = zones expanded by a margin, likely for
  catchment-area analysis). These are the spatial counterpart to the TAZ
  *data* (population, land use) defined in `../digital_twin/`.
- **`distance_markers.py`** — QGIS **Console** script (run inside QGIS's
  Python console, not standalone) — generates 1km interval markers along
  the corridor centerline.
