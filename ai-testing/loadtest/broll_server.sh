#!/bin/bash
# A throwaway server for b-roll: broll_server.sh FIXTURE PORT [DIFFICULTY] [args...]
#   FIXTURE: broll (../tools/serve_broll.py), herd (src/tools/serve_herd.py), recovery (src/tools/serve_recovery.py)
# Fresh copy of the template SQLite (cached Chicago + Minneapolis map regions), real GPS on (the repo's
# browser checks place by geolocation), OpenStreetMap unreachable, one CPU, current src mounted read-only.
FIX=$1; PORT=$2; DIFF=${3:-public}; shift 3
NAME=osz-broll-$FIX; D=/tmp/osz-broll-$FIX
docker rm -f $NAME >/dev/null 2>&1; rm -rf $D; mkdir -p $D; chmod 777 $D
cp /tmp/osz-sweep/template/osz.db $D/osz.db; chmod 666 $D/osz.db
case $FIX in
  broll) SCRIPT=/tools/serve_broll.py ;;
  herd) SCRIPT=/src/tools/serve_herd.py ;;
  recovery) SCRIPT=/src/tools/serve_recovery.py ;;
esac
docker run -d --name $NAME --network host --cpus 1 --memory 448m --memory-swap 448m \
  -v $HOME/osz-stack/src:/src:ro -v $HOME/osz-stack/tools:/tools:ro -v $D:/data -w /src \
  --add-host overpass-api.de:127.0.0.1 --add-host api.openstreetmap.org:127.0.0.1 \
  -e OSZ_SRC=/src -e ENV=dev -e DATABASE_URL=sqlite+aiosqlite:////data/osz.db -e SECRET_KEY=broll-not-public-0123456789 \
  -e REAL_GPS=1 -e FREE_TEXT=1 -e OSZ_OVERPASS_URL=http://127.0.0.1:9/ -e DIFFICULTY=$DIFF -e MAX_PLAYERS=25 \
  osz-siege:final python $SCRIPT $PORT "$@" >/dev/null
for i in $(seq 60); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' 127.0.0.1:$PORT/healthz)" = 200 ] && { echo "$NAME up on $PORT ($DIFF)"; exit 0; }; sleep 1; done
echo "$NAME did not come up"; docker logs $NAME 2>&1 | tail -20; exit 1
