"""A herd: sixty or so of them moving as one thing.

A herd is rare, and it is terrain rather than a fight: you hear it before you see it, you see the
mass from further off than you would see one zombie, and the right answer is to go round. While it
walks it is a single object with a count, so it costs the server no more than one zombie. It
becomes individual zombies only when it notices someone, and when they have all lost whoever that
was, those left gather into one thing again and walk on.

When and where herds cross is a pure function of the map region and the real clock, like the
weather: everyone near it meets the same herd, and a restart does not invent another. Once a herd
is in the world it walks: it keeps to the streets, slides along walls, turns aside when it is
stuck and turns towards a loud noise. So its exact place is world state, shared by whoever is
there and forgotten when nobody is.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from app.game.content import TUNE, ZED_KINDS, ZED_VARIANTS
from app.geo import _decode_bbox, cell_of, neighbors
from app.rng import seeded

REGION = 6               # a geohash-6 cell is about 1.2 km by 0.6 km: a few blocks of a town
GOLDEN = 2.399963229728653
HUNTING = ("alert", "chase", "engaged", "stagger", "down", "rising")


@dataclass
class Herd:
    id: str
    lat: float
    lng: float
    count: int
    heading: float           # where it is going: radians, east = 0, north = pi/2
    seed: int
    until: float             # when it has passed through
    facing: float = 0.0      # the way the column lies; follows the walk, a little behind
    stuck: float = 0.0
    detour: float = 0.0
    detour_until: float = 0.0
    side: int = 0            # which way it is going round whatever is in its way
    blocked_at: float = 0.0
    wakes: int = 0


def spread(count: int) -> tuple[float, float]:
    """Half the length and half the width of the column, in metres: long and narrow, to fit a street."""
    return 1.9 * math.sqrt(count), 0.55 * math.sqrt(count)


def offsets(count: int, seed: int, facing: float):
    """Where each figure walks around the middle, as (east, north) metres. The client draws the
    same pattern from the same numbers, so the crowd on screen is the crowd that breaks up."""
    L, W = spread(count)
    phase, c, s = (seed % 360) * math.pi / 180, math.cos(facing), math.sin(facing)
    out = []
    for i in range(count):
        r, t = math.sqrt((i + 0.5) / count), i * GOLDEN + phase
        u, v = L * r * math.cos(t), W * r * math.sin(t)
        out.append((u * c - v * s, u * s + v * c))
    return out


def nearest(h: Herd, lat: float, lng: float):
    """The point on the column's middle line nearest to somewhere, and how far that is."""
    from app.game.sim import delta_m, shift
    dx, dy = delta_m(h.lat, h.lng, lat, lng)
    c, s, reach = math.cos(h.facing), math.sin(h.facing), spread(h.count)[0] * 0.8
    u = max(-reach, min(reach, dx * c + dy * s))
    return shift(h.lat, h.lng, u * c, u * s), math.hypot(dx - u * c, dy - u * s)


@lru_cache(maxsize=4096)
def _crossing(region: str, block: int) -> dict | None:
    """The herd that crosses this region in this block of hours, if one does."""
    size, cross = TUNE["herd_block_s"], TUNE["herd_cross_s"]
    rng = seeded(f"herd:{region}:{block}")
    if rng.random() >= TUNE["herd_chance"]:
        return None
    from app.game.sim import shift
    t0 = block * size + rng.uniform(0.0, size - cross)
    la0, la1, ln0, ln1 = _decode_bbox(region)
    mid = (la0 + (la1 - la0) * rng.uniform(0.3, 0.7), ln0 + (ln1 - ln0) * rng.uniform(0.3, 0.7))
    heading, length = rng.uniform(0.0, math.tau), TUNE["herd_speed"] * cross
    start = shift(mid[0], mid[1], -math.cos(heading) * length / 2, -math.sin(heading) * length / 2)
    return {"id": f"{region}:{block}", "t0": t0, "t1": t0 + cross, "start": tuple(start), "heading": heading,
            "count": rng.randint(int(TUNE["herd_min"]), int(TUNE["herd_max"])), "seed": rng.randrange(1 << 30)}


