"""
Travel-time calibration for the Route de Tunis corridor.

Written for the actual situation described in the 17 Aug 2026 handoff:
  - no counts, no observed speeds, no signal timings
  - researcher in Paris, no field access
  - therefore: travel time is the ONLY calibration channel available

WHAT THIS FILE DELIBERATELY DOES NOT CONTAIN
--------------------------------------------
There is no GEH function here. GEH is defined for hourly FLOWS. With no
counts, GEH is not available to this project at any threshold. A GEH number
reported before counts exist would be fabricated. That is the single most
important design decision in this file.

Replaces the GEH-centred parts of validation_corrected.py, which assumed
count data that does not exist here.

Order of use:
    1. measure_corridor()     -- settle the 10.43 vs 12.13 km contradiction
    2. corridor_endpoints_lonlat()  -- get query points that match the model
    3. [collect TomTom Route Analysis observations]
    4. demand_audit()         -- gate every run
    5. extract_corridor_travel_times() / extract_segment_speeds()
    6. validate()             -- against pre-declared acceptance criteria

Requires: numpy, pandas, and pyproj for the coordinate step.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Network projection, from the net file header.
UTM_PROJ = "+proj=utm +zone=32 +ellps=WGS84"
NET_OFFSET = (-658474.70, -3845117.23)


# ---------------------------------------------------------------------------
# 0. Settle the geometry before anything else
# ---------------------------------------------------------------------------

def measure_corridor(net_file: str | Path, edge_ids: list[str]) -> dict:
    """Measure the true driven length of an ordered corridor path.

    RESOLVED 17 Aug 2026. The contradiction this function was written to
    detect was real, and the earlier 10.43 km figure was the wrong one.

    Summing <edge> lengths alone UNDERSTATES the driven distance, because it
    omits the internal lanes inside junctions. On this corridor that is
    1.99 km across 159 junctions, averaging 12.6 m each:

        sum of edge lengths      10.43 km
        junction internal lanes   1.99 km
        true driven length       12.42 km
        straight line            12.15 km   -> detour ratio 1.02, plausible

    So the corridor is 12.4 km, and free-flow is 14.8 min, not 12.2 min. Use
    those. `edge_ids` must be the ORDERED path, not a set, because the
    internal lane between consecutive edges is found via the <connection>
    'via' attribute.

    Note the 21 northbound edges carrying a '-' prefix: OSM way direction
    alternates along this corridor, so any filter of the form
    `if not eid.startswith('-')` is wrong. Pass the explicit ordered list.
    """
    root = ET.parse(str(net_file)).getroot()
    ordered = list(edge_ids)
    wanted = set(ordered)
    per_edge, per_edge_speed, all_lanes = {}, {}, {}

    for edge in root.iter("edge"):
        eid = edge.get("id")
        for lane in edge.iter("lane"):
            if lane.get("length") is not None:
                all_lanes[lane.get("id")] = (
                    float(lane.get("length")),
                    float(lane.get("speed", 0)) or None,
                )
        if eid not in wanted:
            continue
        lane_lengths = [float(l.get("length")) for l in edge.iter("lane")
                        if l.get("length") is not None]
        lane_speeds = [float(l.get("speed")) for l in edge.iter("lane")
                       if l.get("speed") is not None]
        if lane_lengths:
            # lanes of one edge share a length; take the max defensively
            per_edge[eid] = max(lane_lengths)
            if lane_speeds:
                per_edge_speed[eid] = max(lane_speeds)

    via = {(c.get("from"), c.get("to")): c.get("via")
           for c in root.iter("connection") if c.get("via")}

    internal_m = 0.0
    internal_s = 0.0
    internal_found = 0
    for a, b in zip(ordered, ordered[1:]):
        v = via.get((a, b))
        if v and v in all_lanes:
            L, spd = all_lanes[v]
            internal_m += L
            internal_found += 1
            if spd:
                internal_s += L / spd

    missing = sorted(wanted - set(per_edge))
    edges_m = sum(per_edge.values())
    edges_s = sum(per_edge[e] / per_edge_speed[e]
                  for e in per_edge if per_edge_speed.get(e))

    return {
        "n_requested": len(wanted),
        "n_found": len(per_edge),
        "missing_edge_ids": missing,
        "edges_only_km": edges_m / 1000.0,
        "internal_lanes_km": internal_m / 1000.0,
        "internal_lanes_found": internal_found,
        "internal_lanes_expected": max(len(ordered) - 1, 0),
        "total_length_km": (edges_m + internal_m) / 1000.0,
        "free_flow_min": (edges_s + internal_s) / 60.0,
        "per_edge_m": per_edge,
    }


def corridor_endpoints_lonlat(net_file: str | Path,
                              first_edge: str,
                              last_edge: str) -> dict:
    """Convert the corridor's true start/end to lat/lon.

    Use THESE as the origin/destination for any travel-time query. Querying a
    route that is longer than the modelled corridor biases every subsequent
    comparison, and you would spend weeks tuning car-following parameters to
    close a gap that is purely geometric.
    """
    from pyproj import Transformer

    root = ET.parse(str(net_file)).getroot()
    shapes = {}
    for edge in root.iter("edge"):
        eid = edge.get("id")
        if eid not in (first_edge, last_edge):
            continue
        lane = next(iter(edge.iter("lane")), None)
        if lane is None or not lane.get("shape"):
            continue
        pts = [tuple(map(float, p.split(","))) for p in lane.get("shape").split()]
        shapes[eid] = pts

    tf = Transformer.from_crs(UTM_PROJ, "EPSG:4326", always_xy=True)

    def to_lonlat(xy):
        x = xy[0] - NET_OFFSET[0]
        y = xy[1] - NET_OFFSET[1]
        lon, lat = tf.transform(x, y)
        return round(lat, 6), round(lon, 6)

    out = {}
    if first_edge in shapes:
        out["origin_latlon"] = to_lonlat(shapes[first_edge][0])
    if last_edge in shapes:
        out["destination_latlon"] = to_lonlat(shapes[last_edge][-1])
    if "origin_latlon" in out and "destination_latlon" in out:
        out["straight_line_km"] = _haversine_km(out["origin_latlon"],
                                                out["destination_latlon"])
    return out


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import radians, sin, cos, asin, sqrt
    R = 6371.0088
    p1, p2 = radians(a[0]), radians(b[0])
    dp, dl = p2 - p1, radians(b[1] - a[1])
    h = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(h))


def sanity_check_geometry(corridor_km: float, straight_line_km: float) -> dict:
    """Detour ratio must be >= 1.0. Anything below is impossible."""
    ratio = corridor_km / straight_line_km if straight_line_km else float("nan")
    return {
        "corridor_km": round(corridor_km, 3),
        "straight_line_km": round(straight_line_km, 3),
        "detour_ratio": round(ratio, 3),
        "possible": ratio >= 1.0,
        "note": ("OK — typical urban detour ratio is 1.05-1.30"
                 if ratio >= 1.0 else
                 "IMPOSSIBLE: a road cannot be shorter than the straight line "
                 "between its endpoints. Either the edge list is incomplete or "
                 "the query endpoints overshoot the corridor."),
    }


# ---------------------------------------------------------------------------
# 1. Standing gate on every run
# ---------------------------------------------------------------------------

def demand_audit(tripinfo: str | Path,
                 route_file: str | Path,
                 sim_end: float,
                 free_flow_s: float,
                 summary_file: str | Path | None = None,
                 max_insertion_loss_pct: float = 2.0) -> dict:
    """Compare scheduled vs inserted vs completed.

    The last OD run was 2439 loaded -> 1749 inserted -> 1035 completed, with
    DepartDelay 118 s. Part of the gap is legitimate: vehicles departing near
    the 1 h cutoff cannot finish a 14.8 min crossing. That part is estimated
    here and separated out.

    CORRECTED 17 Aug 2026. An earlier version set `inserted = completed` on
    the belief that tripinfo lists every vehicle that entered. It does not —
    tripinfo records only vehicles that ARRIVED. In the run above that is the
    difference between 1749 and 1035, so the insertion loss came out as 690
    when it was really 1404.

    `inserted` is now read from the last <step> of the summary file, which is
    authoritative. Without `summary_file` the function still runs but reports
    inserted as None and cannot gate on insertion loss, because guessing it
    is what caused the bug.
    """
    scheduled = 0
    r = ET.parse(str(route_file)).getroot()
    scheduled += sum(1 for _ in r.iter("vehicle"))
    scheduled += sum(1 for _ in r.iter("trip"))
    for f in r.iter("flow"):
        if f.get("number"):
            scheduled += int(f.get("number"))
        elif f.get("vehsPerHour"):
            span = float(f.get("end", 3600)) - float(f.get("begin", 0))
            scheduled += int(float(f.get("vehsPerHour")) * span / 3600)

    t = ET.parse(str(tripinfo)).getroot()
    trips = list(t.iter("tripinfo"))
    completed = len(trips)
    departs = np.array([float(x.get("depart", 0)) for x in trips]) if trips else np.array([])

    # vehicles that departed too late to plausibly finish
    cutoff = sim_end - free_flow_s
    late = int((departs > cutoff).sum()) if departs.size else 0

    # inserted must come from the summary file. tripinfo lists ARRIVALS only.
    inserted = loaded = running = teleports = None
    if summary_file is not None:
        steps = list(ET.parse(str(summary_file)).getroot().iter("step"))
        if steps:
            last = steps[-1]
            inserted = int(last.get("inserted", 0))
            loaded = int(last.get("loaded", 0))
            running = int(last.get("running", 0))
            teleports = int(last.get("teleports", 0))

    res = {
        "scheduled": scheduled,
        "loaded": loaded,
        "inserted": inserted,
        "completed": completed,
        "still_running_at_end": running,
        "teleports": teleports,
        "departed_after_cutoff": late,
        "departed_after_cutoff_note": (
            "these could not finish inside the window and are not a defect; "
            "either extend the simulation past sim_end or exclude them"),
        "mean_depart_delay_s": round(float(np.mean(
            [float(x.get("departDelay", 0)) for x in trips])), 1) if trips else None,
    }

    if inserted is None:
        res["never_inserted"] = None
        res["insertion_loss_pct"] = None
        res["passes"] = None
        res["action"] = ("Pass summary_file to gate on insertion loss. It is "
                         "not inferable from tripinfo, and inferring it is "
                         "what produced the earlier 690-vs-1404 error.")
        return res

    never_inserted = scheduled - inserted
    loss_pct = 100.0 * never_inserted / scheduled if scheduled else float("nan")
    res["never_inserted"] = never_inserted
    res["insertion_loss_pct"] = round(loss_pct, 2)
    # completed < inserted is expected; those vehicles are mid-trip at sim_end
    res["in_transit_at_end"] = inserted - completed
    res["passes"] = loss_pct <= max_insertion_loss_pct
    if not res["passes"]:
        res["action"] = ("Insertion loss above threshold. Check for invalid "
                         "edge ids in the demand file (one bad id aborts the "
                         "whole jtrrouter build), for one-way TAZ violations, "
                         "for edges that disallow passenger cars (88 exist in "
                         "this network), and for oversaturated entry links.")
    return res


# ---------------------------------------------------------------------------
# 2. Observations: the schema TomTom Route Analysis gives you
# ---------------------------------------------------------------------------

@dataclass
class ObservedRoute:
    """One direction x one time slice of TomTom Route Analysis output.

    Route Analysis returns 5th-95th percentile speeds and travel times, per
    segment, with sample sizes. Keep the percentiles. A single mean is much
    weaker evidence and cannot support an interval-based acceptance test.
    """
    direction: str            # "NB" | "SB"
    time_slice: str           # "07:00" ...
    tt_p25_s: float
    tt_p50_s: float
    tt_p75_s: float
    sample_size: int
    segments: pd.DataFrame = field(default_factory=pd.DataFrame)
    # segments columns: segment_id, length_m, speed_p50_kmh, speed_p25_kmh,
    #                   speed_p75_kmh, sample_size


def observations_template(path: str | Path = "observed_traveltimes.csv") -> Path:
    """Write an empty CSV with the required columns and a SYNTHETIC flag.

    Per the project's standing rule: every synthetic number is labelled
    synthetic in the file itself, not only in conversation.
    """
    cols = ["source", "is_synthetic", "direction", "time_slice", "date_range",
            "tt_p25_s", "tt_p50_s", "tt_p75_s", "sample_size"]
    df = pd.DataFrame(columns=cols)
    df.to_csv(path, index=False)
    return Path(path)


# ---------------------------------------------------------------------------
# 3. Simulated side
# ---------------------------------------------------------------------------

def extract_corridor_travel_times(tripinfo: str | Path,
                                  corridor_edges: set[str],
                                  min_edges_traversed: int,
                                  vehroute_file: str | Path | None = None
                                  ) -> pd.DataFrame:
    """Travel times of vehicles that actually traversed the corridor.

    Filtering matters: a network-wide mean travel time is not comparable to a
    corridor route query. Only vehicles whose route covers at least
    `min_edges_traversed` of the corridor edges are counted.

    CORRECTED 17 Aug 2026. The earlier version accepted these two arguments
    and ignored them, returning every tripinfo row — i.e. exactly the
    network-wide mean its own docstring warned against.

    To enable filtering, add to the sumocfg:

        <vehroute-output value="../outputs/am_vehroutes.xml"/>

    and pass that file. Without it the function refuses to filter rather than
    silently returning unfiltered data.
    """
    root = ET.parse(str(tripinfo)).getroot()
    rows = []
    for tp in root.iter("tripinfo"):
        rows.append((tp.get("id"), float(tp.get("duration")),
                     float(tp.get("routeLength", 0)),
                     float(tp.get("timeLoss", 0)),
                     float(tp.get("depart", 0))))
    df = pd.DataFrame(rows, columns=["id", "duration_s", "route_len_m",
                                     "time_loss_s", "depart_s"])
    df["corridor_edges_traversed"] = np.nan
    df["on_corridor"] = pd.NA

    if vehroute_file is None:
        df.attrs["filtered"] = False
        df.attrs["warning"] = (
            "NOT FILTERED — no vehroute_file given, so traversed edges are "
            "unknown. These are network-wide travel times and must not be "
            "compared against a corridor route query.")
        return df

    vr = ET.parse(str(vehroute_file)).getroot()
    counts = {}
    for veh in vr.iter("vehicle"):
        route = next(iter(veh.iter("route")), None)
        if route is None or not route.get("edges"):
            continue
        edges = route.get("edges").split()
        counts[veh.get("id")] = sum(1 for e in edges if e in corridor_edges)

    df["corridor_edges_traversed"] = df["id"].map(counts)
    df["on_corridor"] = df["corridor_edges_traversed"] >= min_edges_traversed
    df.attrs["filtered"] = True
    df.attrs["n_on_corridor"] = int(df["on_corridor"].sum())
    df.attrs["n_total"] = len(df)
    return df[df["on_corridor"] == True].copy()


def extract_segment_speeds(edgedata: str | Path,
                           segment_map: dict[str, list[str]]) -> pd.DataFrame:
    """Per-segment mean speed, vehicle-time weighted.

    segment_map aligns SUMO edges to the TomTom segments so the two spatial
    profiles can be compared segment by segment. Building this mapping is
    manual work and it is the part that makes the comparison meaningful.
    """
    root = ET.parse(str(edgedata)).getroot()
    acc: dict[str, dict] = {}
    for interval in root.iter("interval"):
        for e in interval.iter("edge"):
            s = float(e.get("sampledSeconds", 0) or 0)
            if s <= 0:
                continue
            rec = acc.setdefault(e.get("id"), {"num": 0.0, "den": 0.0})
            rec["num"] += float(e.get("speed", 0) or 0) * s
            rec["den"] += s

    rows = []
    for seg, eids in segment_map.items():
        present = [acc[e] for e in eids if e in acc]
        if not present:
            rows.append({"segment_id": seg, "sim_speed_kmh": np.nan, "n_edges": 0})
            continue
        den = sum(r["den"] for r in present)
        rows.append({"segment_id": seg,
                     "sim_speed_kmh": 3.6 * sum(r["num"] for r in present) / den,
                     "n_edges": len(present)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Acceptance criteria -- declare before calibrating, never after
# ---------------------------------------------------------------------------

def pct_rmse(sim, obs) -> float:
    sim, obs = np.asarray(sim, float), np.asarray(obs, float)
    m = ~(np.isnan(sim) | np.isnan(obs))
    return 100.0 * np.sqrt(np.mean((sim[m] - obs[m]) ** 2)) / np.mean(obs[m])


def theil_u(sim, obs) -> float:
    sim, obs = np.asarray(sim, float), np.asarray(obs, float)
    m = ~(np.isnan(sim) | np.isnan(obs))
    sim, obs = sim[m], obs[m]
    num = np.sqrt(np.mean((sim - obs) ** 2))
    den = np.sqrt(np.mean(sim ** 2)) + np.sqrt(np.mean(obs ** 2))
    return float(num / den) if den else float("nan")


ACCEPTANCE = {
    "min_pct_inside_iqr": 75.0,   # travel time, direction x time slice
    "max_pct_rmse_speed": 15.0,   # segment speeds
    "max_theil_u": 0.10,
    "min_profile_rank_corr": 0.70,  # does the model put bottlenecks where they are
}


def validate(tt: pd.DataFrame, seg: pd.DataFrame | None = None) -> dict:
    """tt  : columns [direction, time_slice, sim_tt_s, tt_p25_s, tt_p50_s, tt_p75_s]
       seg : columns [segment_id, sim_speed_kmh, speed_p50_kmh]

    Reports the profile rank correlation separately from the level error.
    A model can get the average right and put the bottleneck in the wrong
    place; on a corridor study that is a worse failure than a level bias,
    because every ITS siting decision downstream depends on where the
    congestion is.
    """
    res: dict = {}
    inside = tt["sim_tt_s"].between(tt["tt_p25_s"], tt["tt_p75_s"])
    res["pct_inside_iqr"] = round(100.0 * inside.mean(), 1)
    res["tt_pct_rmse"] = round(pct_rmse(tt["sim_tt_s"], tt["tt_p50_s"]), 2)
    res["tt_theil_u"] = round(theil_u(tt["sim_tt_s"], tt["tt_p50_s"]), 4)
    res["tt_mean_bias_s"] = round(float((tt["sim_tt_s"] - tt["tt_p50_s"]).mean()), 1)

    if seg is not None and len(seg) > 2:
        res["speed_pct_rmse"] = round(pct_rmse(seg["sim_speed_kmh"],
                                               seg["speed_p50_kmh"]), 2)
        res["profile_rank_corr"] = round(float(
            seg["sim_speed_kmh"].corr(seg["speed_p50_kmh"], method="spearman")), 3)

    res["passes"] = (
        res["pct_inside_iqr"] >= ACCEPTANCE["min_pct_inside_iqr"]
        and res["tt_theil_u"] <= ACCEPTANCE["max_theil_u"]
        and res.get("speed_pct_rmse", 0) <= ACCEPTANCE["max_pct_rmse_speed"]
        and res.get("profile_rank_corr", 1) >= ACCEPTANCE["min_profile_rank_corr"]
    )
    return res


# ---------------------------------------------------------------------------
# 5. Identifiability -- the constraint that must be stated, not hidden
# ---------------------------------------------------------------------------

FIXED_BEFORE_CALIBRATION = {
    # Fix these from literature (cite heterogeneous-traffic calibration studies),
    # freeze them, and calibrate demand scale ALONE. With travel time as the only
    # observable you cannot jointly identify demand and capacity: the same
    # travel-time gap closes by raising demand or by degrading saturation flow,
    # and nothing in the data tells you which is correct.
    "tau": 1.0,
    "minGap": 2.5,
    "accel": 2.6,
    "decel": 4.5,
    "speedFactor": "norm(1.0,0.10)",
    "sigma": 0.5,
    "_provenance": "TODO: cite source per value before freezing",
    "_sensitivity": "report all conclusions under +/-20% on these",
}

CALIBRATED = {"demand_scale": (0.6, 1.6)}


if __name__ == "__main__":
    # self-test on synthetic, clearly labelled, data
    print("SELF-TEST ON SYNTHETIC DATA (not results)\n")
    print(sanity_check_geometry(12.421, 12.151))   # true driven length, incl. junction internals
    print(sanity_check_geometry(10.430, 12.151))   # edges only - the old, impossible figure
    print()
    rng = np.random.default_rng(0)
    tt = pd.DataFrame({
        "direction": ["NB"] * 6 + ["SB"] * 6,
        "time_slice": ["07:00", "08:00", "12:00", "13:00", "17:00", "18:00"] * 2,
        "tt_p50_s": [1180, 1420, 890, 910, 1350, 1290] * 2,
    })
    tt["tt_p25_s"] = tt["tt_p50_s"] * 0.88
    tt["tt_p75_s"] = tt["tt_p50_s"] * 1.14
    tt["sim_tt_s"] = tt["tt_p50_s"] * rng.normal(1.0, 0.06, len(tt))
    seg = pd.DataFrame({
        "segment_id": [f"S{i:02d}" for i in range(12)],
        "speed_p50_kmh": [42, 38, 22, 19, 35, 40, 28, 24, 45, 44, 31, 26],
    })
    seg["sim_speed_kmh"] = seg["speed_p50_kmh"] * rng.normal(1.0, 0.09, len(seg))
    for k, v in validate(tt, seg).items():
        print(f"  {k:22s} {v}")
    print("\nNo GEH is reported. There are no counts. That is the correct output.")
