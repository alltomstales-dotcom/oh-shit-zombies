"""What a player remembers of the map: ground walked past and things last seen there.

Kept per player and across lives, apart from a life's `explored` list, which only feeds
experience. Nothing here is live. A cell says "you have been near this"; a mark says what a
container held the last time this player looked, and when. Either may be out of date, and no
zombie or unopened container is ever recorded. A pin is the player's own note on their map: it
says nothing about the world and changes nothing in it.
"""
from __future__ import annotations

import math
from functools import lru_cache

from app.geo import _BASE32, _decode_bbox, cell_of

PRECISION = 8                      # a geohash-8 cell is about 38 m east-west by 19 m north-south
CELL_SPAN = (180.0 / 2 ** 20, 360.0 / 2 ** 20)      # degrees of latitude, longitude
MAX_CELLS = 5000                   # about 3.5 square km; the oldest days go first
MAX_MARKS = 200
STEP_M = 8.0                       # look around again after moving this far
MARKS_EVERY_S = 3.0
VIEW_M = 1200.0                    # how far from the asked-for point one reply reaches
VIEW_CELLS = 3000
MAX_PINS = 40
PIN_KINDS = ("supplies", "danger", "shelter", "note")
PIN_REACH_M = 3500.0               # a little further than the overview can be dragged
RESOURCE_KINDS = ("tree", "tree", "rubble", "rock", "ore", "forage", "pond")    # survival.nodes, by index
# Sample points around the survivor: roughly what is in plain view on the street.
OFFSETS = [(dx, dy) for dx in (-38.0, 0.0, 38.0) for dy in (-38.0, -19.0, 0.0, 19.0, 38.0)]

_bbox = lru_cache(maxsize=40000)(_decode_bbox)


def blank() -> dict:
    return {"v": 1, "cells": {}, "marks": {}, "death": None}


