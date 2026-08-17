@echo off
REM Build corridor routes from the OD matrix (od2trips -> duarouter).
REM Run from the project root:  scripts\generate_routes_od.bat
REM
REM This replaces the jtrrouter path for the corridor model. jtrrouter
REM assigns turns at random and produced 59%% U-turn routes; this pipeline
REM routes each vehicle from a real origin to a real destination.
REM
REM WARNING: digital_twin\od_synthetic_am.txt contains INVENTED numbers.
REM Replace them with observed counts before reporting anything.

if not exist routes mkdir routes

od2trips ^
  --taz-files digital_twin\corridor_tazs.add.xml ^
  --od-matrix-files digital_twin\od_synthetic_am.txt ^
  --output-file routes\trips_am.xml ^
  --begin 25200 --end 28800

duarouter ^
  --net-file network\routetunisraw_recomputed_v3.net.xml ^
  --route-files routes\trips_am.xml ^
  --output-file routes\routes_am.xml ^
  --remove-loops ^
  --ignore-errors

echo.
echo Routes written to routes\routes_am.xml
echo Then run:  cd config ^&^& sumo -c routetunis_od_am.sumocfg
