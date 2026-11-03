"""Local testing only: the ordinary app with a herd brought to whoever is connected, so a browser
check can meet one in a minute instead of waiting hours for the real schedule.

    DATABASE_URL=sqlite+aiosqlite:////tmp/osz-herd.db python tools/serve_herd.py 8021 [pass|load] [herds]

pass (the default): one herd of sixty is put down the longest clear street from the survivor, just
beyond where a herd can be made out, walking up that street to where the survivor stood. It is
heard, then seen, and stays one thing until it is near enough to notice them.

load: `herds` herds (default 2) are put forty-five metres away and have noticed the survivor twenty
seconds later, and the survivor is kept alive, so the server carries that many awake herds for as
long as the check wants to measure it.

The real schedule is off, and so are all other zombies: a scout standing in the street waiting for a
herd was otherwise bitten by the ordinary ones before it arrived. Never point this at the production
database.
"""
import math
import os
import sys

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.game import herds  # noqa: E402
from app.game.content import TUNE  # noqa: E402
from app.game.sim import delta_m, dist_m, shift  # noqa: E402
from app.game.building_loader import wanted_regions  # noqa: E402

assert "sqlite" in os.environ.get("DATABASE_URL", ""), "a local SQLite DATABASE_URL only"
MODE = sys.argv[2] if len(sys.argv) > 2 else "pass"
WANT = int(sys.argv[3]) if len(sys.argv) > 3 else (2 if MODE == "load" else 1)
TUNE.update(herd_chance=0.0)
_real_step, _brought, _placed = herds.step, {}, {}


def _street(world, a, far):
    """The clear spot furthest down a street from the survivor, up to `far` metres: (distance, bearing, point)."""
    best = None
    for i in range(36):
        ang = i * math.tau / 36
        for d in range(int(far), 30, -5):
            p = shift(a.lat, a.lng, math.cos(ang) * d, math.sin(ang) * d)
            if world.buildings.containing(p) is None and world.buildings.clear(p, p, 1.5) and world.buildings.clear((a.lat, a.lng), p, 0.6):   # a way to walk, not a view through a window
                if best is None or d > best[0]:
                    best = (d, ang, p)
                break
    return best


def _ahead(world, h):
    q = shift(h.lat, h.lng, math.cos(h.heading) * 1.0, math.sin(h.heading) * 1.0)
    inside, wall = world.buildings.containing(q), world.buildings.first_blocking((h.lat, h.lng), q)
    return f"in:{inside and (inside.id, inside.type, inside.name)} wall:{wall and (wall.id, wall.type, wall.name)}"


def step(world, dt):
    now = world.now
    for zid in [z for z in world.zeds if not z.startswith("h:")]:   # only the herd's own
        del world.zeds[zid]
    for a in list(world.actors.values()):
        if a.dead or (a.lat == 0.0 and a.lng == 0.0) or world.buildings.containing((a.lat, a.lng)) is not None:
            continue
        if MODE == "load":
            a.hp, a.wounds = 100.0, []
        mine = _brought.setdefault(a.id, [])
        mapped = all(r in getattr(world, "resource_regions", ()) for r in wanted_regions([a]))   # the streets all round are known
        if len(mine) < WANT and now - _placed.get(a.id, 0.0) > 3.0 and mapped:
            _placed[a.id] = now
            far = 45.0 if MODE == "load" else world.sight_m(a) * TUNE["herd_see_mult"] + 22
            found = _street(world, a, far)
            if found is None:
                continue
            d, ang, p = found
            heading = ang + math.pi                                # back along the clear line
            h = herds.add(world, p, 60, heading=heading, seed=41 + 97 * len(mine))
            mine.append((h.id, now))
            print(f"herd {h.id} put {d:.0f} m from survivor {a.id}, mode {MODE}", flush=True)
        if MODE == "load":
            for hid, at in mine:
                if hid in world.herds and now - at > 20.0:
                    herds.wake(world, world.herds[hid], a)
    _real_step(world, dt)
    if os.environ.get("OSZ_HERD_TRACE") and int(now) % 5 == 0 and int(now) != _placed.get("trace"):
        _placed["trace"] = int(now)
        for a in world.actors.values():
            print(f"t{int(now) % 1000} survivor {a.id} dead={a.dead} inside={world.buildings.containing((a.lat, a.lng)) is not None} "
                  + " ".join(f"{h.id}:{dist_m(a.lat, a.lng, h.lat, h.lng):.0f}m,seen={herds._in_view(world, h, a)},detour={h.detour_until > now}"
                             f",at=({delta_m(a.lat, a.lng, h.lat, h.lng)[0]:.0f},{delta_m(a.lat, a.lng, h.lat, h.lng)[1]:.0f}),face={math.degrees(h.facing) % 360:.0f}"
                             f",line={world.visible((a.lat, a.lng), (h.lat, h.lng))},edge={herds.nearest(h, a.lat, a.lng)[1]:.0f}m,reach={world.sight_m(a) * TUNE['herd_see_mult']:.0f}"
                             f",ahead={_ahead(world, h)}"
                             for h in world.herds.values())
                  + f" woken={list(world.herd_woken)} zeds={len(world.zeds)}", flush=True)


herds.step = step

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8021, log_level="warning")
