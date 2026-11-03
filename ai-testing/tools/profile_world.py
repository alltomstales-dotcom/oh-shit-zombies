"""Profile the world loop offline: N walking survivors around a start city, with a difficulty
profile, stepping and building every survivor's view as the server does five times a second.
Uses the cached map regions in the sweep template database; no network.
  ~/venvs/osz/bin/python profile_world.py PROFILE N SECONDS [city]"""
import cProfile, json, math, pstats, random, sqlite3, sys, time
sys.path.insert(0, '../src')
from app.daylight import light_level
from app.game import difficulty
from app.game.buildings import Buildings
from app.game.content import TUNE
from app.game.director import Director
from app.game.sim import Actor, World, shift
from app.game.spawn import Spawner
from app.game.starts import by_id
prof, N, SECS = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]); city = by_id(sys.argv[4] if len(sys.argv) > 4 else 'chicago')
d = difficulty.resolve(prof)
w = World(rng=random.Random(1), tune=dict(difficulty.tune_for(d, TUNE), transit_jump_m=float('inf')),
          light_fn=lambda lat, lng, now: light_level(lat, lng, int(now)), spawner=Spawner(density=d['density'], night_packs=d['night_packs']))
w.show_others = True
db = sqlite3.connect('/tmp/osz-sweep/template/osz.db')
for (recs,) in db.execute('select records from building_region'):
    w.buildings.add(json.loads(recs))
w.resource_regions = set(r for (r,) in db.execute('select id from building_region'))
director = Director(w, config=d['director'])
now = time.time(); rng = random.Random(2); heading = {}
for i in range(1, N + 1):
    lat, lng = shift(city['lat'], city['lng'], rng.uniform(-40, 40), rng.uniform(-40, 40))
    a = Actor(id=i, lat=lat, lng=lng, born=now - 99999, placed_at=now, name=f'S{i}', life_id=1)
    w.add_actor(a, now); w.set_position(i, lat, lng, 1.0); heading[i] = rng.uniform(0, 6.28)
known = {}
def tick():
    global now
    now += 0.2
    for i, a in w.actors.items():
        if a.dead:
            continue
        heading[i] += rng.uniform(-.35, .35)
        w.set_position(i, *shift(a.lat, a.lng, math.cos(heading[i]) * 1.6, math.sin(heading[i]) * 1.6), 1.0)
    w.step(now); director.tick()
    for i, a in w.actors.items():
        v = w.view(i, known.get(i)); known[i] = v['building_key']
ticks = int(SECS / 0.2)
for _ in range(25): tick()                      # warm up: cells load
import os
pr = cProfile.Profile(); t0 = time.perf_counter()
if not os.environ.get('NOPROF'): pr.enable()
for _ in range(ticks): tick()
pr.disable() if not os.environ.get('NOPROF') else None; took = time.perf_counter() - t0
zeds = {}
for zid, z in w.zeds.items():
    if z.alive: zeds[zid.split(':')[0]] = zeds.get(zid.split(':')[0], 0) + 1
print(f'{prof}: {N} survivors, {ticks} ticks, {1000 * took / ticks:.0f} ms a tick (budget 200); zombies {zeds}; dead survivors {sum(a.dead for a in w.actors.values())}')
st = pstats.Stats(pr) if not os.environ.get('NOPROF') else None
if st: st.sort_stats(sys.argv[5] if len(sys.argv) > 5 else 'tottime').print_stats(int(sys.argv[6]) if len(sys.argv) > 6 else 14)
