#!/bin/bash
# How many sieges at once this machine holds. A second throwaway server (8141) whose sieges all start at
# 21:00 (OSZ_SIEGE_START_S=1260), the heaviest stretch of the table; bots start a new siege when one ends.
# Steps of N sieges for 180 s each; the server's own siege stats lines and the bots' pings are kept.
# Optional: SURV=n walking survival bots on the same server at the same time (bots.py).
cd ~/osz-stack/loadtest
STEPS=${STEPS:-"10 20 30 40"}; SURV=${SURV:-0}; TAG=${TAG:-ladder}
mkdir -p siege
for N in $STEPS; do
  D=/tmp/osz-siege-ladder; docker rm -f osz-siege-ladder >/dev/null 2>&1; rm -rf $D; mkdir -p $D; chmod 777 $D
  cp /tmp/osz-sweep/template/osz.db $D/osz.db; chmod 666 $D/osz.db
  docker run -d --name osz-siege-ladder --user 1000:1000 --cpus 1 --memory 448m --memory-swap 448m -v $D:/data \
    --add-host overpass-api.de:127.0.0.1 --add-host api.openstreetmap.org:127.0.0.1 -p 127.0.0.1:8141:8000 \
    -e ENV=dev -e DATABASE_URL=sqlite+aiosqlite:////data/osz.db -e SECRET_KEY=siege-ladder-not-public-0123456789 \
    -e REAL_GPS=0 -e FREE_TEXT=0 -e TRUST_PROXY=cloudflare -e OSZ_OVERPASS_URL=http://127.0.0.1:9/ -e MAX_PLAYERS=80 \
    -e OSZ_MAX_SIEGES=80 -e OSZ_SIEGE_START_S=1260 -e DIFFICULTY=public osz-siege:final >/dev/null
  for i in $(seq 60); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' 127.0.0.1:8141/healthz)" = 200 ] && break; sleep 1; done
  sleep 3
  [ "$SURV" -gt 0 ] && (BASE=127.0.0.1:8141 python3 bots.py $SURV 200 chicago > /dev/null 2>&1 &)
  ~/venvs/osz/bin/python siege_bots.py $N --base 127.0.0.1:8141 --app osz-siege-ladder --stagger 0.3 --limit 190 --again --tag _${TAG}_s${SURV} > siege/${TAG}_N${N}_s${SURV}_console.log 2>&1
  docker logs osz-siege-ladder 2>&1 | grep -E "siege stats|stats:|Traceback|ERROR" > siege/${TAG}_N${N}_s${SURV}_server.log
  echo "N=$N SURV=$SURV done $(date +%H:%M:%S)"
  sleep 15
done
docker rm -f osz-siege-ladder >/dev/null 2>&1
