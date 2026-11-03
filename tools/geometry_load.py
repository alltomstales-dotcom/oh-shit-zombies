"""How does one server tick grow with the map that has been visited?

    python -m tools.geometry_load [--towns 1 4 12] [--per-town 600] [--players 3] [--seconds 60] [--herds 0] [--size 60] [--awake]

Builds synthetic towns (a street grid of houses, no network), puts a few walking survivors in the
first ones and leaves the rest loaded but empty, as a long-running server would have them. Then it
runs the ordinary simulation step and the per-player state view on a fake clock and prints what
each costs. A door is opened every few seconds, because every opening used to rebuild the whole
search grid. Nothing here touches a database.

--herds N puts N herds of --size (sixty) on the streets about seventy metres from the survivors, in sight
but not near enough to be noticed; with --awake they have noticed and are sixty zombies each, and
the survivors are kept alive so that the load lasts for the whole run.
"""
from __future__ import annotations

import argparse
import math
import random
import statistics as st
import time

from app.game import herds as herd_rules
from app.game.content import STARTER_KIT
from app.game.sim import Actor, World, shift
from app.game.spawn import Spawner

HZ = 5
BASE = (44.9778, -93.2650)


def town(index, per_town):
    """A grid of 10 m x 14 m houses on a 24 m pitch, with a wider street every fourth row and column."""
    lat0, lng0 = BASE[0] + 0.5 * (index % 4), BASE[1] + 0.7 * (index // 4)
    side = math.ceil(math.sqrt(per_town)); out = []
    for n in range(per_town):
        i, j = n % side, n // side
        x = i * 24 + (i // 4) * 10 - side * 13; y = j * 24 + (j // 4) * 10 - side * 13
        corners = [shift(lat0, lng0, x + dx, y + dy) for dx, dy in ((0, 0), (10, 0), (10, 14), (0, 14))]
        out.append({"id": f"t{index}:{n}", "name": "", "source": "osm", "type": "house", "outline": [list(c) for c in corners]})
    return (lat0, lng0), out


def run(towns, per_town, players, seconds, herds=0, seed=1, awake=False, size=60):
    w = World(rng=random.Random(seed), spawner=Spawner(density=1.0, salt=str(seed)), light_fn=lambda *_: 1.0)
    centres = []
    for t in range(towns):
        c, records = town(t, per_town); centres.append(c)
        w.buildings.add(records)
    actors = []
    for p in range(players):
        c = centres[p % towns]; a = Actor(id=p + 1, lat=c[0], lng=c[1], born=-10 * 86400)
        for code, qty in STARTER_KIT:
            a.add(code, qty)
        start = shift(c[0], c[1], -5 + 3 * p, -7)                   # on a street, not in a house
        w.add_actor(a, 1.0); w.set_position(a.id, start[0], start[1], 3.0); actors.append(a)
    for h in range(herds):
        a = actors[h % len(actors)]; k = h // len(actors)
        at = w.spawn_point(*shift(a.lat, a.lng, 5 + 34 * k, (25 if awake else 70) + 30 * k))    # up the street from them
        herd = w.add_herd(at, size, heading=0.0, seed=7 + h)
        if awake:
            herd_rules.wake(w, herd, a)
    doors = [o for b in list(w.buildings.items.values())[:50] for o in b.openings if o.get("kind") == "door"]
    step_ms, view_ms, now, seen = [], [], 1.0, {}
    rng = random.Random(seed)
    headings = [rng.uniform(0, math.tau) for _ in actors]
    walking = 0
    for tick in range(int(seconds * HZ)):
        now += 1.0 / HZ
        walking += len(w.herds)
        for k, a in enumerate(actors):
            if a.dead:
                continue
            if awake:
                a.hp, a.wounds = 100.0, []
            if tick % 40 == 0:
                headings[k] += rng.uniform(-1.2, 1.2)
            p = shift(a.lat, a.lng, math.cos(headings[k]) * 0.27, math.sin(headings[k]) * 0.27)
            w.set_position(a.id, p[0], p[1], 3.0)
        if tick % 25 == 12 and doors:                               # somebody, somewhere, opens a door
            o = doors[(tick // 25) % len(doors)]; o["open"] = not o["open"]; w.buildings.revision += 1
        t0 = time.perf_counter(); w.step(now); step_ms.append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        for a in actors:
            if not a.dead:                                          # as the hub asks: walls only when they changed
                seen[a.id] = w.view(a.id, seen.get(a.id))["building_key"]
        view_ms.append((time.perf_counter() - t0) * 1000)
    q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(len(xs) * p))]
    return dict(towns=towns, buildings=len(w.buildings.items), zeds=len(w.zeds), stashes=len(w.stashes),
                herds=len(w.herds), herd_ticks=walking, hunting=sum(z.state in herd_rules.HUNTING for z in w.zeds.values()),
                step_mean=st.mean(step_ms), step_p95=q(step_ms, .95), step_max=max(step_ms),
                view_mean=st.mean(view_ms), view_p95=q(view_ms, .95), view_max=max(view_ms),
                alive=sum(not a.dead for a in actors))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--towns", type=int, nargs="+", default=[1, 4, 12]); ap.add_argument("--per-town", type=int, default=600)
    ap.add_argument("--players", type=int, default=3); ap.add_argument("--seconds", type=float, default=60); ap.add_argument("--herds", type=int, default=0); ap.add_argument("--awake", action="store_true"); ap.add_argument("--size", type=int, default=60)
    a = ap.parse_args()
    print(f"{a.players} survivors walking for {a.seconds:.0f} s at {HZ} ticks a second, {a.per_town} houses a town" + (f", {a.herds} herds of {a.size} {'awake' if a.awake else 'walking'}" if a.herds else ""))
    print("towns buildings zeds stashes | step ms mean  p95   max | views ms mean  p95   max | alive | herds left, zombies hunting")
    for t in a.towns:
        r = run(t, a.per_town, a.players, a.seconds, a.herds, awake=a.awake, size=a.size)
        print(f"{r['towns']:5d} {r['buildings']:9d} {r['zeds']:4d} {r['stashes']:7d} | {r['step_mean']:12.2f} {r['step_p95']:5.1f} {r['step_max']:5.0f} |"
              f" {r['view_mean']:13.2f} {r['view_p95']:5.1f} {r['view_max']:5.0f} | {r['alive']}/{a.players} | {r['herds']}, {r['hunting']}", flush=True)


if __name__ == "__main__":
    main()
