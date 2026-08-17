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
