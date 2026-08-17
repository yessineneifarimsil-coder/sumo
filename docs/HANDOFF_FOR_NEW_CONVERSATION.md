# Route de Tunis SUMO Model — Handoff for New Claude Conversation

Read this first, in full, before touching any file. This project has a
history of assumptions being made without verification — don't repeat that.
Every claim below marked "confirmed" was checked directly against the real
uploaded files in a previous session (grep/BFS on the actual network XML,
not inference). Claims marked "pending" are not yet verified — say so if
asked, don't assume they're resolved.

## 0. How to work with this user

- The person is a PhD student (Sfax, Tunisia, now partly working from
  France) building this model for their thesis. Their written English has
  frequent typos/phonetic spelling ("te" for "the", "ave" for "have",
  "u" for "you") — read past this fluently, don't comment on it, don't
  mirror it back.
- They work in **Anaconda Prompt** (Windows) for `jtrrouter`/`sumo`/
  `netconvert` commands, and **NetEdit** (GUI) for network topology edits.
  Project folder: `C:\Users\LENOVO\SUMO_Projects\RouteDeTunis\`
- **You (Claude) cannot control their screen or run NetEdit/sumo yourself.**
  No live PC access. Everything is upload → analyze → instruct or
  edit-and-hand-back → they execute → they report back. Be explicit about
  this limitation rather than implying you can "just do it."
- **You CAN and should directly edit their XML/config files** when you
  have the actual file content uploaded — this project has shown that
  hand-verifying against the real network (grep, BFS on connections) finds
  real bugs that guessing from documentation never would. Prefer this over
  giving click-by-click NetEdit instructions when a direct file edit is
  possible and safe.
- When editing the compiled `.net.xml` directly: safe to edit `<edge>`
  targets, shapes, and add plain `<connection from=".." to=".."
  fromLane=".." toLane=".."/>` elements WITHOUT `via`/`dir`/`state`
  attributes (those encode auto-generated internal-lane/right-of-way
  logic — don't hand-fake them). Always tell the user to open the result
  in NetEdit and press **F5 (Compute Junctions)** before saving, so the
  internals get regenerated properly. Always validate the edited XML is
  well-formed before handing it back.
- Attached zip (`RouteDeTunis-SUMO-organized.zip`) already reflects the
  current best-known state, including the pending E1 fix. Don't
  re-organize from scratch — extend what's there.

## 1. Project identity

- PhD thesis, microscopic SUMO model, ~13 km urban corridor "Route de
  Tunis," Sfax, Tunisia.
- Simulation window: 07:00–19:00 (25200–68400 s).
- Goal: stable, documented, warning-free baseline first; calibration and
  KPI extraction second; traffic-management/infrastructure scenarios and
  TraCI-based control third.

## 2. Architecture (confirmed)

```
OSM export.json --(gis/json_to_osm.py)--> routetunis_raw.osm
    --(NetEdit/netconvert)--> network/routetunisraw.net.xml
                                      |
demand/flows.xml + demand/turnRatios.xml
                                      |
                                  jtrrouter
                                      |
                          routes/routetunis_routes.xml (GENERATED,
                                   not committed, regenerate via
                                   scripts/generate_routes.*)
                                      |
config/routetunis.sumocfg  <--  demand/bus25.rou.xml
        + signals/feux_route_tunis.add.xml
                                      |
                              sumo / sumo-gui
                                      |
                    outputs/routetunis_tripinfo.xml, _summary.xml
```

A second, parallel, **unconnected** demand-modeling track exists in
`digital_twin/` (TAZ zones, OD matrix, 9 vehicle types) — not wired into
the active sumocfg. Its future role (replace `flows.xml`, or separate
thesis phase e.g. MCDM) is **undecided** — don't merge it in without
asking.

## 3. Current state of core files (as of this handoff)

| File | Status |
|---|---|
| `demand/flows.xml` | Fixed and current: chronologically ordered, `bretelle_east_*` uses `from="E1"` (confirmed correct after the E1 fix below), no duplicate vType |
| `demand/bus25.rou.xml` | Rewritten from a broken fixed-route to `<trip from=".." to=".."/>` auto-routing (see §4) |
| `network/routetunisraw.net.xml` | **Contains a pending, unverified fix** — see §4. Everything else in it reflects the June 2026 netconvert cleanup + E4 repair (confirmed present) |
| `config/routetunis.sumocfg` | Now loads `bus25.rou.xml` + `feux_route_tunis.add.xml` (previously built but never active), `time-to-teleport=300/180` re-enabled |
| `outputs/routetunis_tripinfo.xml`, `_summary.xml` | **Empty as of the last real run (2026-06-19)** — zero vehicles/timesteps logged. Baseline has never produced usable KPI data. **Unresolved** — needs a fresh run and diagnosis once the E1 fix is verified. |

## 4. The E1 bug — most important open thread, read carefully

This was manually built by the user (not from OSM) to represent a slip
road ("bretelle" — here literally a bridge/overpass, not just a ramp)
because OSM doesn't cleanly capture this interchange.

- **Confirmed problem**: `E1` originally ended at a hand-built node `J2`
  with zero outgoing connections — a genuine dead end in the graph. Every
  `bretelle_east_*` vehicle got a single-edge route (`edges="E1"`) and
  vanished without entering the corridor. This also broke Bus 25's fixed
  route (`E1 → 245250305#20 → 245250305#35 → 693648180`), which was
  independently confirmed via BFS to never have been a valid connected
  path at any point (not even before this bug — that original route was
  fictional).
