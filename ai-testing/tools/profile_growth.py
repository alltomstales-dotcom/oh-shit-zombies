"""What grows? Offline: N walking survivors round a start city on a difficulty profile, with K corpses
scattered within R m of the centre (as a soak leaves them where bots die). Times the world step and
the views separately, then cProfiles both.
  ~/venvs/osz/bin/python profile_growth.py PROFILE N K SECONDS [R_m] [sortkey] [lines]"""
import cProfile, json, math, os, pstats, random, sqlite3, sys, time
sys.path.insert(0, os.environ.get('OSZ_SRC', '../src'))
from app.daylight import light_level
from app.game import difficulty, corpses
from app.game.content import TUNE
from app.game.director import Director
from app.game.sim import Actor, World, Zed, shift
from app.game.spawn import Spawner
from app.game.starts import by_id
prof, N, K, SECS = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
R = float(sys.argv[5]) if len(sys.argv) > 5 else 120.0
city = by_id('chicago'); d = difficulty.resolve(prof)
w = World(rng=random.Random(1), tune=dict(difficulty.tune_for(d, TUNE), transit_jump_m=float('inf')),
          light_fn=lambda lat, lng, now: light_level(lat, lng, int(now)), spawner=Spawner(density=d['density'], night_packs=d['night_packs']))
w.show_others = True
db = sqlite3.connect('/tmp/osz-sweep/template/osz.db')
for (recs,) in db.execute('select records from building_region'):
    w.buildings.add(json.loads(recs))
w.resource_regions = set(r for (r,) in db.execute('select id from building_region'))
director = Director(w, config=d['director'])
now = time.time(); w.now = now; rng = random.Random(2); heading = {}
for i in range(1, N + 1):
    lat, lng = shift(city['lat'], city['lng'], rng.uniform(-40, 40), rng.uniform(-40, 40))
    a = Actor(id=i, lat=lat, lng=lng, born=now - 99999, placed_at=now, name=f'S{i}', life_id=1)
    w.add_actor(a, now); w.set_position(i, lat, lng, 1.0); heading[i] = rng.uniform(0, 6.28)
for k in range(K):
    lat, lng = shift(city['lat'], city['lng'], rng.uniform(-R, R), rng.uniform(-R, R))
    if k % 4 == 0:
        dead = Actor(id=100000 + k, lat=lat, lng=lng, name=f'D{k}', life_id=1)
        body = corpses.survivor(dead, now)
    else:
        body = corpses.create(w, Zed(id=f'c:{k}', lat=lat, lng=lng, kind='shambler', hp=0, hp_max=20, speed=1, variant=k, home=(lat, lng)))
        body['until'] = now + 86400
    w.corpses[body['id']] = body
known = {}
ZN = int(os.environ.get('Z_NEAR', '0'))
for k in range(ZN):                         # idle zombies loitering round the start, as a busy soak leaves them
    lat, lng = shift(city['lat'], city['lng'], rng.uniform(-70, 70), rng.uniform(-70, 70))
    if w.buildings.containing((lat, lng)): continue
    w.zeds[f'near:{k}'] = Zed(id=f'near:{k}', lat=lat, lng=lng, home=(lat, lng), speed=1.2)
def tick(parts):
    global now
    now += 0.2
    for i, a in w.actors.items():
        if a.dead: continue
        heading[i] += rng.uniform(-.35, .35)
        w.set_position(i, *shift(a.lat, a.lng, math.cos(heading[i]) * 1.6, math.sin(heading[i]) * 1.6), 1.0)
    t0 = time.perf_counter(); w.step(now); director.tick(); t1 = time.perf_counter()
    for i, a in w.actors.items():
        known[i] = w.view(i, known.get(i))['building_key']
    t2 = time.perf_counter(); parts['step'] += t1 - t0; parts['view'] += t2 - t1
for _ in range(25): tick({'step': 0, 'view': 0})
ticks = int(SECS / 0.2); parts = {'step': 0.0, 'view': 0.0}
pr = cProfile.Profile()
if os.environ.get('PROF'): pr.enable()
for _ in range(ticks): tick(parts)
pr.disable()
alive = sum(z.alive for z in w.zeds.values())
print(f'{prof}: N={N} corpses={len(w.corpses)} zombies={alive}: step {1000*parts["step"]/ticks:.1f} ms, views {1000*parts["view"]/ticks:.1f} ms a tick')
if os.environ.get('PROF'):
    pstats.Stats(pr).sort_stats(sys.argv[6] if len(sys.argv) > 6 else 'tottime').print_stats(int(sys.argv[7]) if len(sys.argv) > 7 else 18)
if os.environ.get('CALLERS'):
    st = pstats.Stats(pr); st.sort_stats('cumtime').print_callers(os.environ['CALLERS'])
