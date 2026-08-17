# Progress Log

Keep this updated after each work session — it becomes the raw material for
your rapport d'avancement and defense.

## Format
```
## YYYY-MM-DD
- What you did
- What you decided and why
- What's next
```

---

## Stage 0 — Network sourcing (gis/)
- Pulled corridor OSM data via Overpass API → `gis/export.json`
  (2025-12-14).
- Converted to standard OSM via `gis/json_to_osm.py` → `gis/routetunis_raw.osm`.
- Imported into NetEdit, cleaned geometry → `network/routetunisraw.net.xml`.
- Built QGIS project (`gis/RouteDeTunis_Complete.qgz`) with corridor
  centerline and TAZ geometries; `gis/distance_markers.py` generates 1km
  markers along the corridor.

## Phase 1 — Network construction
- Network validated: ~1,669 nodes, 2,341 edges (per earlier inventory).

## Phase 2 — Demand and calibration (active pipeline)
- `demand/flows.xml`: main corridor flow (AM 1200, midday 800, PM 1300
  veh/h) plus 5 lateral entries and 2 ramp flows (E1/E9).
- `demand/bus25.rou.xml`: line 25, 10 aller + 10 retour, AM peak, corridor
  → Technopole. Kept separate from `flows.xml` (see `decisions.md`).
- `demand/turnRatios.xml`: 11 major turning movements calibrated
  (HIGH ≈ 0.18, MED ≈ 0.08), giving ~60% of vehicles exiting via laterals.
- Routes generated via `scripts/generate_routes.*` (jtrrouter) →
  `routes/routetunis_routes.xml` (reproducible, not committed).
- `signals/feux_route_tunis.add.xml`: 3 coordinated signalized junctions
  (50s/30s split, offsets 0/15/30s).
- Earlier duarouter-based attempt (`routetunis.trips.xml` → duarouter)
  superseded and dropped — see `decisions.md`.

## Phase 2 (parallel) — Digital twin demand model
- `digital_twin/01_master_build_digital_twin.py`: 8 TAZs with population/
  land-use data, 9 vehicle types with driver-behavior variation, peak-hour
  OD matrix (08:00–09:00).
- **Not yet connected to the active simulation** — status tracked in
  `digital_twin/README.md` and `decisions.md`.

## Phase 2B.5 — Network cleanup + E4 repair (June 2026)
*(Reconstructed from a Perplexity-authored handover doc, not verified
first-hand — confirm against the actual local network file.)*
- Ran `netconvert --sumo-net-file routetunisraw.net.xml --remove-edges.isolated`
  — removed 11 roads without junctions. Produced non-fatal geometry
  warnings (sharp turns, reduced connection speeds) — worth a pass to
  check if any fall on the study corridor itself.
- Identified edge **E4** reaching junction **-2948** with no valid outgoing
  logical connection. Fixed manually in NetEdit (Edit Connections mode);
  verified via Select Dead Ends that E4 no longer appears.
- Regenerated `routetunis_routes.xml` after the fix — jtrrouter completed
  with no E4-related warning.
- File timestamps support this already being reflected in the network you
  uploaded (`routetunisraw.net.xml` dated 2026-06-19, `routetunis_routes.xml`
  regenerated right after) — but this hasn't been independently confirmed,
  only inferred from dates.

## Phase 2C — Junction stabilization / config fixes
- Identified at least one deadlocked junction under load.
- Reorganization pass: discovered `bus25.rou.xml` and
  `feux_route_tunis.add.xml` were built but not actually loaded by
  `routetunis.sumocfg`; `time-to-teleport` was disabled. Fixed — see
  `decisions.md`.
- Fixed a latent duplicate-vType-id bug (`bus` defined in both
  `flows.xml` and `bus25.rou.xml`) before it caused a load error.
- Real junction fix (per junction): either convert to `traffic_light` or
  raise `priority` on the corridor edges relative to side edges, then
  recompute junctions in NetEdit. [Fill in specific junction IDs as
  resolved.]

## Verification pass (2026-08-14) — real evidence, not inference
- Parsed the actual `routetunisraw.net.xml` (19,646 connections) and cross
  checked every edge ID in `turnRatios.xml`, all flow entry edges, and the
  Bus 25 fixed route against it.
- Found: **E1 is a genuine dead-end** (`J2` is `dead_end` type, zero
  outgoing connections). Confirmed via the real generated
  `routetunis_routes.xml`: `bretelle_east_*` vehicles get single-edge
  routes (`edges="E1"`) — they never entered the corridor. This silently
  wasted ~140 veh/day of ramp demand and was the root cause of Bus 25's
  route failure too (its first hop was `E1 → ...`).
  See `decisions.md` for full detail and the fix (new reverse edge `-E1`,
  `flows.xml` updated, `bus25.rou.xml` rewritten to use `<trip>` auto-routing).
- Found: Bus 25's original fixed route was **never a valid connected
  path** at any point — none of its 3 edge pairs connect in the real
  network. Confirmed via BFS.
- Found: last real run's outputs (`routetunis_tripinfo.xml` /
  `routetunis_summary.xml`, dated 2026-06-19) are **completely empty** —
  zero vehicles, zero timesteps. Baseline has never actually produced
  usable KPI data. Not yet resolved — needs a fresh run.
- **Status: fixes drafted, not yet executed/verified on the actual PC.**
  Waiting on: NetEdit reverse-edge creation, route regeneration, and a
  full `sumo -c routetunis.sumocfg` run with output confirmed non-empty.

## Next
- Finish stabilizing remaining critical junctions.
- Run a clean 12h reference simulation with bus + signals now active,
  extract KPIs (speed, delay, queue length, throughput).
- Calibrate against field observations.
- Decide the digital-twin track's role (replace `flows.xml` vs. separate
  thesis phase) and document in `decisions.md`.
- Begin TraCI integration (`scripts/traci/run_simulation.py`).
