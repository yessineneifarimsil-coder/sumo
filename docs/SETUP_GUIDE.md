# Setup Guide — VS Code + Git + GitHub, from your existing folder

## What changed vs. your original flat folder

| Your file | New location | Notes |
|---|---|---|
| `routetunisraw.net.xml` | `network/` | unchanged content |
| `flows.xml` | `demand/` | **edited**: removed unused duplicate `vType bus` |
| `turnRatios.xml` | `demand/` | unchanged |
| `bus25.rou.xml` | `demand/` | unchanged |
| `feux_route_tunis.add.xml` | `signals/` | unchanged, **now actually loaded** by sumocfg |
| `routetunis.sumocfg` | `config/` | **edited**: now loads bus25 + signals, paths updated, teleport re-enabled |
| `routetunis_routes.xml` | *(don't move — regenerate)* | delete your copy, run `scripts/generate_routes.bat` instead |
| `routetunis.rou.alt.xml` | *(dropped)* | obsolete duarouter leftover — safe to delete on your PC |
| `01_master_build_digital_twin.py` | `digital_twin/` | unchanged, see its README — not wired into sumocfg |
| `routetunis_od_matrix.xml`, `routetunis_model_summary.json` | `digital_twin/` | unchanged |
| `export.json`, `json_to_osm.py`, `routetunis_raw.osm` | `gis/` | unchanged, this is Stage 0 |
| `RouteDeTunis_Complete.qgz`, `RouteDeTunis_Line.*`, `RouteDeTunis_TAZ*.{gpkg,shp,shx,dbf,prj}` | `gis/` | unchanged |
| `distance_markers.py` | `gis/` | unchanged (runs in QGIS console) |
| `roundabouts.txt` | `scripts/` | unchanged, source data for `define_traffic_control.py` |
| `routetunis_tripinfo.xml`, `routetunis_summary.xml`, `tripinfo.xml`, `summary.xml` | `outputs/` (or delete) | old outputs, regenerate with a fresh run |

## 1. Replace your working folder

Download this reorganized zip, unzip it. This becomes your new
`RouteDeTunis-SUMO` project root — you don't need to manually move files,
everything you had is already placed correctly (with the two edits noted
above).

**Delete your old flat folder's `routetunis_routes.xml` and
`routetunis.rou.alt.xml`** — don't copy them in; regenerate the former with
the script below instead.

## 2. Regenerate routes (Anaconda Prompt, from the project root)

```
scripts\generate_routes.bat
```

## 3. Test the simulation with bus + signals now active

```
sumo -c config\routetunis.sumocfg
```

Watch for any errors on load — if SUMO complains about anything in
`bus25.rou.xml` or `feux_route_tunis.add.xml`, that's new information (they
were never actually exercised together before), so don't be surprised if
something needs a small fix. Report back what you see and I'll help debug.

## 4. Open in VS Code

```
cd path\to\RouteDeTunis-SUMO
code .
```

## 5. Git + GitHub (same as before)

```
git init
git lfs install
git add .
git commit -m "Reorganize project structure, fix bus/signal loading"
```

Then either:
```
gh auth login
gh repo create RouteDeTunis-SUMO --private --source=. --remote=origin --push
```
or create an empty repo on github.com and:
```
git remote add origin https://github.com/<your-username>/RouteDeTunis-SUMO.git
git branch -M main
git push -u origin main
```

## 6. Day-to-day

```
git add .
git commit -m "short description"
git push
```
Every session, not just before meetings.