- **User's real-world design intent (confirmed by them directly)**: this
  is a real interchange. Vehicles from junction `-2948` either continue
  onto `E1` (the slip road, in reality a bridge/overpass) to merge onto
  Route de Tunis, or turn right onto a different road entirely (not yet
  modeled). `J2` was meant to represent the point where the slip road
  touches Route de Tunis. `E0` (a separate edge, `J1 → -2990`) is the
  roundabout's right-turn exit. A second merge point exists on "the road
  under the slip road from the left," confirmed to be the already-working
  `E9` edge (west side, already correctly connected — no fix needed
  there). The slip-road-over-the-road movement (straight over the bridge)
  uses an edge the user hasn't built yet — not blocking, out of scope for
  now.
- **Root-cause geometry (confirmed via coordinates)**: `J2`
  (`2653.12, 4574.83`) sits ~21m from a shape point on real edge
  `840516306#1` (`type="highway.primary"`, i.e., actually Route de Tunis)
  — mid-segment, not at either of that edge's endpoint junctions (`-1531`,
  113m away; `-4087`, 231m away). So `J2` really is roughly where the
  user says it is in reality — the network just never had a node there to
  connect it to.
- **Fix applied (PENDING VERIFICATION — do not assume this works)**:
  Rather than the "correct" fix (splitting `840516306#1` exactly at J2's
  coordinates), a pragmatic **node consolidation** was made: `E1`
  retargeted from `J2` to the existing junction `-1531` instead (113m
  short of the true merge point), since there's no intermediate junction
  on that stretch so this doesn't materially affect corridor-level
  behavior. Concretely, in `network/routetunisraw.net.xml`:
  - `<edge id="E1">`'s `to` changed from `J2` to `-1531`, shape/lane
    trimmed to match
  - `J2` junction removed (orphaned)
  - New connection added: `<connection from="E1" to="840516306#1"
    fromLane="0" toLane="0"/>` — **without** `via`/`dir`/`state`
    (needs NetEdit to regenerate those)
- **What must happen next, in order**:
  1. User opens this network file in NetEdit, presses **F5** (Compute
     Junctions), visually verifies the merge at `-1531` looks correct
     and points the right direction, saves.
  2. Regenerate routes: `jtrrouter --net-file routetunisraw.net.xml
     --route-files flows.xml --turn-ratio-files turnRatios.xml
     --accept-all-destinations --output-file routetunis_routes.xml
     --begin 25200 --end 68400` — should complete with **no** "Repaired
     route" warnings for bus25 vehicles, and `bretelle_east_*` should get
     real multi-edge routes (compare with `bretelle_west_*`, which
     already works, as a sanity check).
  3. Run `sumo -c routetunis.sumocfg`, confirm
     `routetunis_tripinfo.xml`/`_summary.xml` are **non-empty** this
     time — this may also resolve the separate zero-output issue (§3),
     or that may need independent diagnosis if it doesn't.
  4. **If NetEdit throws an error on load, or the recomputed junction
     looks wrong**: this is useful information, not a failure — ask for
     a screenshot/error text and debug from there. Don't assume the
     patch is broken without evidence, but don't assume it's fine either.
- **Planned follow-up, after the baseline above is confirmed working**:
  do the precise fix — actually split `840516306#1` at J2's original
  coordinates (`2653.12, 4574.83`) to place the merge exactly where it
  belongs in reality, rather than the 113m-early approximation. The user
  explicitly asked to do this *after* getting a working baseline first.
  This was the next planned task when this handoff was written.

## 5. Other confirmed-good things (don't re-verify these)

- All 21 `turnRatios.xml` edge IDs exist in the current network.
- All `flows.xml` entry edges exist.
- `flows.xml` is chronologically ordered (AM → MID → PM) — the historical
  "route file should be sorted" warning does not apply to the current file.
- E4's connection to `-2948`/onward exists (June 2026 repair confirmed
  present in the network).
- E9 (west ramp) generates real, correct multi-edge routes already.

## 6. Known still-open issues (don't consider these resolved)

1. **Zero-output baseline run** (§3) — needs a fresh run after the E1 fix
   is verified; may or may not resolve on its own.
2. **E1 fix itself** — pending user verification in NetEdit (§4).
3. **Digital twin track's role** — undecided (replace `flows.xml`, or
   separate thesis phase). Don't merge without asking.
4. **Precise E1 split** — planned, not started (§4, follow-up item).
5. Side-road terminal edges elsewhere in the network — not audited beyond
   E1. Don't assume other dead ends are bugs OR are fine; check if asked.
6. Deadlocked junction(s) mentioned in earlier project history — a
   specific node ID was never pinned down. `time-to-teleport` is the
   current safety valve, not a real fix.
7. Geometry warnings from the June netconvert cleanup (sharp turns,
   speed reductions) — not reviewed for whether any fall on the corridor
   itself.

## 7. Immediate next steps, in order

1. Get the user's post-NetEdit-verification network file and terminal
   output from steps in §4.
2. Confirm or debug the E1 merge.
3. Confirm or diagnose non-empty simulation output.
4. Once stable: do the precise E1 split (§4 follow-up).
5. Extract real KPIs from a full 12h run, compare to any field data the
   user has.
6. Revisit the digital-twin track decision.
7. Only after a stable, documented baseline: move to TraCI integration
   (`scripts/traci/run_simulation.py` already scaffolded) and thesis
   scenario comparisons.

## 8. Files to attach in the new conversation

Send, in this order:
1. **This document**
2. `RouteDeTunis-SUMO-organized.zip` — the full organized project,
   including the pending-fix network file, updated `decisions.md` (full
   verified history) and `progress_log.md`
3. Whatever NetEdit produces after step §4.1 (the post-F5 network file) —
   if this hasn't happened yet, send the current network as-is and say so
4. Terminal output from the jtrrouter regeneration and sumo run, once run
