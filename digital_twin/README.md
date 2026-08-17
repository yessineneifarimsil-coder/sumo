# Digital Twin track — status: NOT connected to the active simulation

This folder holds a separate, more detailed demand-modeling approach:

- `01_master_build_digital_twin.py` — defines 8 TAZs with population/land-use
  data, 9 vehicle types with driver-behavior parameters (aggressive/normal/
  cautious car drivers, taxis, 2 bus types, 2 truck types, motorcycles), and
  a peak-hour (08:00–09:00) origin-destination matrix. Generates
  `routetunis_od_matrix.xml` and `routetunis_model_summary.json`.

**As of the last reorganization, nothing in `config/routetunis.sumocfg`
loads these files.** The active simulation uses the simpler `demand/flows.xml`
+ `demand/turnRatios.xml` → jtrrouter pipeline instead (see main README).

## Why this is kept separate rather than merged

This wasn't a clear-cut decision, so it's parked here rather than guessed at:

- It could become the **replacement** demand model (richer, OD-matrix-based,
  more realistic driver heterogeneity) once the base corridor is stable.
- Or it could be a **separate deliverable** for a later thesis phase (e.g.
  a fuzzy-MCDM ITS evaluation, which was mentioned in earlier planning
  notes as a "Phase 3" item, distinct from the base traffic simulation).

**Decide and document this in `../docs/decisions.md` once you know** —
until then, treat this folder as reference work-in-progress, not part of
the reproducible pipeline in `scripts/generate_routes.*`.

## If you want to wire it in later

You'd need an OD-matrix-to-routes step (SUMO's `od2trips` + `duarouter`,
not `jtrrouter`, since `jtrrouter` works from turn ratios, not an OD
matrix), producing a routes file that would replace (not add to)
`routes/routetunis_routes.xml` in the sumocfg.