def planned(c: dict, now: float) -> tuple[float, float]:
    """Where the schedule puts a herd at a moment: a straight line. Used only to bring it in."""
    from app.game.sim import shift
    d = TUNE["herd_speed"] * min(max(now - c["t0"], 0.0), c["t1"] - c["t0"])
    return tuple(shift(c["start"][0], c["start"][1], math.cos(c["heading"]) * d, math.sin(c["heading"]) * d))


def due(lat: float, lng: float, now: float) -> list[dict]:
    """Crossings under way in the region around a point and the regions beside it."""
    cell, block = cell_of(lat, lng, REGION), int(now // TUNE["herd_block_s"])
    out = []
    for region in [cell] + neighbors(cell):
        c = _crossing(region, block)
        if c is not None and c["t0"] <= now < c["t1"]:
            out.append(c)
    return out


def next_crossing(lat: float, lng: float, now: float, blocks: int = 2000) -> dict | None:
    """For tests and tools: the next herd through the region a point is in."""
    region, first = cell_of(lat, lng, REGION), int(now // TUNE["herd_block_s"])
    for block in range(first, first + blocks):
        c = _crossing(region, block)
        if c is not None and c["t1"] > now:
            return c
    return None


def add(world, point, count: int, heading: float = 0.0, seed: int = 1, until: float | None = None, hid: str | None = None) -> Herd:
    """Put a herd in the world."""
    world.herd_seq += 1
    h = Herd(id=hid or f"made:{world.herd_seq}", lat=point[0], lng=point[1], count=count, heading=heading,
             facing=heading, seed=seed, until=world.now + 3600.0 if until is None else until)
    world.herds[h.id] = h
    return h


def _notices(world, h: Herd, a, dt: float) -> bool:
    """The rule one zombie follows, from the nearest part of the column: within sight with a clear
    line, or near enough to hear moving feet through a wall. Sixty pairs of eyes are quicker."""
    T = world.T
    if world.arriving(a):
        return False
    p, d = nearest(h, a.lat, a.lng)
    rngm = world._zed_range(None, a)
    if d > rngm:
        return False
    if not (world.visible(p, (a.lat, a.lng)) or (a.speed > .4 and d < world.heard_m(a) * T["noise_wall_mult"])):
        return False
    if d < rngm * 0.5:
        return True
    rate = T["herd_notice_rate"] * (T["grace_notice"] if world.now - a.born < T["grace_h"] * 3600 else 1.0)
    return world.rng.random() < 1.0 - math.exp(-rate * dt)


def wake(world, h: Herd, a) -> int:
    """It has noticed someone: the one thing becomes its zombies, where the figures walked."""
    from app.game.sim import Zed, dist_m, shift
    T, rng, now = world.T, world.rng, world.now
    spec = ZED_KINDS["shambler"]                               # a herd is the slow kind: a wall, not a sprint
    h.wakes += 1
    for i, (dx, dy) in enumerate(offsets(h.count, h.seed, h.facing)):
        p = (h.lat, h.lng)
        for k in (1.0, 0.6, 0.3):                              # a place behind a wall is pulled in towards the middle
            q = shift(h.lat, h.lng, dx * k, dy * k)
            if world.buildings.clear((h.lat, h.lng), q):
                p = q
                break
        hp = float(rng.randint(*spec["hp"]))
        z = Zed(id=f"h:{h.id}:{h.wakes}.{i}", lat=p[0], lng=p[1], kind="shambler", hp=hp, hp_max=hp,
                speed=rng.uniform(*spec["speed"]), variant=(h.seed + i) % ZED_VARIANTS, home=(p[0], p[1]),
                temp=True, next_groan=now + rng.uniform(0.5, 9.0))
        z.state, z.target, z.last_seen = "alert", a.id, now
        z.t_state = now + rng.uniform(0.4, 2.6)                # heads turn over a couple of seconds, not at once
        world.zeds[z.id] = z
    world.herds.pop(h.id, None)
    world.herd_spent[h.id] = h.until
    world.herd_woken[h.id] = {"herd": h, "calm": now, "check": now + 1.0}
    world.herd_told = {k for k in world.herd_told if k[1] != h.id}
    for x in world.actors.values():
        if not x.dead and dist_m(x.lat, x.lng, h.lat, h.lng) <= T["herd_hear_m"]:
            world._ev(x, "herd", op="woke", n=h.count, mine=x.id == a.id)
    a.last_threat = now
    return h.count


def _regather(world) -> None:
    """Those of a woken herd that are left, once none of them is after anyone, are one thing again."""
    T, now = world.T, world.now
    for hid, rec in list(world.herd_woken.items()):
        if now < rec["check"]:
            continue
        rec["check"] = now + 1.0
        prefix = f"h:{hid}:"
        mine = [z for z in world.zeds.values() if z.id.startswith(prefix) and z.alive]
        if not mine:
            del world.herd_woken[hid]
            continue
        if any(z.state in HUNTING for z in mine):
            rec["calm"] = now
            continue
        if now - rec["calm"] < T["herd_regather_s"]:
            continue
        del world.herd_woken[hid]
        if len(mine) < T["herd_least"]:                        # too few to be a herd: they stay as zombies
            continue
        for z in mine:
            del world.zeds[z.id]
        old = rec["herd"]
        lat, lng = sum(z.lat for z in mine) / len(mine), sum(z.lng for z in mine) / len(mine)
        point = world.spawn_point(lat, lng) or (mine[0].lat, mine[0].lng)
        h = Herd(id=hid, lat=point[0], lng=point[1], count=len(mine), heading=old.heading, facing=old.heading,
                 seed=old.seed, until=max(old.until, now + T["herd_leave_s"]), wakes=old.wakes)
        world.herds[hid] = h
        world.herd_spent[hid] = h.until


def heard(world, lat: float, lng: float, radius: float, src=None) -> None:
    """A loud sound. A herd does not break up for a noise: all of it turns and walks that way.
    Made right beside it, the noise shows it who made it."""
    from app.game.sim import delta_m
    for h in list(world.herds.values()):
        p, d = nearest(h, lat, lng)
        if d > radius:
            continue
        if src is not None and not src.dead and d <= radius * world.T["herd_noise_wake"]:
            wake(world, h, src)
            continue
        if d > (radius if world.visible((lat, lng), p) else radius * .55):
            continue
        dx, dy = delta_m(h.lat, h.lng, lat, lng)
        h.detour = math.atan2(dy, dx)
        h.detour_until, h.stuck = world.now + min(world.T["herd_turn_s"], d / world.T["herd_speed"]), 0.0


def step(world, dt: float) -> None:
    """Once per tick: bring in herds that are due near someone, walk them, and let them notice."""
    from app.game.sim import bearing_deg, dist_m, shift
    T, now = world.T, world.now
    live = [a for a in world.actors.values()
            if not a.dead and a.transit_until <= now and not (a.lat == 0.0 and a.lng == 0.0)]
    if not live:
        world.herds.clear(); world.herd_told.clear()
        return
    for hid, until in list(world.herd_spent.items()):
        if until <= now and hid not in world.herd_woken:
            del world.herd_spent[hid]
    if world.herd_woken:
        _regather(world)
    # --- arrivals: only out of sight, and only while someone is near enough for it to matter
    if TUNE["herd_chance"] > 0:
        for a in live:
            if now - a.born < T["herd_spare_new_s"]:           # a survivor's first hour does not call one in
                continue
            for c in due(a.lat, a.lng, now):
                if c["id"] in world.herds or c["id"] in world.herd_spent:
                    continue
                p = planned(c, now)
                if dist_m(a.lat, a.lng, *p) > T["herd_load_m"]:
                    continue
                if any(dist_m(x.lat, x.lng, *p) < world.sight_m(x) * T["herd_see_mult"] + 20 for x in live):
                    continue
                point = world.spawn_point(p[0], p[1])
                if point is not None and world.buildings.containing(point) is None:
                    add(world, point, c["count"], c["heading"], c["seed"], c["t1"], c["id"])
    for h in list(world.herds.values()):
        near = sorted(((dist_m(a.lat, a.lng, h.lat, h.lng), a.id, a) for a in live), key=lambda r: r[:2])
        watched = any(d <= world.sight_m(a) * T["herd_see_mult"] + 20 for d, _, a in near)
        if near[0][0] > T["herd_load_m"] * 1.6 or (now >= h.until and not watched):
            del world.herds[h.id]                              # nobody left to meet it, or it has passed through unseen
            world.herd_told = {k for k in world.herd_told if k[1] != h.id}
            continue
        woke = next((a for d, _, a in near if d <= T["herd_hear_m"] and _notices(world, h, a, dt)), None) if dt > 0 else None
        if woke is not None:
            wake(world, h, woke)
            continue
        # --- the walk: straight on, keeping to the street, and aside for a while when stuck
        hd = h.detour if now < h.detour_until else h.heading
        m = T["herd_speed"] * dt
        before = (h.lat, h.lng)
        if world.buildings.containing(before) is not None:     # the map of this street arrived after the herd did
            before = _open_ground(world, before)
            if before is None:
                del world.herds[h.id]
                continue
            h.lat, h.lng = before
        after = world.buildings.move(before, shift(h.lat, h.lng, math.cos(hd) * m, math.sin(hd) * m))
        if world.buildings.containing(after) is not None:
            after = before                                     # a crowd does not file through a doorway
        if dt > 0:
            h.stuck = h.stuck + dt if dist_m(*before, *after) < m * 0.3 else max(0.0, h.stuck - dt)
            if h.stuck > 3.0:
                if not h.side or now - h.blocked_at > 60.0:    # a new obstacle: pick a way round and keep to it
                    h.side = world.rng.choice((-1, 1))
                h.blocked_at = now
                h.detour = hd + h.side * world.rng.uniform(1.0, 2.1)
                h.detour_until, h.stuck = now + world.rng.uniform(8.0, 16.0), 0.0
            turn = (hd - h.facing + math.pi) % math.tau - math.pi
            h.facing += max(-0.6 * dt, min(0.6 * dt, turn))
        h.lat, h.lng = after
        # --- said once to each survivor: heard as a direction first, then seen
        for d, _, a in near:
            if d > T["herd_hear_m"]:
                break
            op = "seen" if _in_view(world, h, a) else "heard"
            if (a.id, h.id, op) in world.herd_told or (a.id, h.id, "seen") in world.herd_told:
                continue
            world.herd_told.add((a.id, h.id, op))
            world._ev(a, "herd", op=op, n=h.count, d=round(d), b=round(bearing_deg(a.lat, a.lng, h.lat, h.lng)))


def _open_ground(world, start):
    """The nearest place that is not inside a building, for a herd that a building has landed on."""
    from app.game.sim import shift
    for radius in range(3, 91, 3):
        for i in range(16):
            p = shift(*start, math.cos(i * math.tau / 16) * radius, math.sin(i * math.tau / 16) * radius)
            if world.buildings.containing(p) is None and world.buildings.clear(p, p, 1.0):
                return p
    return None


def _in_view(world, h: Herd, a) -> bool:
    p, d = nearest(h, a.lat, a.lng)
    if d > world.sight_m(a) * world.T["herd_see_mult"]:
        return False
    return world.visible((a.lat, a.lng), p) or world.visible((a.lat, a.lng), (h.lat, h.lng))


def view(world, a) -> list:
    """The herds this survivor can make out: further off than one zombie shows, and only with a clear line."""
    return [[h.id, round(h.lat, 7), round(h.lng, 7), h.count, h.seed % 720, round(h.facing, 2)]
            for h in world.herds.values() if _in_view(world, h, a)]
