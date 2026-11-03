"""Does a zombie ever turn up inside a home that is shut?

    python -m tools.sealed_home_soak [--seeds 1 2 3] [--seconds 3600] [--owner in|away|both]

One synthetic town (tools.geometry_load.town, no network, no database) with everything that makes
zombies running at once: the fixed packs of the street cells, the director's stragglers and
ambushes for two survivors, and a herd of sixty that is woken on the middle street. Every house in
the town is somebody's shut home, so that a spawn landing in one is likely rather than a one in a
thousand chance (one house is a thousandth of the town). The owner of the middle house either sits
in it or is two streets away; a second survivor walks round the block making noise and is kept
alive so that the pressure lasts.

Every tick, any zombie whose position is inside a house while that house is shut (every outside
opening closed and whole) is counted, with how it was made. A zombie that breaks a door or window
down and walks in is not counted: the run notes the break-in, mends the opening and takes away
every zombie in or against that house (one standing in a frame as it is mended would otherwise
step in through a whole window), and the watch goes on.
"""
from __future__ import annotations

import argparse
import math
import random

from app.game import herds as herd_rules
from app.game.content import STARTER_KIT
from app.game.director import Director
from app.game.sim import Actor, World, dist_m, shift
from app.game.spawn import Spawner
from tools.geometry_load import HZ, town


def made_by(zid) -> str:
    return {"h": "herd", "t": "director"}.get(str(zid)[:1], "street pack")


def run(seed=1, seconds=3600, owner="in"):
    w = World(rng=random.Random(seed), spawner=Spawner(density=1.0, salt=str(seed)), light_fn=lambda *_: 1.0)
    d = Director(w)
    centre, records = town(0, 144); w.buildings.add(records)
    home = min((b for b in w.buildings.items.values() if b.rooms),
               key=lambda b: dist_m(*b.ll(b.rooms[0]["pos"]), *centre))
    room = home.ll(home.rooms[0]["pos"])
    for n, b in enumerate(w.buildings.items.values()):                 # every house is a shut home
        w.homes[1 if b is home else 1000 + n] = {"building": b.id, "defenses": {}}
    outside = {b.id: [o for o in b.openings if o["label"] != "Room door"] for b in w.buildings.items.values()}
    people = []
    for pid in (1, 2):
        a = Actor(id=pid, lat=centre[0], lng=centre[1], born=-10 * 86400)
        for code, qty in STARTER_KIT:
            a.add(code, qty)
        w.add_actor(a, 1.0); people.append(a)
    keeper, walker = people
    start = room if owner == "in" else w.spawn_point(*shift(*room, 60, 55))
    w.set_position(keeper.id, start[0], start[1], 3.0)
    lap = [w.spawn_point(*shift(*room, 26 * math.cos(k * math.tau / 12), 26 * math.sin(k * math.tau / 12))) for k in range(12)]
    lap = [p for p in lap if p]
    now, seen, breaches, most, herd_at, woke = 1.0, {}, [], 0, int(seconds * HZ * 0.3), 0
    made = {"street pack": 0, "director": 0, "herd": 0}; known = set()
    for tick in range(int(seconds * HZ)):
        now += 1.0 / HZ
        for a in people:
            a.hp, a.wounds, a.dead = 100.0, [], False
        goal = lap[(tick // (HZ * 8)) % len(lap)]                       # round the block, a corner every eight seconds
        dy, dx = (goal[0] - walker.lat) * 111320, (goal[1] - walker.lng) * 111320 * math.cos(math.radians(goal[0]))
        far = math.hypot(dx, dy) or 1.0
        p = w.buildings.move((walker.lat, walker.lng), shift(walker.lat, walker.lng, dx / far * min(far, 0.5), dy / far * min(far, 0.5)))
        w.set_position(walker.id, p[0], p[1], 3.0)
        if owner == "in":
            w.set_position(keeper.id, room[0], room[1], 3.0)
        if tick % (HZ * 25) == 0:
            w.noise(walker.lat, walker.lng, 45.0, walker)
        if tick == herd_at:                                             # a herd on the home's street, woken at once
            at = w.spawn_point(*shift(*room, 0, 18))
            if at:
                woke = herd_rules.wake(w, w.add_herd(at, 60, heading=0.0, seed=seed), walker)
        before = {z.id: (z.lat, z.lng) for z in w.zeds.values()}
        w.step(now); d.tick()
        for zid in w.zeds.keys() - known:
            known.add(zid); made[made_by(zid)] += 1
        most = max(most, len(w.zeds))
        for b in w.buildings.items.values():
            if any(o["open"] or o["broken"] for o in outside[b.id]):      # judged here, not by the rule under test
                breaches.append((round(now), b.id))
                for o in outside[b.id]:
                    o["open"], o["broken"], o["damage"] = False, False, 0
                w.buildings.revision += 1
                middle = b.ll(b.rooms[0]["pos"])
                for z in [z for z in w.zeds.values() if dist_m(z.lat, z.lng, *middle) < 14]:
                    del w.zeds[z.id]
        for z in w.zeds.values():
            b = w.buildings.containing((z.lat, z.lng))
            if b is not None and z.id not in seen:
                was = before.get(z.id)
                seen[z.id] = (round(now, 1), made_by(z.id), z.state, "new" if was is None else "was inside" if b.contains(was) else f"came {dist_m(*was, z.lat, z.lng):.1f} m")
    return dict(seed=seed, owner=owner, seconds=seconds, made=made, most=most, woke=woke, breaches=breaches, inside_while_shut=seen)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3]); ap.add_argument("--seconds", type=float, default=3600)
    ap.add_argument("--owner", choices=("in", "away", "both"), default="both")
    a = ap.parse_args(); bad = 0
    print("seed owner | zombies made: street packs, director, herd | most at once | broken into | inside while shut")
    for seed in a.seeds:
        for owner in (("in", "away") if a.owner == "both" else (a.owner,)):
            r = run(seed, a.seconds, owner); bad += len(r["inside_while_shut"])
            print(f"{seed:4d} {owner:5s} | {r['made']['street pack']:5d} {r['made']['director']:5d} {r['made']['herd']:5d} | {r['most']:4d} |"
                  f" {len(r['breaches'])} | {len(r['inside_while_shut'])} {list(r['inside_while_shut'].items())[:4]}", flush=True)
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
