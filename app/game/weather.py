"""What everyone in a town shares because it comes from the real clock, never from one life.

Rain and the helicopter are pure functions of place and time: no state, nothing to save, and two
players standing in the same area always get the same answer. A survivor's own day number is the
only thing here that belongs to a life, and it changes nothing: it is a calendar, not a trigger.
"""
from __future__ import annotations

from functools import lru_cache

from app.daylight import light_level
from app.game.content import TUNE
from app.geo import _decode_bbox, cell_of
from app.rng import seeded

AREA = 5                 # a geohash-5 cell is about 4.9 km across: a town, or a district of a city


def area_of(lat: float, lng: float) -> str:
    return cell_of(lat, lng, AREA)


def life_day(a, now: float) -> int:
    """Day 1 is the day a survivor starts. Real days, counted from that moment."""
    return int(max(0.0, now - a.born) // 86400) + 1


@lru_cache(maxsize=4096)
def _rain_block(area: str, block: int) -> bool:
    return seeded(f"rain:{area}:{block}").random() < TUNE["rain_chance"]


def rain(lat: float, lng: float, now: float) -> dict | None:
    """Raining here now? Decided in blocks of a few hours per area."""
    size = TUNE["rain_block_s"]
    block = int(now // size)
    if not _rain_block(area_of(lat, lng), block):
        return None
    return {"until": (block + 1) * size}


@lru_cache(maxsize=4096)
def _heli_window(area: str, block: int) -> tuple[float, float, float] | None:
    """(heard from, overhead from, gone at) for the pass in this block, if there is one."""
    size, warn, over = TUNE["heli_block_s"], TUNE["heli_warn_s"], TUNE["heli_over_s"]
    rng = seeded(f"heli:{area}:{block}")
    if rng.random() >= TUNE["heli_chance"]:
        return None
    heard = block * size + rng.uniform(0.0, size - warn - over)
    # It flies by day only. Night is already the harder half, and bots that stayed out under a
    # night pass died 42% of the time against 24% without one. Judged at the middle of the area,
    # so everyone in it agrees.
    lat_lo, lat_hi, lng_lo, lng_hi = _decode_bbox(area)
    if light_level((lat_lo + lat_hi) / 2, (lng_lo + lng_hi) / 2, int(heard)) < TUNE["heli_min_light"]:
        return None
    return heard, heard + warn, heard + warn + over


def helicopter(lat: float, lng: float, now: float) -> dict | None:
    """The pass in progress over this area, if any: heard first, then overhead."""
    area, block = area_of(lat, lng), int(now // TUNE["heli_block_s"])
    w = _heli_window(area, block)
    if w is None or not w[0] <= now < w[2]:
        return None
    return {"id": f"{area}:{block}", "phase": "coming" if now < w[1] else "overhead",
            "overhead": w[1], "ends": w[2]}


def next_helicopter(lat: float, lng: float, now: float, blocks: int = 64) -> tuple[float, float, float] | None:
    """For tests and tools: the next pass at or after `now` in this area."""
    area, first = area_of(lat, lng), int(now // TUNE["heli_block_s"])
    for block in range(first, first + blocks):
        w = _heli_window(area, block)
        if w and w[2] > now:
            return w
    return None


def step(world, a) -> None:
    """Per survivor, per step: say when the helicopter comes and goes, and let it draw a crowd.

    Overhead, every few seconds, it is a loud noise at each survivor who is out in the open, so
    every idle pack within its reach walks toward them. Indoors it passes over. A survivor in
    their first hour is left alone: the event is for people who have a door to get behind.
    """
    if a.dead or (a.lat == 0.0 and a.lng == 0.0):
        return
    h = helicopter(a.lat, a.lng, world.now)
    seen = world.heli_seen.get(a.id)
    key = (h["id"], h["phase"]) if h else None
    if key != seen:
        if key is None:
            world.heli_seen.pop(a.id, None)
            world._ev(a, "heli", phase="gone")
        else:
            world.heli_seen[a.id] = key
            world._ev(a, "heli", phase=h["phase"], overhead=round(h["overhead"]), ends=round(h["ends"]))
    if not h or h["phase"] != "overhead":
        return
    if world.now - a.born < TUNE["heli_spare_new_s"] or world.buildings.containing((a.lat, a.lng)) is not None:
        return
    if world.now - world.heli_pulse.get(a.id, -1e9) >= TUNE["heli_pulse_s"]:
        world.heli_pulse[a.id] = world.now
        world.noise(a.lat, a.lng, TUNE["heli_pull_m"], a, certain=True)


def view(world, a) -> dict:
    r, h = rain(a.lat, a.lng, world.now), helicopter(a.lat, a.lng, world.now)
    return {"rain": bool(r), "rain_until": r["until"] if r else None,
            "heli": {"phase": h["phase"], "overhead": round(h["overhead"]), "ends": round(h["ends"]),
                     "sheltered": world.buildings.containing((a.lat, a.lng)) is not None} if h else None}
