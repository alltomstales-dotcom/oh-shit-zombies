"""The pacing director. The fixed world decides where zombies are; the director decides when a
walk has been quiet for too long and nudges it. It never places anything inside your sight.
A session always opens with something shuffling in from the edge of the fog within seconds:
most streets are empty, and an empty first minute reads as a game with no zombies in it.

`policy(actor, summary) -> beat name` is pluggable: the default is weighted chance; a model can
be dropped in later (see tools/jev_policy.py). Beats:
  quiet      nothing
  straggler  one zombie that has already picked up your trail, somewhere behind you
  ahead      a small group drifting across the way you are heading
  noise      a crash or an alarm off to one side: it pulls what is already out there
  hunt       (escalate mode only) a small pack that is already on your trail, from behind

Two modes, chosen by the difficulty profile (app/game/difficulty.py):
  ease       the original. Beats every 45 to 100 s, and it goes quiet when you are hurt or bleeding.
  escalate   a gentle first minute (only the opening shamblers), then pressure climbs with time in
             the session: shorter lulls, bigger groups, fewer quiet beats, and from half pressure a
             pack that is already hunting you. Being hurt does not buy a rest. A death or a
             reconnect starts the session, and the gentle minute, again.
"""
from __future__ import annotations

import math

from app.game.content import ZED_KINDS, ZED_VARIANTS
from app.game.sim import Actor, World, Zed, shift

BEATS = ("quiet", "straggler", "ahead", "noise", "hunt")
NOISES = ("glass", "alarm", "crash", "dog")


def default_policy(rng, actor: Actor, s: dict) -> str:
    w = {"quiet": 25, "straggler": 30, "ahead": 30, "noise": 15}
    if s["hp"] < 50 or s["bleeding"]:
        w["quiet"] += 40
        w["ahead"] -= 20
    if s["night"]:
        w["straggler"] += 10
    total = sum(max(0, v) for v in w.values())
    r = rng.random() * total
    for k, v in w.items():
        r -= max(0, v)
        if r <= 0:
            return k
    return "quiet"


def escalate_policy(rng, actor: Actor, s: dict) -> str:
    """Weighted chance that leans harder as `pressure` (0..1) rises. Hurt changes nothing."""
    p = s.get("pressure", 0.0)
    w = {"quiet": 25 - 20 * p, "straggler": 30, "ahead": 30, "noise": 15 - 5 * p,
         "hunt": 30 * max(0.0, p - 0.5) * 2}
    if s["night"]:
        w["straggler"] += 10
    total = sum(max(0, v) for v in w.values())
    r = rng.random() * total
    for k, v in w.items():
        r -= max(0, v)
        if r <= 0:
            return k
    return "quiet"


def _lerp(a, b, t):
    return a + (b - a) * t


