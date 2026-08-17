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
