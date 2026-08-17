#!/usr/bin/env bash
# Regenerate routes/routetunis_routes.xml from source network + demand.
# Run from the project root: bash scripts/generate_routes.sh
set -euo pipefail

mkdir -p routes

jtrrouter \
  --net-file network/routetunisraw.net.xml \
  --route-files demand/flows.xml \
  --turn-ratio-files demand/turnRatios.xml \
  --accept-all-destinations \
  --output-file routes/routetunis_routes.xml \
  --begin 25200 --end 68400

echo "Routes regenerated at routes/routetunis_routes.xml"
echo "Bus line 25 is separate: demand/bus25.rou.xml (loaded directly by SUMO config, not via jtrrouter)"
