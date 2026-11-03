#!/bin/bash
# Same world reset as player/schedule.py: forget killed zombies, corpses, doors and events, restart the app.
cd ~/osz-stack
docker compose stop app >/dev/null 2>&1
docker compose exec -T db psql -U osz -d osz -qc 'delete from zed_dead; delete from world_corpse; delete from building_opening; delete from world_events;'
docker compose up -d app >/dev/null 2>&1
for i in $(seq 90); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' 127.0.0.1:8120/healthz)" = 200 ] && { sleep 3; echo "app up after $i s"; exit 0; }; sleep 1; done
echo "app did not come back"; exit 1
