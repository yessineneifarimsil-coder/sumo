# Modeling Decisions Log

One entry per non-obvious choice, so you can defend it in your defense.

## Bus + signals now loaded in routetunis.sumocfg
- **What**: `routetunis.sumocfg` previously only loaded
  `routetunis_routes.xml` (cars only), with `feux_route_tunis.add.xml`
  commented out and `time-to-teleport` disabled (`-1`). Reorganized to load
  `bus25.rou.xml` and the signals, and re-enabled teleport as a safety
  valve (`300`s vehicle, `180`s stopped).
- **Why**: this was flagged as likely unintentional — the bus line and
  signal coordination were built but never actually exercised in a run.
  Confirmed with supervisor-in-progress that both should be active going
  forward.
- **Side effect found and fixed**: `flows.xml` had an unused `vType id="bus"`
  identical to the one in `bus25.rou.xml`. Loading both route files together
  would throw a duplicate-vType-id error in SUMO. Removed the unused
  declaration from `flows.xml` (kept the real one in `bus25.rou.xml`, where
  it's actually referenced by the bus flows).

## Deadlocked junction(s)
- **What**: [fill in — junction ID(s), e.g. `-3115`]
- **Why**: [traffic_light vs. raised corridor priority — pick one and say
  why, e.g. "converted to traffic_light because 4+ conflicting movements
  made a static priority junction unstable under AM peak load"]
- **Alternative considered**: [the other option, and why it was rejected]
- **Interim mitigation**: `time-to-teleport` safety valve in the sumocfg
  (see above) prevents one deadlock from freezing the full 12h run while
  junctions are stabilized one at a time.

## Two parallel demand models — kept separate for now
- **What**: `demand/flows.xml` (+ `turnRatios.xml`, active, drives the real
  simulation) vs. `digital_twin/01_master_build_digital_twin.py` (TAZ + OD
  matrix + 9 vehicle types, not connected to any running simulation).
- **Why kept separate rather than merged**: undecided as of this
  reorganization whether the digital-twin track will replace `flows.xml`
  as the demand model, or serve a separate thesis phase (e.g. MCDM
  evaluation). Merging now would be premature. **Update this entry once
  decided** — it materially changes the project's demand-modeling story
  for the defense.

## Junction handling (network cleanup)
- **What**: kept the full network rather than manually pruning every branch.
- **Why**: the network is too dense to clean node-by-node by hand in
  reasonable time; the corridor and its real lateral accesses matter most
  for the thesis scope.
- **Alternative**: full manual cleanup — rejected as too time-costly and
  risked breaking real connections.

## Bus line kept in a separate file from car flows
- **What**: `bus25.rou.xml` is separate from `flows.xml`, both loaded by
  the sumocfg's `route-files`.
- **Why**: jtrrouter repairs (silently rewrites) fixed routes when they're
  mixed with turn-ratio-based flows in the same jtrrouter input, corrupting
  the bus itinerary. Keeping fixed bus routes out of the jtrrouter pipeline
  entirely and loading them directly into SUMO avoids this.

## Turn ratio calibration
- **What**: 11 major turning movements, HIGH ≈ 0.18 / MED ≈ 0.08.
- **Why**: approximates ~60% of vehicles exiting via active laterals
  (commercial/residential access) vs. ~40% through-traffic, based on
  [local knowledge / field counts / cite your source].

## E1 dead-end bug — root cause of both bus route failure and wasted ramp demand (2026-08-14)
- **What**: `E1` (used as the "east ramp" entry in `flows.xml` and as the
  first hop of the Bus 25 fixed route) leads to junction `J2`, which is
  typed `dead_end` with zero outgoing connections — confirmed by parsing
  the actual `routetunisraw.net.xml` and by inspecting the real generated
  `routetunis_routes.xml`, where every `bretelle_east_am/mid/pm` vehicle's
  route was just `<route edges="E1"/>` (spawns and immediately vanishes,
  never enters the corridor).
- **Why the June E4 fix didn't catch this**: that fix connected `E4 → E1`,
  which made jtrrouter's warning about E4 disappear. But the chain still
  dead-ends one edge further down (`E4 → E1 → J2`). The symptom (warning)
  was fixed; the underlying problem (this ramp goes nowhere) wasn't.
- **Confirmed via BFS on the real network graph** (19,646 parsed
  connections): no path exists from `E1` onward in the "into the corridor"
  direction. A reverse edge (`-E1`) does not exist. The *other* real edge
  at junction `-2948` (`189714556#0`) **does** lead into the corridor —
  BFS confirmed a 52-edge path from `189714556#0` to the main corridor
  entry `26603900#0`.
- **User confirmed**: E1 is meant to be a real entry ramp into the corridor
  (not exit-only).
- **Fix applied (pending on-PC execution)**:
  1. NetEdit: add a reverse-direction edge for E1 (creates `-E1`,
     `J2 → -2948`), then explicitly connect `-E1 → 189714556#0` at
     junction `-2948`, recompute junctions, save.
  2. `flows.xml`: changed `bretelle_east_am/mid/pm` from `from="E1"` to
     `from="-E1"`.
  3. `bus25.rou.xml`: rewritten from fixed `<route edges="...">` (which
     was never a valid connected path — see below) to `<trip from=".."
     to=".."/>` elements, letting SUMO auto-route at load time instead of
     relying on a hand-typed edge sequence that breaks on any future
     network edit.
  4. `routetunis.sumocfg`: now loads `bus25.rou.xml` and
     `feux_route_tunis.add.xml` (previously built but never active — see
     entry below), `time-to-teleport` re-enabled as a safety valve.
- **Status: NOT YET VERIFIED ON THE ACTUAL PC.** This was diagnosed and
  fixed by parsing the uploaded network file; NetEdit/jtrrouter/sumo have
  not been re-run since. Confirm with a real regenerate + run before
  treating this as resolved.

## Bus 25's original fixed route was never actually connected
- **What**: the original `<route edges="E1 245250305#20 245250305#35
  693648180"/>` was checked hop-by-hop against the real network graph.
  **None of the three consecutive edge pairs were connected** — e.g.
  `245250305#20` only connects to `-45856427#12`, `245250305#21`, and
  `-245250305#20`, never to `245250305#35`. `693648180` is also
  geographically distant (kilometers away in the network's own
  coordinates) from the other three edges.
- **Why this matches old symptoms**: this fully explains the historical
  jtrrouter warnings "Repaired route of vehicle 'bus25_aller_am.*'" —
  jtrrouter was silently discarding the literal edge list and improvising
  a path, because the specified sequence was never valid to begin with.
- **Fix**: switched to `<trip>`-based routing (see above) — a real
  82-edge path from `189714556#0` to `693648180` was confirmed to exist
  via BFS, so once `-E1` is created, SUMO's internal router should be able
  to connect Bus 25 automatically.

## E1 merge point fix — pragmatic node consolidation (2026-08-14)
- **What**: E1 was retargeted from the fictional dead-end `J2` to the real
  junction `-1531` on `840516306#1` (Route de Tunis), with shape/length
  trimmed accordingly, and a new connection `E1 → 840516306#1` added.
  `J2` removed (orphaned).
- **Why `-1531` instead of the exact real-world merge point**: the user
  confirmed the real slip road actually merges ~113m further along the
  same edge than `-1531`, at the coordinates originally assigned to their
  hand-built `J2` node (`2653.12, 4574.83`). `840516306#1` is a single
  edge with no intermediate junction between `-1531` and that point, so
  snapping the merge to `-1531` is a **node consolidation** — standard
  practice in digital-twin/network modeling when a real merge point falls
  mid-edge rather than at an existing node. Since there's no cross-street
  in between, this doesn't materially change corridor-level behavior
  (travel time, throughput) — it would only matter for a study that
  specifically analyzes weaving/conflict dynamics at that exact merge.
- **Status: edit made via direct XML patch (not yet run through NetEdit's
  Compute Junctions / not yet verified by the user).** The new connection
  was added WITHOUT `via`/`dir`/`state` attributes (internal-lane/
  right-of-way encoding that's normally auto-generated) — deliberately,
  to avoid hand-faking junction internals. **Required next step**: open in
  NetEdit, press F5 (Compute Junctions), visually verify the merge at
  `-1531` looks correct and flows in the right direction, save, then
  regenerate routes and re-run the simulation.
- **Planned follow-up (after baseline confirmed working)**: do the
  precise version — actually split `840516306#1` at
  `(2653.12, 4574.83)` (J2's original coordinates, ~21m from an existing
  shape point on that edge) to create a real junction exactly where the
  slip road merges in reality, rather than the ~113m-early approximation.
  Not done yet by mutual agreement — get a working baseline first, refine
  precision later.

## Zero-output baseline run (2026-06-19)
- **What**: the most recent `routetunis_tripinfo.xml` /
  `routetunis_summary.xml` (dated June 19, 2026, right after the E4 fix)
  contain zero vehicle/timestep entries — the run produced no usable data.
- **Likely explanation**: at least partly explained by the E1 bug above —
  a meaningful share of demand was silently vanishing on a single dead-end
  edge — but this alone wouldn't cause literally zero output for the
  *whole* run, since `main_am`/`main_mid`/`main_pm` route correctly. More
  likely the GUI run was closed before completion, or another load error
  occurred. **Needs a fresh run to diagnose properly** — not yet resolved.

## Network cleanup + E4 connection repair (June 2026)
- **What**: `netconvert --remove-edges.isolated` run on the network
  (removed 11 unjunctioned roads), plus a manual fix in NetEdit for edge
  E4 → junction -2948, which had no valid outgoing connection.
- **Why**: isolated edges and the broken E4 connection were generating
  jtrrouter warnings and likely contributing to routing/deadlock issues.
- **Status**: treated as repaired based on a handover document's account
  and consistent file timestamps (network + regenerated routes both dated
  2026-06-19), but **not independently re-verified in this session** —
  re-check with Select Dead Ends in NetEdit before relying on it, and
  re-verify after any further topology edits.
- **Not yet done**: a dated backup of `routetunisraw.net.xml` was
  recommended before this kind of in-place edit
  (`copy routetunisraw.net.xml routetunisraw_before_cleanup.net.xml`) —
  confirm one exists; if not, back up the *current* file now before any
  further network changes.

## Edge-ID validity — not yet checked against current network
- **What**: `turnRatios.xml`'s 11 `from`/`to` edge pairs and the bus25
  fixed-route edge sequences (`E1 245250305#20 245250305#35 693648180`,
  reverse) have not been programmatically verified to still exist and
  connect correctly in the current `routetunisraw.net.xml`.
- **Why it matters**: earlier jtrrouter logs showed "Repaired route of
  vehicle 'bus25_aller_am.*'" warnings, meaning at least one edge pair in
  the fixed bus route wasn't properly connected at that time. Unclear if
  this was fixed by the later netconvert/E4 work or is still open.
- **Action needed**: run the bus routes and turn ratios against the
  current network (e.g. inspect in NetEdit, or check duarouter/jtrrouter
  output for repair warnings) before treating Bus 25 or the turn-ratio
  calibration as validated.

## Obsolete file dropped: routetunis.rou.alt.xml
- **What**: not carried into the reorganized structure.
- **Why**: this was the alternate-routes output from an earlier duarouter
  run (`routetunis.trips.xml` → duarouter → `routetunis.rou.xml`,
  2025-12-20), from before the switch to the jtrrouter + turnRatios
  pipeline. Superseded; the current pipeline is documented in
  `scripts/generate_routes.*`.
<!-- APPEND these entries to docs/decisions.md, after the existing sections. -->

## E1 merge recomputed headlessly instead of via NetEdit F5
- **What**: the hand-added `<connection from="E1" to="840516306#1"/>` had no
  `via`/`dir`/`state`, and junction `-1531` had no `E1_0` in its `incLanes`.
  Rebuilt the network with
  `netconvert --sumo-net-file routetunisraw.net.xml -o routetunisraw_recomputed.net.xml`.
- **Why**: this was not an optional tidy-up. Every SUMO runtime tool rejected
  the file outright — `Error: Attribute 'dir' is missing in definition of a
  connection. Quitting (on error).` Nothing could run until the internal lanes
  and right-of-way were regenerated. `netconvert --sumo-net-file` uses the same
  importer NetEdit does, so it is the headless equivalent of Compute Junctions.
- **Verification**: topology is unchanged — 3269 edges, 1424 junctions, 8542
  connections, 7 tlLogic before and after, zero added, zero removed. Only
  internal lanes and right-of-way were regenerated. The connection came back as
  `via=":-1531_0_0" dir="s" state="m"`, i.e. minor priority, so the slip road
  yields to Route de Tunis. Correct for a merge.
- **Still outstanding**: the merge sits 113 m short of J2's true position
  (2653.12, 4574.83). The precise split of `840516306#1` at those coordinates is
  still the planned follow-up.

## Root cause of the empty baseline outputs
- **What**: `flows.xml` on the PC had `from="-E1"` on all three
  `bretelle_east_*` flows. That edge exists in no version of the network.
- **Why it mattered**: jtrrouter does not skip an unroutable flow, it aborts the
  entire build and writes an empty `<routes/>`. One wrong edge ID cost all 7,511
  vehicles. sumo-gui then loaded, had nothing to run, and was closed by hand,
  leaving 1,091/1,096-byte header-only output files. That is what "empty
  outputs" meant — a load-time failure, not a simulation that ran without
  vehicles.
- **Provenance**: `-E1` is documented in an old `bus25.rou.xml` comment as "the
  new reverse edge created in NetEdit". It was never present in any saved
  network. Either the NetEdit save was lost or the edge was never created.
- **Decision**: the zip branch (`E1`, not `-E1`) is canonical as of 2026-08-16.
  The `-E1` branch is abandoned.

## time-to-teleport.stopped removed from the config
- **What**: `<time-to-teleport.stopped value="180"/>` deleted.
- **Why**: it is not a SUMO option. `Error: No option with the name
  'time-to-teleport.stopped' exists. Could not load configuration.` The valid
  suffixes are `.highways`, `.highways.min-speed`, `.disconnected`, `.remove`,
  `.remove-constraint`, `.ride`, `.bidi`, `.railsignal-deadlock`. Plain
  `time-to-teleport=300` is retained as a safety valve, not a fix.

## sumocfg paths made relative to the config file
- **What**: all paths in `routetunis.sumocfg` now read `../network/...`,
  `../demand/...`, `../routes/...`, `../signals/...`, `../outputs/...`.
- **Why**: SUMO resolves relative paths against the location of the config file,
  not the working directory. Bare filenames only worked when everything sat in
  one flat folder, which the structured layout no longer does. This version runs
  correctly from any working directory.

## bus25.rou.xml sorted by departure time
- **What**: `aller` and `retour` trips were listed in two separate blocks, each
  starting at 25200 s. Now interleaved in ascending `depart` order.
- **Why**: SUMO does not reorder route files. It emitted
  `Warning: Route file should be sorted by departure time, ignoring
  'bus25_retour_am.N'` and **silently dropped all ten return buses**. After
  sorting, all 20 bus trips complete.

## bus25 return terminus set to E5 as a placeholder
- **What**: `to="E9"` replaced with `to="E5"` on all ten `retour` trips.
- **Why**: E9 is a one-way entry ramp. Its only incoming edge is `96146991#2`,
  which is not reachable from the corridor's east end, so E9 cannot be a
  destination. SUMO agreed: `No connection between edge '693648180' and edge
  'E9' found` → `has no valid route` → hard abort at t≈28980. E5 is reachable
  from `693648180` and its end lies ~48 m from E1's origin junction `-2948`,
  making it the geometric mirror of the E1 entry.
- **Status**: PLACEHOLDER, not a surveyed terminus. To be replaced once the
  SORETRAS route is confirmed. `export.json` contains no bus infrastructure at
  all — 1,455 elements, all `way`, all tagged `highway`, no relations, no tagged
  nodes — so the real terminus cannot be derived from the current data sources.

## Signal programmes rebuilt per junction
- **What**: `feux_route_tunis.add.xml` replaced by `feux_corrected.add.xml`.
- **Why**: the old file applied one 16-character phase template to all three
  junctions, but `-3115` has 6 signals and `-3121` has 7. SUMO tolerated this
  with `Unused states in tlLogic ... after tl-index 5`, so it did not block a
  run, but the surplus characters were meaningless and the template also
  produced conflicting `G` greens (`Lane '1190751094_0' is targeted by 2
  'G'-links`). Not defensible in a published result.
- **How the new file was built**: state strings taken verbatim from the
  network's own computed logic, so each is the correct width for that junction's
  link indices, with lowercase `g` restored for permissive movements. A 4 s
  all-red clearance phase is appended. Cycle is 90 s everywhere so the
  0 / 15 / 30 offsets coordinate.
- **Splits**: `-3121` and `-5174` get the intended 50/30 major-minor split,
  assigned by checking each phase's controlled links against the approach road
  class (`highway.primary` vs `highway.service` / `highway.secondary`).
  `-3115` is kept at 40/40 because both of its approaches are Route de Tunis in
  opposite directions — there is no minor road there to favour.
- **Conflict-free links held green**: at `-3115` link 0 and at `-3121` link 5
  are green in all four computed phases, because netconvert found them
  conflict-free. They are deliberately left green through the all-red clearance.
  Clearing them would cost capacity for no safety gain, and forcing them to
  yellow triggered `Missing yellow phase ... when switching to phase 4`.
- **Result**: loads with zero traffic-light warnings.

## jtrrouter turnaround weight set explicitly to zero
- **What**: routes are now generated with
  `--remove-loops --turn-defaults 15,80,5,0`.
- **Why**: 92.4 % of generated routes (6,940 of 7,511) contained an edge
  immediately followed by its own reverse — an instant U-turn. The fourth value
  in `--turn-defaults` is the turnaround weight; omitting it lets jtrrouter
  U-turn freely. Measured effect: 92.4 % → 73.6 % with `--remove-loops` alone,
  → 69.7 % with `15,80,5`, → 59.1 % with `15,80,5,0`.
- **Honest limitation**: this is mitigation, not a fix, and no KPI from it is
  publishable. 59 % U-turns is still absurd. With 11 `edgeRelation` entries
  across 3,269 edges, jtrrouter is guessing at essentially every junction, and
  22 edges are outright dead ends, so vehicles routed into a stub have no legal
  move except to reverse. Random turn-ratio routing is the wrong demand model
  for this network; the OD/TAZ track is the right one.

## Digital-twin TAZs are geo-referenced ~85 km north of the network
- **What**: every TAZ centroid in `digital_twin/routetunis_model_summary.json`
  lies between 35.78 and 35.82 °N. The network's `origBoundary` is
  `10.733148, 34.735388, 10.786732, 35.036069` and never reaches 35.04.
- **Why it matters**: those zones cannot map onto any edge in the network, which
  is the mechanical reason the digital-twin track was never wired into the
  active sumocfg. Sfax is at 34.74 °N; 35.8 °N is near Sousse.
- **Same error elsewhere**: the thesis proposal states a bounding box of
  35.78–35.82 °N, so this is one root cause, probably a single mistyped
  latitude that propagated into both artefacts.
- **Open**: whether `gis/RouteDeTunis_TAZ.gpkg` polygons share the error or are
  correctly placed. To be checked in QGIS.
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
Corridor length corrected to 12.42 km, 17 Aug 2026. Summing SUMO <edge> lengths gives 10.43 km, but that omits the internal lanes inside junctions — 1.99 km across 159 junctions, mean 12.6 m each. The error was caught by a geometry sanity check: the corridor endpoints are 12.15 km apart in a straight line, and a road cannot be shorter than the straight line between its ends. Detour ratio is now 1.02. Free-flow travel time is 14.8 min, not 12.2. The original "13 km" project figure was closer to correct than the 10.4 km correction that briefly replaced it. scripts\travel_time_calibration.py::measure_corridor now computes this properly and its self-test prints the old figure as IMPOSSIBLE so it cannot be reintroduced.
