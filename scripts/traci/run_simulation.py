"""
Minimal TraCI scaffold for the Route de Tunis SUMO model.

This is a *starting point* for the next thesis phase: instead of only
reading tripinfo.xml / summary.xml at the end of a run, this connects to a
live SUMO instance and lets you read/log/act on the simulation at every
timestep (vehicle positions, speeds, queue lengths, signal states, etc.),
and eventually test adaptive control logic.

Run from the project root:
    python scripts/traci/run_simulation.py
"""

import os
import sys
import traci
import pandas as pd

# --- SUMO_HOME must be set (same requirement as sumo-gui/jtrrouter) ---
if "SUMO_HOME" not in os.environ:
    sys.exit("Please set the SUMO_HOME environment variable (see environment.yml).")

SUMO_BINARY = "sumo"  # use "sumo-gui" to watch it visually
SUMOCFG = os.path.join("config", "routetunis.sumocfg")

sumo_cmd = [SUMO_BINARY, "-c", SUMOCFG]


def run():
    traci.start(sumo_cmd)

    step_records = []

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            t = traci.simulation.getTime()

            # Example: log corridor-wide KPIs every step.
            # Replace "main_edge_id" with the real edge ID once you decide
            # which edges represent the corridor you want to track.
            vehicle_ids = traci.vehicle.getIDList()
            if vehicle_ids:
                avg_speed = sum(traci.vehicle.getSpeed(v) for v in vehicle_ids) / len(vehicle_ids)
            else:
                avg_speed = 0.0

            step_records.append({
                "time": t,
                "n_vehicles": len(vehicle_ids),
                "avg_speed_mps": avg_speed,
            })

    finally:
        traci.close()

    df = pd.DataFrame(step_records)
    os.makedirs("outputs", exist_ok=True)
    df.to_csv(os.path.join("outputs", "traci_step_log.csv"), index=False)
    print(f"Logged {len(df)} steps to outputs/traci_step_log.csv")


if __name__ == "__main__":
    run()