def _day(now: float) -> int:
    return int(now // 86400)


def _metres(lat0, lng0, lat1, lng1) -> float:
    return math.hypot((lat1 - lat0) * 111320.0, (lng1 - lng0) * 111320.0 * math.cos(math.radians(lat0)))


def _shift(lat, lng, east, north):
    return lat + north / 111320.0, lng + east / (111320.0 * math.cos(math.radians(lat)))


def for_player(world, a) -> dict:
    """This player's memory, made on first use from what the current life has already walked."""
    mem = world.memories.get(a.id)
    if mem is None:
        mem = world.memories[a.id] = blank()
        seeded = _day(a.born if a.born > 0 else world.now)
        for coarse in a.explored[-MAX_CELLS // 32:]:          # geohash-7: a block walked, no finer than that
            for ch in _BASE32:
                mem["cells"][coarse + ch] = seeded
        if mem["cells"]:
            world.memory_dirty.add(a.id)
    return mem


def observe(world, a) -> None:
    """Called every step. Cheap unless the survivor has moved or a shelf has changed."""
    if a.dead or (a.lat == 0.0 and a.lng == 0.0) or a.location_loading_until:
        return
    mem = for_player(world, a)
    state = world.memory_state.setdefault(a.id, {"at": None, "day": None, "marks_at": -1e9})
    at, today = state["at"], _day(world.now)
    if at is None or state["day"] != today or _metres(at[0], at[1], a.lat, a.lng) >= STEP_M:
        state["at"], state["day"] = (a.lat, a.lng), today
        cells, changed = mem["cells"], False
        for east, north in OFFSETS:
            c = cell_of(*_shift(a.lat, a.lng, east, north), PRECISION)
            if cells.get(c) != today:
                cells[c] = today
                changed = True
        if changed:
            if len(cells) > MAX_CELLS:
                for c, _ in sorted(cells.items(), key=lambda kv: kv[1])[:len(cells) - MAX_CELLS + MAX_CELLS // 10]:
                    del cells[c]
            world.memory_dirty.add(a.id)
    if world.now - state["marks_at"] >= MARKS_EVERY_S:
        state["marks_at"] = world.now
        marks = mem["marks"]
        for sid, shelf in a.loot_shelves.items():
            left = sum(i["qty"] for i in shelf["items"])
            old = marks.get(sid)
            if old is None or old["left"] != left:
                marks[sid] = {"kind": shelf.get("kind", "chest"), "lat": round(shelf["lat"], 6),
                              "lng": round(shelf["lng"], 6), "left": left, "t": int(world.now)}
                world.memory_dirty.add(a.id)
        from app.game import vehicles
        seen_cars = mem.setdefault("vehicles", {})
        for car in vehicles.view(world, a):
            mark = {"kind": car["kind"], "lat": round(car["lat"], 6), "lng": round(car["lng"], 6), "t": int(world.now)}
            old = seen_cars.get(car["id"])
            if old is None or old["lat"] != mark["lat"] or old["lng"] != mark["lng"] or world.now-old["t"] >= 60:
                seen_cars[car["id"]] = mark
                world.memory_dirty.add(a.id)
        if len(seen_cars) > MAX_MARKS:
            for vid, _ in sorted(seen_cars.items(), key=lambda kv: kv[1]["t"])[:len(seen_cars)-MAX_MARKS]:
                del seen_cars[vid]
        if len(marks) > MAX_MARKS:
            for sid, _ in sorted(marks.items(), key=lambda kv: kv[1]["t"])[:len(marks) - MAX_MARKS]:
                del marks[sid]


def note_death(world, a) -> None:
    mem = for_player(world, a)
    mem["death"] = {"lat": round(a.lat, 6), "lng": round(a.lng, 6), "t": int(world.now),
                    "cause": (a.death or {}).get("cause", ""),
                    "floor_level":a.floor_level,"floor_building":a.floor_building,
                    "corpse":(a.death or {}).get('corpse')}
    world.memory_dirty.add(a.id)


def _pins(mem, now) -> list:
    return [{"id": pid, "kind": p["kind"], "lat": p["lat"], "lng": p["lng"], "age_s": max(0, int(now - p["t"]))}
            for pid, p in mem.get("pins", {}).items()]


def pin(world, a, op="add", lat=None, lng=None, kind="note", pin=None, **_) -> dict:
    """Put a pin on the player's own map, or take one off. Like looking at the map, it is not an action."""
    mem = for_player(world, a)
    pins = mem.setdefault("pins", {})
    if op == "remove":
        if pins.pop(str(pin), None) is None:
            return {"ok": False, "why": "that pin is already gone", "pins": _pins(mem, world.now)}
    elif op == "add":
        if kind not in PIN_KINDS:
            return {"ok": False, "why": "unknown kind of pin"}
        if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and math.isfinite(lat) and math.isfinite(lng)
                and abs(lat) <= 90 and abs(lng) <= 180 and _metres(a.lat, a.lng, lat, lng) <= PIN_REACH_M):
            return {"ok": False, "why": "that is further than your map reaches"}
        if len(pins) >= MAX_PINS:
            return {"ok": False, "why": f"A map holds {MAX_PINS} pins. Remove one first."}
        mem["pin_seq"] = mem.get("pin_seq", 0) + 1
        pins[str(mem["pin_seq"])] = {"kind": kind, "lat": round(lat, 6), "lng": round(lng, 6), "t": int(world.now)}
    else:
        return {"ok": False, "why": "unknown pin action"}
    world.memory_dirty.add(a.id)
    return {"ok": True, "pins": _pins(mem, world.now)}


def _spent(a, lat, lng) -> list:
    """Trees felled, rock quarried out and the like: this player's own used-up spots, from their home record."""
    home = a.home or {}
    out = []
    for oid, left in home.get("nodes", {}).items():
        at = home.get("node_positions", {}).get(oid)
        if left > 0 or not at or _metres(lat, lng, at[0], at[1]) > VIEW_M * 3:
            continue
        try:
            kind = RESOURCE_KINDS[int(oid.rsplit(":", 1)[1])]
        except (ValueError, IndexError):
            continue
        out.append({"id": oid, "kind": kind, "lat": round(at[0], 6), "lng": round(at[1], 6)})
    return out


def view(world, a, lat: float | None = None, lng: float | None = None) -> dict:
    """The part of this player's memory around a point: what the Area overview draws."""
    mem = for_player(world, a)
    if lat is None or lng is None or not (math.isfinite(lat) and math.isfinite(lng)):
        lat, lng = a.lat, a.lng
    today = _day(world.now)
    dlat, dlng = VIEW_M / 111320.0, VIEW_M / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    cells = []
    for c, seen in mem["cells"].items():
        lat_lo, _, lng_lo, _ = _bbox(c)
        if abs(lat_lo - lat) <= dlat and abs(lng_lo - lng) <= dlng:
            cells.append([round(lat_lo, 6), round(lng_lo, 6), max(0, today - seen)])
    if len(cells) > VIEW_CELLS:
        cells.sort(key=lambda c: (c[0] - lat) ** 2 + ((c[1] - lng) * math.cos(math.radians(lat))) ** 2)
        del cells[VIEW_CELLS:]
    marks = [{"id": sid, "kind": m["kind"], "lat": m["lat"], "lng": m["lng"], "left": m["left"],
              "age_s": max(0, int(world.now - m["t"]))}
             for sid, m in mem["marks"].items() if _metres(lat, lng, m["lat"], m["lng"]) <= VIEW_M * 3]
    death = mem.get("death")
    from app.game.floors import root
    r=root(world)
    bodies={**r.upper_corpses,**r.corpses}
    for level in r.levels.values():bodies.update(level.corpses)
    recoveries=[{'id':b['id'],'lat':b['lat'],'lng':b['lng'],'floor_level':b.get('floor_level',0),
                 'floor_building':b.get('floor_building'),'remaining_s':max(0,int(b['until']-world.now)),
                 'empty':not b['items']} for b in bodies.values()
                if b.get('owner')==a.id and b['until']>world.now]
    recoveries.sort(key=lambda b:b['remaining_s'],reverse=True)
    return {"ok": True, "lat": lat, "lng": lng, "span": list(CELL_SPAN), "cells": cells, "marks": marks,
            "death": dict(death, age_s=max(0, int(world.now - death["t"]))) if death else None,
            "known": len(mem["cells"]), "pins": _pins(mem, world.now), "spent": _spent(a, lat, lng),"recoveries":recoveries[:12],
            "vehicles":[dict(m, id=vid, age_s=max(0,int(world.now-m["t"]))) for vid,m in mem.get("vehicles",{}).items()
                        if _metres(lat,lng,m["lat"],m["lng"]) <= VIEW_M*3]}
