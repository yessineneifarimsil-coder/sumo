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
<!-- APPEND this entry to docs/progress_log.md -->

## 2026-08-16 — first baseline that actually runs

**What was done**

- Ran the real project files through `netconvert` → `jtrrouter` → `sumo`
  (SUMO 1.27.1) rather than reasoning about them. Four separate hard stops were
  found, each hidden behind the previous, which is why no run had ever
  completed:
  1. the network would not load at all (`Attribute 'dir' is missing in
     definition of a connection`);
  2. `time-to-teleport.stopped` is not a SUMO option, so the config itself
     failed to load;
  3. `bus25.rou.xml` was not well-formed XML (two consecutive hyphens inside a
     comment);
  4. every `bus25_retour_*` trip was unroutable (`to="E9"`), which is a hard
     abort, not a warning.
- Rebuilt the network headlessly with `netconvert --sumo-net-file`. Verified the
  E1 merge now registers at junction `-1531` and that topology is otherwise
  identical.
- Traced the long-standing empty-output problem to `from="-E1"` in `flows.xml`.
  See decisions.md.
- Replaced the copy-pasted signal template with per-junction programmes derived
  from the network's own computed logic.
- Quantified the gridlock cause: 92.4 % of generated routes contained an
  immediate U-turn.

**Result — first complete 12 h baseline**

| | loaded | inserted | completed | teleports | mean speed | mean timeLoss |
|---|---|---|---|---|---|---|
| before | 7522 | 3723 | 3500 | 1789 | 13.3 km/h | 2210 s |
| after | 7531 | 6548 | 6322 | 1531 | 25.5 km/h | 1218 s |

All 20 Bus 25 trips now complete (previously 10 of 20, with the ten return
buses silently dropped as unsorted).

**Decided**

- The zip branch is canonical. The `-E1` branch on the PC is abandoned.
- E5 stays as the Bus 25 return terminus placeholder until the SORETRAS route
  is confirmed.
- No KPI from this run is publishable. It is a working pipeline, not a
  calibrated model.

**Next**

1. Confirm the real Bus 25 western terminus (SORETRAS map or local enquiry) and
   replace E5.
2. Check `gis/RouteDeTunis_TAZ.gpkg` in QGIS — do the polygons share the
   35.78–35.82 °N error, or is only the JSON wrong?
3. Define INT_1–INT_3 and ART_1–ART_2 as an explicit junction/edge list, the way
   `scripts/roundabouts.txt` already does for rb1–rb4.
4. Raise the observed-data gap with the supervisor. There are no counts, speeds
   or delays anywhere in the project, so no calibration is currently possible
   and the proposal's calibration section cannot be substantiated.
5. Fix the two sections both numbered 3.1.3 in the proposal.
6. After the baseline is stable: the precise split of `840516306#1` at
   (2653.12, 4574.83) to move the E1 merge to its true position.
