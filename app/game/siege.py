"""Siege: survive 30 minutes on a real landmark. A solo run in its own small world; survival is untouched.

Design and bars: ~/osz-stack/SIEGE.md. The pattern (a sawtooth wave table, a boss every five minutes,
quick choices of three upgrades, chests, an ending at 30:00) is borrowed from the genre; every name and
number here is ours, scaled to what one survivor with a bat can face and what this server can hold.

Everything that decides difficulty is data at the top of this file, so it can be retuned without code.
The simulation is `sim.World`, the same one survival runs: zombies grab, bite and bleed you exactly as
they do there. Upgrades act through `Actor.mods`, which is empty in survival.
"""
from __future__ import annotations

import copy
import math
import random

from app.game import difficulty
from app.game.content import ITEMS, TUNE, ZED_KINDS, ZED_VARIANTS
from app.game.sim import Actor, World, Zed, bearing_deg, dist_m, shift

# ---------------------------------------------------------------------------------------- the arena
ARENA = {"id": "daley", "label": "Daley Plaza, Chicago", "landmark": "the Picasso",
         "lat": 41.88355, "lng": -87.62985, "r": 35.0, "region": "dp3wmb"}
KEEP_BUILDINGS_M = 160.0        # only the buildings this near the arena are copied into a siege's world
SPAWN_RING_M = (44.0, 56.0)     # zombies walk in from just outside the arena
LIGHT = 0.6                     # fixed dusk: every run is the same fight, whatever the real clock says
LENGTH_S = 30 * 60
START_BANDAGES = 4
BREATHE_PER_S = 1.5             # endurance back every second even mid-fight (survival only regains it standing still)

# ---------------------------------------------------------------------------------------- the waves
# The shape, minute by minute (0 to 29): the minimum number alive in a well-known horde game's first
# stage. A sawtooth, not a ramp: it climbs, falls back to a breather, spikes. Only the shape is used.
SHAPE = [15, 30, 50, 40, 30, 10, 20, 80, 100, 30, 10, 300, 20, 150, 20, 100, 100, 20, 60, 100,
         100, 300, 200, 300, 300, 100, 150, 300, 300, 300]
# Scaled to this game and this server (tuned by bots, 2026-11-03, player/siege_tune/): floor =
# max(MIN_FLOOR, shape x SCALE x a ramp from FLOOR_RAMP[0] at 0:00 to FLOOR_RAMP[1] at 30:00).
SCALE = 0.10
MIN_FLOOR = 2
FLOOR_RAMP = (0.6, 1.4)         # and a multiplier on the floor from 0:00 to 30:00: later spikes hit harder
SPAWN_PER_S = 1.5               # how fast the floor is refilled when it is not met
HP_RAMP = (1.0, 2.5)            # zombie health multiplier from 0:00 to 30:00
SPEED_RAMP = (1.0, 2.0)         # and speed: from the classic pace to a little past the public setting's (x1.8)


def build_waves(scale=None, min_floor=None, hp_ramp=None, speed_ramp=None, floor_ramp=None):
    """The table, one row a minute: {minute, floor, hp, speed}. Kept as data; built once at import."""
    scale = SCALE if scale is None else scale
    min_floor = MIN_FLOOR if min_floor is None else min_floor
    hp_ramp, speed_ramp, floor_ramp = hp_ramp or HP_RAMP, speed_ramp or SPEED_RAMP, floor_ramp or FLOOR_RAMP
    rows = []
    for m, n in enumerate(SHAPE):
        f = m / (len(SHAPE) - 1)
        k = floor_ramp[0] + (floor_ramp[1] - floor_ramp[0]) * f
        rows.append({"minute": m, "floor": max(min_floor, round(n * scale * k)),
                     "hp": round(hp_ramp[0] + (hp_ramp[1] - hp_ramp[0]) * f, 3),
                     "speed": round(speed_ramp[0] + (speed_ramp[1] - speed_ramp[0]) * f, 3)})
    return rows


WAVES = build_waves()

