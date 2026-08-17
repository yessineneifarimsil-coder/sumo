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
