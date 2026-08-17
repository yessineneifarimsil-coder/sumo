@echo off
REM Regenerate routes\routetunis_routes.xml from source network + demand.
REM Run from the project root in Anaconda Prompt: scripts\generate_routes.bat
REM
REM Updated 2026-08-16:
REM   - now points at network\routetunisraw_recomputed.net.xml. The old
REM     routetunisraw.net.xml cannot be loaded by any SUMO tool at all
REM     ("Attribute 'dir' is missing in definition of a connection").
REM   - --remove-loops and --turn-defaults 15,80,5,0 added. The 4th value is the
REM     turnaround weight; without it jtrrouter U-turns freely and 92% of routes
REM     contained an instant reversal. See docs\decisions.md.

if not exist routes mkdir routes

jtrrouter ^
  --net-file network\routetunisraw_recomputed.net.xml ^
  --route-files demand\flows.xml ^
  --turn-ratio-files demand\turnRatios.xml ^
  --accept-all-destinations ^
  --remove-loops ^
  --turn-defaults 15,80,5,0 ^
  --output-file routes\routetunis_routes.xml ^
  --begin 25200 --end 68400

echo Routes regenerated at routes\routetunis_routes.xml
echo Bus line 25 is separate: demand\bus25.rou.xml (loaded directly by SUMO config, not via jtrrouter)