# ---------------------------------------------------------------------------------------- bosses
BOSS_EVERY_S = 300
BOSS_WARN_S = 10.0
# One at 5, 10, 15, 20 and 25 minutes. Huge, slower than the rest, hits hard, can't be shoved over.
BOSSES = [
    {"at": 300, "name": "The Doorman", "hp": 110, "speed": 0.95, "dmg": 1.54},
    {"at": 600, "name": "The Foreman", "hp": 170, "speed": 1.0, "dmg": 1.82},
    {"at": 900, "name": "The Bailiff", "hp": 240, "speed": 1.05, "dmg": 2.1},
    {"at": 1200, "name": "The Alderman", "hp": 310, "speed": 1.1, "dmg": 2.38},
    {"at": 1500, "name": "The Judge", "hp": 400, "speed": 1.15, "dmg": 2.66},
]
BOSS_XP = 12

# ---------------------------------------------------------------------------------------- levels
CHOICE_TIMEOUT_S = 20.0         # the run is paused while choosing; after this the first is taken
TIME_XP_EVERY_S = 5.0           # a point of experience for staying alive this long


def xp_needed(level: int) -> int:
    """Experience from level `level` to the next. Kills give 1, a boss BOSS_XP."""
    return 4 + level              # with time alone: 20, 24, 28, 32, 36, 40 s for the first six choices


# The pool. Each is small and stacks up to `max` times. `mods` multiply or add on Actor.mods.
UPGRADES = {
    "heavy":   {"name": "Heavier swings", "text": "+15% swing damage", "max": 5, "mods": {"dmg": ("mul", 1.15)}},
    "quick":   {"name": "Quicker recovery", "text": "Swings recover 10% faster", "max": 4, "mods": {"rec": ("mul", 0.9)}},
    "arc":     {"name": "Wide arc", "text": "A swing also hits one more zombie in reach", "max": 3, "mods": {"cleave": ("add", 1)}},
    "jacket":  {"name": "Thick jacket", "text": "Take 12% less damage", "max": 4, "mods": {"armor": ("mul", 0.88)}},
    "feet":    {"name": "Fleet feet", "text": "+8% speed", "max": 3, "mods": {"speed": ("mul", 1.08)}},
    "wind":    {"name": "Second wind", "text": "Heal 35 and stop all bleeding", "max": 99, "heal": 35},
    "mend":    {"name": "Slow mend", "text": "Regain 0.4 health a second", "max": 3, "mods": {"regen": ("add", 0.4)}},
    "charge":  {"name": "Shoulder charge", "text": "Shoves knock down more and push further", "max": 3,
                "mods": {"shove_kd": ("add", 0.12), "shove_push": ("mul", 1.3)}},
    "breath":  {"name": "Deep breath", "text": "Swings cost 25% less endurance; get your breath back faster", "max": 2,
                "mods": {"endc": ("mul", 0.75), "breathe": ("add", 1.0)}},
    "weapon":  {"name": "Better weapon", "text": "Bat to crowbar to hand axe", "max": 2, "weapon": ["crowbar", "axe"]},
    "bandage": {"name": "A roll of bandages", "text": "+2 bandages", "max": 99, "give": ("bandage", 2)},
}

# ---------------------------------------------------------------------------------------- chests
CHEST_EVERY_S = 180.0
CHEST_OPEN_M = 2.2
CHEST_MAX = 2                   # arena chests waiting at once (boss chests come on top)
# One find per chest for the haul that goes home. Plain supplies; nothing for sale, ever.
HAUL = [("bandage", 1, 3), ("snack", 1, 3), ("water", 1, 2), ("nails", 1, 4), ("plank", 1, 3),
        ("knife", 1, 2), ("crowbar", 1, 1), ("disinfectant", 1, 2)]

# ---------------------------------------------------------------------------------------- score
SCORE = {"kill": 10, "second": 1, "boss": 500, "extracted": 3000}
EVAC_WARN_S = LENGTH_S - 60


def tune():
    """The siege's own dials: the classic game, with no first-day grace or arrival calm. Zombie speed is
    then ramped by the wave table, up to the public setting's by the end."""
    d = difficulty.resolve("classic")
    t = dict(difficulty.tune_for(d, TUNE))
    # Always at fighting pace: survival's three-times "exploring" pace would outrun every wave.
    # Walking a plaza isn't a long outing: survival's per-metre endurance cost left the bot at zero in a
    # minute, and a tired swing does under half damage.
    t.update(grace_h=0.0, early_s=0.0, arrival_calm_s=0.0, transit_jump_m=float("inf"), walk_speed_explore_mult=1.0,
             walk_end_per_m=TUNE["walk_end_per_m"] * 0.25, end_regen=TUNE["end_regen"] * 1.3)
    return t