class Director:
    def __init__(self, world: World, policy=None, lull_s=(45.0, 100.0), check_s=5.0,
                 opening_s=(5.0, 9.0), config: dict | None = None):
        self.w = world
        self.opening_s = opening_s
        self.cfg = dict(config or {"mode": "ease", "lull_s": lull_s})
        self.mode = self.cfg.get("mode", "ease")
        if self.mode == "ease" and config is not None:
            lull_s = tuple(self.cfg.get("lull_s", lull_s))
        self.policy = policy or (escalate_policy if self.mode == "escalate" else default_policy)
        self.lull_s = lull_s
        self.check_s = check_s
        self.st: dict[int, dict] = {}
        self.log: list[dict] = []
        self._seq = 0

    def summary(self, a: Actor) -> dict:
        w = self.w
        return {"hp": a.hp, "end": a.end, "panic": a.panic,
                "bleeding": any(x["bleeding"] for x in a.wounds),
                "calm_s": w.now - a.last_threat, "night": w.light_fn(a.lat, a.lng, w.now) < 0.4,
                "kills": a.kills, "armed": a.weapon() is not None,
                "bandages": a.count("bandage")}

    def pressure(self, a: Actor, s: dict) -> float:
        """0 for the gentle first minute of a session, rising to 1 over the ramp. Always 0 in ease mode."""
        if self.mode != "escalate":
            return 0.0
        c = self.cfg
        return max(0.0, min(1.0, (self.w.now - s["since"] - c["gentle_s"]) / max(1.0, c["ramp_s"])))

    def _lull(self, a: Actor, s: dict) -> float:
        if self.mode != "escalate":
            return self.w.rng.uniform(*self.lull_s)
        p, c = self.pressure(a, s), self.cfg
        lo = _lerp(c["lull_start_s"][0], c["lull_end_s"][0], p)
        hi = _lerp(c["lull_start_s"][1], c["lull_end_s"][1], p)
        return self.w.rng.uniform(lo, hi)

    def tick(self):
        w, now = self.w, self.w.now
        for a in list(w.actors.values()):
            if a.floor_level or a.dead or not a.connected or a.transit_until > now or (a.lat == 0.0 and a.lng == 0.0):
                continue
            s = self.st.get(a.id)
            if s is None:
                s = self.st[a.id] = {"next": now + self.check_s, "walked": a.walked_m, "since": now}
                s["lull"] = self._lull(a, s)                  # drawn before the opening, as it always was
                s.update(last=now, open_at=(now + w.rng.uniform(*self.opening_s) if self.opening_s else None))
            if s["open_at"] is not None:
                if now < s["open_at"]:
                    continue
                s["open_at"] = None
                if not self._company(a) and not self._crowded():   # already something to look at: no need
                    s.update(last=now, walked=a.walked_m)
                    self.log.append({"t": now, "actor": a.id, "beat": "opening"})
                    self._opening(a)
                continue
            if now < s["next"]:
                continue
            s["next"] = now + self.check_s
            calm = now - max(a.last_threat, s["last"])
            moved = a.walked_m - s["walked"]
            # walking earns the next beat; standing still only delays it by a minute
            if a.channel or calm < s["lull"] or (moved < 25.0 and calm < s["lull"] + 60.0):
                continue
            if self.mode == "escalate" and now - s["since"] < self.cfg["gentle_s"]:
                continue                                   # the gentle first minute
            summary = self.summary(a)
            p = summary["pressure"] = self.pressure(a, s)
            beat = self.policy(w.rng, a, summary)
            if beat not in BEATS or (beat == "hunt" and self.mode != "escalate"):
                beat = "quiet"
            if beat in ("straggler", "ahead", "hunt") and self._crowded():
                beat = "quiet"                             # the server's budget for sent zombies is spent
            s.update(last=now, walked=a.walked_m)
            s["lull"] = self._lull(a, s)
            self.log.append({"t": now, "actor": a.id, "beat": beat, "pressure": round(p, 2)})
            if len(self.log) > 2000:
                del self.log[:1000]
            getattr(self, f"_{beat}")(a, p)

    def _crowded(self) -> bool:
        """Sent zombies are capped at temp_max_base + temp_max_per_player per survivor on the map.
        A lone survivor never reaches it; a crowd that keeps dying at one start city did, without limit."""
        T = self.w.T
        players = sum(1 for a in self.w.actors.values() if not a.dead and a.connected)
        sent = sum(1 for z in self.w.zeds.values() if z.temp and z.alive)
        return sent >= T.get("temp_max_base", 60) + T.get("temp_max_per_player", 3) * players

    def forget(self, actor_id: int):
        self.st.pop(actor_id, None)

    # ---------------------------------------------------------------- beats
    def _spawn(self, a: Actor, bearing: float, dist: float, kind: str, chase: bool) -> Zed | None:
        w, rng = self.w, self.w.rng
        rad = math.radians(bearing)
        lat, lng = shift(a.lat, a.lng, math.sin(rad) * dist, math.cos(rad) * dist)
        point = w.spawn_point(lat, lng, observer=a)
        if point is None:return None
        lat, lng = point
        spec = ZED_KINDS[kind]
        self._seq += 1
        hp = float(rng.randint(*spec["hp"]))
        z = Zed(id=f"t:{self._seq}", lat=lat, lng=lng, kind=kind, hp=hp, hp_max=hp,
                speed=rng.uniform(*spec["speed"]) * w.T.get("zed_speed_mult", 1.0), variant=rng.randrange(ZED_VARIANTS),
                home=(lat, lng), temp=True, next_groan=w.now + rng.uniform(2, 6), spawned_at=w.now)
        if chase:
            z.state, z.target, z.last_seen = "chase", a.id, w.now
        from app.geo import cell_of
        z.spawn_unmapped = hasattr(w,"resource_regions") and cell_of(lat,lng,6) not in w.resource_regions
        w.zeds[z.id] = z
        return z

    def _company(self, a: Actor) -> bool:
        """Is there already a zombie the survivor can see or is being hunted by?"""
        from app.game.sim import dist_m
        sight = self.w.sight_m(a)
        return any(z.alive and (z.target == a.id or dist_m(a.lat, a.lng, z.lat, z.lng) <= sight)
                   for z in self.w.zeds.values())

    def _opening(self, a: Actor):
        """Two or three shamblers just past the fog, wandering in. Heard first, then seen."""
        rng = self.w.rng
        base = rng.uniform(0, 360)
        dist = self.w.sight_m(a) + 3.0
        for _ in range(rng.choice([2, 2, 3])):
            z = self._spawn(a, base + rng.uniform(-10, 10), dist + rng.uniform(0, 6), "shambler", chase=False)
            if z is None:continue
            z.state, z.goal = "investigate", (a.lat, a.lng)
            z.next_groan = self.w.now + rng.uniform(0.5, 3.0)

    def _grow(self, p: float) -> int:
        return int(round(self.cfg.get("group_grow", 0) * p)) if self.mode == "escalate" else 0

    def _quiet(self, a: Actor, p: float = 0.0):
        pass

    def _straggler(self, a: Actor, p: float = 0.0):
        rng = self.w.rng
        for i in range(1 + self._grow(p) // 2):
            dist = max(self.w.sight_m(a) + 6.0, rng.uniform(30, 42)) + 4.0 * i
            kind = "lurcher" if rng.random() < 0.3 else "shambler"
            self._spawn(a, (a.heading + 180 + rng.uniform(-35, 35)) % 360, dist, kind, chase=True)

    def _hunt(self, a: Actor, p: float = 0.0):
        """A small pack that has your scent, coming from behind and to one side. Escalate mode only."""
        rng = self.w.rng
        dist = max(self.w.sight_m(a) + 6.0, rng.uniform(28, 38))
        base = (a.heading + 180 + rng.choice([-1, 1]) * rng.uniform(20, 60)) % 360
        lo, hi = self.cfg.get("hunt_size", (3, 5))
        for _ in range(rng.randint(lo, hi)):
            kind = "lurcher" if rng.random() < 0.35 else "shambler"
            self._spawn(a, base + rng.uniform(-10, 10), dist + rng.uniform(-3, 5), kind, chase=True)

    def _ahead(self, a: Actor, p: float = 0.0):
        rng = self.w.rng
        dist = max(self.w.sight_m(a) + 8.0, rng.uniform(45, 60))
        base = (a.heading + rng.uniform(-25, 25)) % 360
        for _ in range(rng.choice([2, 2, 3, 3, 4]) + self._grow(p)):
            z = self._spawn(a, base + rng.uniform(-8, 8), dist + rng.uniform(-5, 5), "shambler", chase=False)
            if z is None:continue
            z.state, z.goal = "investigate", (a.lat, a.lng)   # drifting your way, not yet on to you

    def _noise(self, a: Actor, p: float = 0.0):
        rng = self.w.rng
        side = rng.choice([-1, 1]) * rng.uniform(50, 100)
        rad = math.radians((a.heading + side) % 360)
        dist = rng.uniform(50, 75)
        lat, lng = shift(a.lat, a.lng, math.sin(rad) * dist, math.cos(rad) * dist)
        self.w.noise(lat, lng, 60.0)
        a.events.append({"e": "noise", "kind": rng.choice(NOISES),
                         "b": round((a.heading + side) % 360), "d": round(dist)})