def near_records(records, center=None, keep_m=KEEP_BUILDINGS_M):
    """Building records whose outline comes within keep_m of the arena."""
    c = center or (ARENA["lat"], ARENA["lng"])
    out = []
    for r in records:
        o = r.get("outline") or []
        if o and min(dist_m(c[0], c[1], p[0], p[1]) for p in o) <= keep_m:
            out.append(r)
    return out


class SiegeRun:
    """One player's thirty minutes. `step(dt)` advances it; it pauses itself while a choice is open."""

    def __init__(self, player_id: int, name: str, records, seed: int | None = None, wall: float = 0.0,
                 waves=None, bosses=None, arena=None, run_id: int = 1, spawn_per_s: float | None = None, start_t: float = 0.0):
        self.arena = dict(arena or ARENA)
        self.waves = waves or WAVES
        self.spawn_per_s = SPAWN_PER_S if spawn_per_s is None else spawn_per_s
        self.bosses = copy.deepcopy(bosses or BOSSES)
        self.rng = random.Random(seed)
        self.world = World(rng=random.Random(self.rng.random()), tune=tune(), light_fn=lambda lat, lng, now: LIGHT)
        self.world.show_others = False
        self.world.buildings.add(near_records(records, (self.arena["lat"], self.arena["lng"])))
        self.t = 0.0                                  # siege seconds; stops while a choice is open
        self.base = 1_000_000.0                       # the world's own clock = base + t
        self.world.now = self.base
        a = Actor(id=player_id, name=name, life_id=run_id, born=self.base - 1e6, placed_at=self.base - 1e6,
                  lat=self.arena["lat"], lng=self.arena["lng"], placement_epoch=1)
        a.mods = {"breathe": BREATHE_PER_S}
        bat = a.add("bat", 1, ITEMS["bat"].get("cond"))
        a.hands = bat["id"]
        a.add("bandage", START_BANDAGES)
        self.world.add_actor(a, self.base)
        self.world.set_position(a.id, a.lat, a.lng, 1.0)
        self.actor = a
        self.player_id = player_id
        self.xp = 0; self.level = 1; self.taken = {}; self.choice = None; self.choice_until = 0.0
        self.pending_levels = 0
        self.kills_seen = 0; self.bosses_killed = 0
        self.boss_next = 0; self.boss_warn = None; self.boss_id = None
        self.chests = []; self.chest_seq = 0; self.next_chest = CHEST_EVERY_S
        self.haul = []; self.events = []
        self.spawn_acc = 0.0; self.zseq = 0; self.time_xp_acc = 0.0
        self.over = None                              # {"result": "dead"|"extracted"|"left", "t", "score", ...}
        self.wall_started = wall
        if start_t:                                   # load tests only (OSZ_SIEGE_START_S): begin later in the table
            self.t = float(start_t)
            self.boss_next = sum(1 for b in self.bosses if b["at"] <= self.t)
            self.next_chest = (int(self.t // CHEST_EVERY_S) + 1) * CHEST_EVERY_S
        self.evac_told = False
        self.peak_alive = 0

    # ----------------------------------------------------------------------------- the clock
    @property
    def minute(self) -> int:
        return min(len(self.waves) - 1, int(self.t // 60))

    def alive_zeds(self):
        return [z for z in self.world.zeds.values() if z.alive]

    def score(self) -> int:
        a = self.actor
        s = SCORE["kill"] * a.kills + SCORE["second"] * int(self.t) + SCORE["boss"] * self.bosses_killed
        if self.over and self.over["result"] == "extracted":
            s += SCORE["extracted"]
        return s

    def step(self, dt: float, wall: float = 0.0):
        """Advance by dt real seconds. Returns True while the run goes on."""
        if self.over:
            return False
        if self.choice is not None:
            if wall and self.choice_until and wall >= self.choice_until:
                self.pick(0)                            # nobody chose: take the first
            return True
        dt = max(0.0, min(1.0, dt))
        self.t += dt
        w = self.world
        w.step(self.base + self.t)
        a = self.actor
        if a.dead or a.death:
            if not a.dead:
                w.step(self.base + self.t)            # let the simulation finish the death
            self._end("dead")
            return False
        if self.t >= LENGTH_S:
            self._end("extracted")
            return False
        self._hold_in_arena()
        self._spawn(dt)
        self._boss()
        self._hunt()
        self._chests()
        self._experience(dt)
        return True

    # ----------------------------------------------------------------------------- the arena
    def _hold_in_arena(self):
        a, ar = self.actor, self.arena
        d = dist_m(ar["lat"], ar["lng"], a.lat, a.lng)
        if d > ar["r"]:
            b = math.radians(bearing_deg(ar["lat"], ar["lng"], a.lat, a.lng))
            a.lat, a.lng = shift(ar["lat"], ar["lng"], math.sin(b) * ar["r"], math.cos(b) * ar["r"])
            if a.raw:
                a.raw = (a.lat, a.lng, a.raw[2])

    def clamp(self, lat, lng):
        """A move the player asked for, held inside the arena."""
        ar = self.arena
        d = dist_m(ar["lat"], ar["lng"], lat, lng)
        if d <= ar["r"]:
            return lat, lng
        b = math.radians(bearing_deg(ar["lat"], ar["lng"], lat, lng))
        return shift(ar["lat"], ar["lng"], math.sin(b) * ar["r"], math.cos(b) * ar["r"])

    def _ring_point(self, bearing: float | None = None):
        ar, w = self.arena, self.world
        for _ in range(24):
            b = math.radians(self.rng.uniform(0, 360) if bearing is None else bearing + self.rng.uniform(-20, 20))
            r = self.rng.uniform(*SPAWN_RING_M)
            p = shift(ar["lat"], ar["lng"], math.sin(b) * r, math.cos(b) * r)
            if w.buildings.containing(p) is None:
                return p
        return shift(ar["lat"], ar["lng"], 0.0, -SPAWN_RING_M[0])     # the street to the south is open

    def _free_point(self, r_max: float):
        ar, w = self.arena, self.world
        for _ in range(40):
            b = math.radians(self.rng.uniform(0, 360)); r = r_max * math.sqrt(self.rng.random())
            p = shift(ar["lat"], ar["lng"], math.sin(b) * r, math.cos(b) * r)
            if w.buildings.containing(p) is None:
                return p
        return (ar["lat"], ar["lng"])

    # ----------------------------------------------------------------------------- zombies
    def _new_zed(self, p, hp, speed, boss=None):
        self.zseq += 1
        kind = ZED_KINDS["shambler"]
        zid = f"s:{self.zseq}"
        z = Zed(id=zid, lat=p[0], lng=p[1], kind="shambler", hp=hp, hp_max=hp, speed=speed,
                variant=self.rng.randrange(ZED_VARIANTS), home=p, temp=True, spawned_at=self.world.now,
                state="chase", target=self.actor.id, last_seen=self.world.now, next_groan=self.world.now + self.rng.uniform(2, 8))
        if boss:
            z.boss = boss
        self.world.zeds[zid] = z
        self.world._wall_clearance(z)
        return z

    def _spawn(self, dt):
        row = self.waves[self.minute]
        alive = sum(1 for z in self.alive_zeds() if not getattr(z, "boss", None))
        self.peak_alive = max(self.peak_alive, alive)
        if alive >= row["floor"]:
            self.spawn_acc = 0.0
            return
        self.spawn_acc += self.spawn_per_s * dt
        kind = ZED_KINDS["shambler"]
        while self.spawn_acc >= 1.0 and alive < row["floor"]:
            self.spawn_acc -= 1.0; alive += 1
            hp = self.rng.uniform(*kind["hp"]) * row["hp"]
            speed = self.rng.uniform(*kind["speed"]) * self.world.T["zed_speed_mult"] * row["speed"]
            self._new_zed(self._ring_point(), hp, speed)

    def _hunt(self):
        """Every zombie here came for you: none of them wanders off or forgets."""
        a, now = self.actor, self.world.now
        for z in self.world.zeds.values():
            if not z.alive:
                continue
            if z.state in ("idle", "investigate"):
                z.state, z.target, z.goal, z.last_seen, z.sleep_until = "chase", a.id, None, now, 0.0
            elif z.target is None:
                z.target = a.id                         # staggered or knocked down: it gets up for you
            if z.state == "chase":
                z.last_seen = now

    def _boss(self):
        if self.boss_next >= len(self.bosses):
            return
        spec = self.bosses[self.boss_next]
        if self.boss_warn is None and self.t >= spec["at"] - BOSS_WARN_S:
            bearing = self.rng.uniform(0, 360)
            p = self._ring_point(bearing)
            self.boss_warn = {"name": spec["name"], "at": spec["at"], "lat": p[0], "lng": p[1],
                              "b": round(bearing_deg(self.arena["lat"], self.arena["lng"], p[0], p[1]))}
            self._event("boss_warn", name=spec["name"], b=self.boss_warn["b"], lat=p[0], lng=p[1], in_s=BOSS_WARN_S)
        if self.boss_warn is not None and self.t >= spec["at"]:
            p = (self.boss_warn["lat"], self.boss_warn["lng"])
            z = self._new_zed(p, spec["hp"], spec["speed"], boss={"n": self.boss_next + 1, "name": spec["name"], "dmg": spec["dmg"]})
            self.boss_id = z.id
            self._event("boss", name=spec["name"], hp=spec["hp"])
            self.boss_warn = None
            self.boss_next += 1

    # ----------------------------------------------------------------------------- chests and haul
    def _chests(self):
        a = self.actor
        if self.t >= self.next_chest:
            self.next_chest += CHEST_EVERY_S
            if sum(1 for c in self.chests if c["kind"] == "arena") < CHEST_MAX:
                self._add_chest(self._free_point(self.arena["r"] - 4.0), "arena")
        for c in list(self.chests):
            if dist_m(a.lat, a.lng, c["lat"], c["lng"]) <= CHEST_OPEN_M:
                self.chests.remove(c)
                self._open_chest(c)

    def _add_chest(self, p, kind):
        self.chest_seq += 1
        c = {"id": f"c{self.chest_seq}", "lat": p[0], "lng": p[1], "kind": kind}
        self.chests.append(c)
        self._event("chest", id=c["id"], kind=kind, lat=p[0], lng=p[1])

    def _open_chest(self, c):
        options = self._available()
        got = self.rng.choice(options) if options else None
        if got:
            self._apply(got)
        code, lo, hi = self.rng.choice(HAUL)
        qty = self.rng.randint(lo, hi)
        self.haul.append({"code": code, "qty": qty})
        self._event("chest_open", id=c["id"], upgrade=got, upgrade_name=UPGRADES[got]["name"] if got else None,
                    find=code, find_name=ITEMS[code]["name"], qty=qty)

    # ----------------------------------------------------------------------------- experience and upgrades
    def _experience(self, dt):
        a = self.actor
        new_kills = a.kills - self.kills_seen
        self.kills_seen = a.kills
        self.xp += new_kills
        if self.boss_id and self.boss_id not in self.world.zeds:
            boss_z = self.boss_id
            self.boss_id = None
            self.bosses_killed += 1
            self.xp += BOSS_XP - 1                     # its kill already counted 1
            self._add_chest(self._last_boss_point or self._free_point(10.0), "boss")
            self._event("boss_down", n=self.bosses_killed)
        if self.boss_id and self.boss_id in self.world.zeds:
            z = self.world.zeds[self.boss_id]
            self._last_boss_point = self.clamp(z.lat, z.lng)
        self.time_xp_acc += dt
        while self.time_xp_acc >= TIME_XP_EVERY_S:
            self.time_xp_acc -= TIME_XP_EVERY_S
            self.xp += 1
        while self.xp >= xp_needed(self.level):
            self.xp -= xp_needed(self.level)
            self.level += 1
            self.pending_levels += 1
        if self.pending_levels and self.choice is None:
            self._offer()

    _last_boss_point = None

    def _available(self):
        a = self.actor
        out = []
        for k, u in UPGRADES.items():
            if self.taken.get(k, 0) >= u["max"]:
                continue
            if k == "weapon" and self.taken.get(k, 0) >= len(u["weapon"]):
                continue
            out.append(k)
        return out

    def _offer(self):
        options = self._available()
        self.rng.shuffle(options)
        self.choice = options[:3]
        self.pending_levels -= 1
        self.choice_until = 0.0                        # set by whoever drives the run (wall clock)
        self._event("level", level=self.level, choice=[{"id": k, "name": UPGRADES[k]["name"], "text": UPGRADES[k]["text"]} for k in self.choice])

    def open_choice(self, wall: float):
        if self.choice is not None and not self.choice_until:
            self.choice_until = wall + CHOICE_TIMEOUT_S

    def pick(self, i):
        if self.choice is None:
            return {"ok": False, "why": "nothing to choose"}
        if not isinstance(i, int) or not 0 <= i < len(self.choice):
            return {"ok": False, "why": "choose one of the three"}
        k = self.choice[i]
        self.choice = None; self.choice_until = 0.0
        self._apply(k)
        self._event("picked", id=k, name=UPGRADES[k]["name"])
        if self.pending_levels:
            self._offer()
        return {"ok": True, "picked": k}

    def _apply(self, k):
        a, u = self.actor, UPGRADES[k]
        n = self.taken.get(k, 0)
        self.taken[k] = n + 1
        for key, (op, v) in u.get("mods", {}).items():
            base = a.mods.get(key, 1.0 if op == "mul" else 0.0)
            a.mods[key] = round(base * v if op == "mul" else base + v, 4)
        if "heal" in u:
            a.hp = min(self.world.T["hp_max"], a.hp + u["heal"])
            for wd in a.wounds:
                wd["bleeding"] = False
        if "give" in u:
            a.add(u["give"][0], u["give"][1])
        if "weapon" in u:
            code = u["weapon"][min(n, len(u["weapon"]) - 1)]
            old = a.item(a.hands)
            if old:
                a.items.remove(old)
            row = a.add(code, 1, ITEMS[code].get("cond"))
            a.hands = row["id"]
        a.dirty = True

    # ----------------------------------------------------------------------------- the end
    def _end(self, result):
        a = self.actor
        if result == "extracted":
            self._event("extracted")
        self.over = {"result": result, "t": round(min(self.t, LENGTH_S), 1), "kills": a.kills, "level": self.level,
                     "bosses": self.bosses_killed, "haul": copy.deepcopy(self.haul), "cause": (a.death or {}).get("cause")}
        self.over["score"] = self.score()

    def leave(self):
        if not self.over:
            self._end("left")

    def _event(self, e, **kw):
        ev = {"e": "siege_" + e, "t": round(self.t, 1), **kw}
        self.events.append(ev)
        self.actor.events.append(ev)
        self.events = self.events[-200:]

    # ----------------------------------------------------------------------------- what the player sees
    def info(self) -> dict:
        boss = self.world.zeds.get(self.boss_id) if self.boss_id else None
        nb = self.bosses[self.boss_next]["at"] if self.boss_next < len(self.bosses) else None
        return {
            "arena": {k: self.arena[k] for k in ("id", "label", "landmark", "lat", "lng", "r")},
            "t": round(self.t, 1), "length": LENGTH_S, "minute": self.minute, "score": self.score(),
            "level": self.level, "xp": self.xp, "xp_next": xp_needed(self.level), "kills": self.actor.kills,
            "alive": sum(1 for z in self.world.zeds.values() if z.alive), "floor": self.waves[self.minute]["floor"],
            "boss_in": round(nb - self.t, 1) if nb is not None else None,
            "boss_warn": self.boss_warn,
            "boss": {"id": boss.id, "name": boss.boss["name"], "hp": round(max(0.0, boss.hp)), "hp_max": round(boss.hp_max)} if boss else None,
            "choice": [{"id": k, "name": UPGRADES[k]["name"], "text": UPGRADES[k]["text"]} for k in self.choice] if self.choice else None,
            "choice_left": round(max(0.0, self.choice_until - self._wall), 1) if self.choice and self.choice_until else None,
            "chests": [[c["id"], round(c["lat"], 7), round(c["lng"], 7), c["kind"]] for c in self.chests],
            "taken": dict(self.taken), "haul": copy.deepcopy(self.haul),
            "evac_in": round(LENGTH_S - self.t, 1) if self.t >= EVAC_WARN_S else None,
            "over": self.over,
        }

    _wall = 0.0
