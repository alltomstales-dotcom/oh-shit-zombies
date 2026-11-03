"""The simulation: zombies, survivors, pursuit and fights. Pure Python, no I/O.

Time is whatever the caller passes to `step(now)`: the wall clock on the server, a fake clock in
tests and in the bot harness (which is how thousands of walks get simulated in seconds).

One World holds every zombie near any connected survivor. Zombies are shared: a kill is a kill
for everybody. Everything the survivor's body does (health, endurance, panic, wounds) lives on
the Actor.
"""
from __future__ import annotations

import math
import time
import zlib
import copy
import random
from dataclasses import dataclass, field

from app.game.content import BODY_PARTS, FISTS, ITEMS, TUNE, ZED_KINDS, STASH_LOOT
from app.game.buildings import Buildings, point_segment
from app.game.progression import award, skill_level, view as progression_view
from app.geo import cell_of
from app.game import equipment, home, survival
from app.game import loot as loot_system
from app.game import corpses as corpse_system
from app.game import memory
from app.game import study
from app.game import weather
from app.game import herds
from app.game import backgrounds,bases,vehicles,broadcasts

M_PER_DEG = 111_320.0


DROP_KEEP_S = 15 * 60      # a dropped weapon lies where it fell this long
DROP_VIEW_LIMIT = 24


def _mlng(lat: float) -> float:
    return M_PER_DEG * max(0.01, math.cos(math.radians(lat)))


def delta_m(lat1, lng1, lat2, lng2) -> tuple[float, float]:
    """East and north metres from point 1 to point 2 (flat-earth; fine at street scale)."""
    return (lng2 - lng1) * _mlng(lat1), (lat2 - lat1) * M_PER_DEG


def dist_m(lat1, lng1, lat2, lng2) -> float:
    dx, dy = delta_m(lat1, lng1, lat2, lng2)
    return math.hypot(dx, dy)


def shift(lat, lng, dx, dy) -> tuple[float, float]:
    return lat + dy / M_PER_DEG, lng + dx / _mlng(lat)


def bearing_deg(lat1, lng1, lat2, lng2) -> float:
    """Compass bearing from 1 to 2: 0 north, 90 east."""
    dx, dy = delta_m(lat1, lng1, lat2, lng2)
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


def _pick(rng, pairs):
    total = sum(w for _, w in pairs)
    r = rng.random() * total
    for item, w in pairs:
        r -= w
        if r <= 0:
            return item
    return pairs[-1][0]


@dataclass
class Zed:
    id: str
    lat: float
    lng: float
    kind: str = "shambler"
    hp: float = 26.0
    hp_max: float = 26.0
    speed: float = 0.85
    variant: int = 0
    spawn_unmapped: bool = False
    home: tuple = (0.0, 0.0)
    state: str = "idle"          # idle|investigate|alert|chase|engaged|stagger|down|rising|dead
    target: int | None = None    # actor id
    t_state: float = 0.0         # when the current timed state ends
    attack_at: float = 0.0
    last_seen: float = 0.0       # last time it perceived its target
    spawned_at: float = 0.0      # when the director sent it (0 for the fixed world)
    goal: tuple | None = None    # where it is walking when wandering or investigating
    next_groan: float = 0.0
    sleep_until: float = 0.0     # far from everyone: skip it until then
    temp: bool = False           # placed by the director, not part of the fixed world
    night: bool = False
    boss: dict | None = None     # siege only: {"n", "name", "dmg"}. Never set in survival.
    wander_dt: float = 0.0       # idle shuffling is stepped in chunks (TUNE wander_step_s)
    stuck: int = 0               # wandering steps in a row without headway

    @property
    def alive(self) -> bool:
        return self.state != "dead"


@dataclass
class Actor:
    id: int
    name: str = "Survivor"
    life_id: int = 0
    remains: dict | None = None  # immutable initial death stock, never used to refill a pack
    background: dict | None = None
    lat: float = 0.0
    lng: float = 0.0
    raw: tuple | None = None     # last reported position (lat, lng, accuracy)
    position_mode: str = "desk"  # GPS follows the real fix; desk movement follows physical capacity
    hp: float = 100.0
    end: float = 100.0
    panic: float = 0.0
    wounds: list = field(default_factory=list)
    items: list = field(default_factory=list)     # [{"id", "code", "qty", "cond"}]
    hunger: float = 0.0
    thirst: float = 0.0
    sleep: float = 0.0
    lantern: bool = False
    worn: dict = field(default_factory=dict)
    home: dict | None = None  # PlayerHome, deliberately separate from this life
    home_owner: int = 0  # runtime binding; durable active base is BaseSelection
    base_role: str = 'owner'
    base_members: list = field(default_factory=list)
    base_choices: list = field(default_factory=list)
    pending_learning: bool = False
    pending_work: dict | None = None
    vehicle_id: str | None = None  # seats release on cold restart, GPS launch and death
    study: dict | None = None  # the manual being read: {"skill","code","need_s","done_s","since","at"}
    knowledge: list = field(default_factory=list)
    learned_media: list = field(default_factory=list)
    studied: list = field(default_factory=list)   # skills that gain double for this life
    hands: int | None = None                      # item id of the weapon held
    busy_until: float = 0.0
    channel: dict | None = None                   # {"kind", "ends", ...}
    back_ready_at: float = 0.0
    last_action: float = -99.0
    scream_ready_at: float = 0.0
    panic_scream_ready_at: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    born: float = 0.0
    placed_at: float = 0.0
    placement_epoch: int = 0
    floor_level: int = 0
    floor_building: str | None = None
    floor_epoch: int = 0
    location_loading_until: float = 0.0
    gps_anchor: list | None = None
    infected_at: float | None = None
    turns_at: float | None = None
    transit_until: float = 0.0
    connected: bool = True
    dead: bool = False
    death: dict | None = None
    kills: int = 0
    walked_m: float = 0.0
    xp: int = 0
    skill_xp: dict = field(default_factory=dict)
    training_m: float = 0.0
    explored: list = field(default_factory=list)
    building_searches: dict = field(default_factory=dict)  # per-life attempts and discovered caches
    claimed: set = field(default_factory=set)     # stash ids this survivor has searched
    loot_shelves: dict = field(default_factory=dict)
    loot_receipts: list = field(default_factory=list)
    pending_search: dict | None = None  # Hub commits a completed reveal before publishing it
    pending_body_search: str | None = None
    pending_window: dict | None = None
    window_until: float = 0.
    events: list = field(default_factory=list)
    dirty: bool = False
    _next_item_id: int = 1
    _next_wound_id: int = 1
    sprinting: bool = False
    quiet: bool = False                           # creeping: slow, hard to hear, harder to spot
    last_threat: float = -999.0                   # last time something was chasing or on it
    mods: dict = field(default_factory=dict)      # siege upgrades only (siege.py); always empty in survival

    # -- inventory helpers ---------------------------------------------------------------
    def item(self, item_id):
        return next((i for i in self.items if i["id"] == item_id), None)

    def count(self, code) -> int:
        return sum(i["qty"] for i in self.items if i["code"] == code and (not ITEMS[code].get("perishable") or i.get("cond",100)>0))

    def add(self, code, qty=1, cond=None) -> dict:
        spec = ITEMS[code]
        if "stack" in spec:
            row = next((i for i in self.items if i["code"] == code and i.get("cond")== (cond if cond is not None else spec.get("cond"))), None)
            if row:
                row["qty"] += qty
                self.dirty = True
                return row
        row = {"id": self._next_item_id, "code": code, "qty": qty,
               "cond": cond if cond is not None else spec.get("cond")}
        self._next_item_id += 1
        self.items.append(row)
        self.dirty = True
        return row

    def take(self, code, qty=1) -> bool:
        if qty <= 0 or self.count(code) < qty:
            return False
        remaining = qty
        for row in list(self.items):
            if row['code'] != code or ITEMS[code].get('perishable') and row.get('cond',100)<=0:
                continue
            used=min(remaining,row['qty']);row['qty']-=used;remaining-=used
            if row['qty']<=0:self.items.remove(row)
            if not remaining:break
        self.dirty = True
        return True

    def weight(self) -> float:
        return sum(ITEMS[i["code"]]["w"] * i["qty"] for i in self.items)

    def weapon(self) -> dict | None:
        row = self.item(self.hands) if self.hands is not None else None
        return row if row and ITEMS[row["code"]]["kind"] in ("weapon", "gun") else None


class World:
    def __init__(self, rng: random.Random | None = None, tune: dict | None = None,
                 light_fn=None, spawner=None):
        self.T = dict(TUNE, **(tune or {}))
        self.rng = rng or random.Random()
        self.light_fn = light_fn or (lambda lat, lng, now: 1.0)
        self.spawner = spawner          # object with zeds(cell, now) / stashes(cell, now) / cells_near(lat, lng)
        self.zeds: dict[str, Zed] = {}
        self.actors: dict[int, Actor] = {}
        self.buildings = Buildings()
        self._level_root = None
        self._level_key = None
        self.levels = {}
        self.level_states = {}
        self.upper_corpses = {}
        self.homes: dict[int,dict] = {}
        self.home_dirty = set()
        self.broadcast_fired=set();self.vehicles={};self.vehicle_dirty=set();self.vehicle_controls={}
        self.memories: dict[int, dict] = {}    # per player, across lives: see memory.py
        self.memory_dirty: set[int] = set()
        self.memory_state: dict[int, dict] = {}
        self.heli_seen: dict[int, tuple] = {}     # survivor -> (pass id, phase) last announced
        self.heli_pulse: dict[int, float] = {}
        self.herds: dict[str, herds.Herd] = {}   # each a single walking thing: see herds.py
        self.herd_spent: dict[str, float] = {}    # herd id -> until when the schedule must not bring it back
        self.herd_woken: dict[str, dict] = {}     # herds that are zombies for now
        self.herd_told: set[tuple] = set()        # (survivor, herd, heard|seen) already said
        self.herd_seq = 0
        self._geometry_seen = -1
        self.stashes: dict[str, dict] = {}
        self.drops: dict[str, dict] = {}
        self.corpses: dict[str, dict] = {}
        self.corpse_dirty = set()
        self.corpse_ready = set()
        self.dead_until: dict[str, float] = {}     # zombie id -> time it may exist again
        self.new_dead: list[tuple[str, float]] = []  # for the store to persist
        self.loaded: dict[str, tuple] = {}         # cell -> (bucket, night)
        self.now = 0.0
        self._drop_seq = 1

    # ------------------------------------------------------------------ survivors
    def add_actor(self, actor: Actor, now: float) -> Actor:
        self.now = max(self.now, now)
        self.actors[actor.id] = actor
        if actor.lat!=0 or actor.lng!=0:self.for_actor(actor)._wall_clearance(actor)
        return actor

    def remove_actor(self, actor_id: int):
        self.heli_seen.pop(actor_id, None)
        self.heli_pulse.pop(actor_id, None)
        self.herd_told = {k for k in self.herd_told if k[0] != actor_id}
        a = self.actors.pop(actor_id, None)
        if a is None:
            return
        for z in self.zeds.values():
            if z.target == actor_id and z.alive:
                z.target, z.state, z.goal = None, "idle", None

    def for_actor(self,actor):
        from app.game import floors
        a=self.actors.get(actor) if isinstance(actor,int) else actor
        return floors.layer(self,a) if a is not None else self

    def set_position(self, actor_id: int, lat: float, lng: float, acc: float = 10.0, mode: str = "desk"):
        a = self.actors.get(actor_id)
        if a is None:
            return
        if a.vehicle_id:return
        if a.floor_level and not self.for_actor(a).buildings.clear((a.lat,a.lng),(lat,lng)):
            return
        first = a.raw is None
        a.raw = (lat, lng, acc)
        a.position_mode = "gps" if mode == "gps" else "desk"
        if first and a.lat == 0.0 and a.lng == 0.0:
            a.lat, a.lng = lat, lng
            self._wall_clearance(a)

    def climb_out(self, a: Actor, checked: bool = False) -> bool:
        """Last resort for a building with no walkable exit: put the survivor on the nearest open ground.

        A few outlines are walled in by their neighbours on every side. Without this, a survivor
        whose real position starts them inside one could never leave. `checked` means the caller
        has already found that no exit can be planned.
        """
        start = (a.lat, a.lng)
        if self.buildings.containing(start) is None:
            return False
        if not checked:
            blocked = {oid for h in self.homes.values() for oid, d in h.get("defenses", {}).items() if d.get("hp", 0) > 0}
            if self.buildings.exit_plan(start, blocked)["ok"]:
                return False
        for radius in range(3, 151, 2):
            for i in range(24):
                angle = i * math.tau / 24
                p = shift(*start, math.cos(angle) * radius, math.sin(angle) * radius)
                if self.buildings.containing(p) is None and self.buildings.clear(p, p, 1.0):
                    a.lat, a.lng = p
                    a.raw = (p[0], p[1], 1)
                    a.speed = 0.0
                    a.dirty = True
                    return True
        return False

    def early(self, a: Actor) -> bool:
        """Inside the difficulty's gentle first moments after being placed (off unless early_s is set)."""
        since = a.placed_at or a.born
        return self.T["early_s"] > 0 and since > 0 and self.now - since < self.T["early_s"]

    def arriving(self, a: Actor) -> bool:
        """Just appeared and still standing about: nothing has noticed this survivor yet."""
        T = self.T
        since = a.placed_at or a.born
        return since > 0 and self.now - since < T["arrival_calm_s"] and a.walked_m < T["arrival_calm_m"] and a.kills == 0

    def protected_home(self, point):
        b = self.buildings.containing(point)
        if b is None or not any(h.get('building') == b.id for h in self.homes.values()):
            return False
        outside = [o for o in b.openings if o['label'] != 'Room door']
        return all(
            (not o['open'] and not o['broken']) or any(
                h.get('defenses', {}).get(o['id'], {}).get('hp', 0) > 0
                for h in self.homes.values()) for o in outside)

    def spawn_point(self, lat, lng, observer=None):
        """Choose a bounded spawn outside sealed homes and walls, retaining fog distance."""
        start = (lat, lng)
        def allowed(p):
            return (not self.protected_home(p) and self.buildings.clear(p, p) and
                    (observer is None or dist_m(*p, observer.lat, observer.lng) >= self.sight_m(observer)))
        if allowed(start):
            return start
        for radius in (2, 4, 8, 12, 20, 30, 45):
            for i in range(24):
                p = shift(*start, math.cos(i * math.tau / 24) * radius,
                          math.sin(i * math.tau / 24) * radius)
                if allowed(p):
                    return p
        return None

    def protect_unmapped_spawns(self, region):
        """Resolve automatic spawns made before this region's footprints arrived."""
        for zid, z in list(self.zeds.items()):
            if not z.spawn_unmapped or cell_of(z.lat, z.lng, 6) != region:
                continue
            z.spawn_unmapped = False
            if not self.protected_home((z.lat, z.lng)):
                continue
            observer = self.actors.get(z.target) if z.temp else None
            point = self.spawn_point(z.lat, z.lng, observer)
            if point is None:
                del self.zeds[zid]
            else:
                z.lat, z.lng = point
                z.home = point

    def buildings_gone(self, ids, region=None):
        """A map refresh took these buildings away: what existed only inside them goes too."""
        ids = set(ids)
        for sid in [sid for sid, s in self.stashes.items() if s.get('building') in ids]:
            del self.stashes[sid]
        for a in self.actors.values():
            for bid in ids:
                a.building_searches.pop(bid, None)
            if region and not a.dead and cell_of(a.lat, a.lng, 6) == region:
                self._ev(a, 'map', message='The real map of these streets has arrived. Buildings have changed.')

    def add_herd(self, point, count: int, heading: float = 0.0, seed: int = 1, until: float | None = None):
        return herds.add(self, point, count, heading, seed, until)

    def sight_m(self, a: Actor) -> float:
        light = self.light_fn(a.lat, a.lng, self.now)
        return self.T["sight_night_m"] + (self.T["sight_day_m"] - self.T["sight_night_m"]) * light + (18 if a.lantern else 0)

    def _ev(self, a: Actor, kind: str, **kw):
        a.events.append({"e": kind, **kw})

    # ------------------------------------------------------------------ the clock
    def step(self,now:float):
        if self._level_root is not None:return self._step_level(now)
        vehicles.step(self,max(0.,min(1.,now-self.now)) if self.now else 0.,now)
        all_actors=self.actors
        try:
            self.actors={pid:a for pid,a in all_actors.items() if not a.floor_level}
            self._step_level(now)
        finally:self.actors=all_actors
        active={}
        for a in all_actors.values():
            if a.floor_level:
                level=self.for_actor(a)
                if level is not self:active[level._level_key]=level
        for level in active.values():level.step(now)

    def _step_level(self, now: float):
        dt = max(0.0, min(1.0, now - self.now)) if self.now else 0.0
        self.now = now
        # The operator's stats line can ask for the step split by part (hub sets `step_parts`).
        parts = getattr(self, "step_parts", None)
        if parts is not None:
            pc = time.perf_counter; t = [pc()]
            def lap(name):
                t2 = pc(); parts[name] = parts.get(name, 0.0) + t2 - t[0]; t[0] = t2
        else:
            def lap(name):
                pass
        for cid,b in list(self.corpses.items()):
            if b['until'] <= now:
                del self.corpses[cid];self.corpse_dirty.discard(cid);self.corpse_ready.discard(cid)
        if self.drops and now >= getattr(self, "_drops_checked", 0.0):
            # A weapon knocked out of someone's hands lies there a while, then someone else has had it.
            # Nothing removed them before, and the soak left one every 15 s at a busy start city.
            self._drops_checked = now + 5.0
            for did, d in list(self.drops.items()):
                if now - d.get("t", now) > DROP_KEEP_S:
                    del self.drops[did]
        for a in self.actors.values():
            if a.home is not None:self.homes[a.home_owner or a.id]=a.home
        survival.sync_geometry(self)
        if self._geometry_seen != self.buildings.revision:
            self._geometry_seen=self.buildings.revision
            for body in list(self.actors.values())+list(self.zeds.values()):self._wall_clearance(body)
        lap("step:upkeep")
        for a in list(self.actors.values()):
            if not a.dead:
                self._step_actor(a, dt)
        lap("step:survivors")
        if self.spawner is not None:
            self._load_cells()
        lap("step:cells")
        self._building_loot()
        lap("step:loot")
        herds.step(self, dt)
        lap("step:herds")
        if dt > 0:
            self._step_zeds(dt)
        lap("step:zombies")
        for a in self.actors.values():
            if not a.dead and a.hp <= 0:
                self._die(a, a.death or {"cause": "bled out"})

    def _wall_clearance(self,body):
        start=(body.lat,body.lng)
        if self.buildings.clear(start,start):return
        for radius in (.5,1,1.5,2,3,5,8):
            for i in range(16):
                angle=i*math.tau/16
                p=shift(*start,math.cos(angle)*radius,math.sin(angle)*radius)
                if self.buildings.clear(p,p):
                    body.lat,body.lng=p
                    if isinstance(body,Actor):body.raw=(*p,1);body.dirty=True
                    return

    def visible(self, a, b):
        return self.buildings.clear(a, b, radius=0, vision=True)

    def nearby_buildings(self, a, radius=180):
        return self.buildings.near((a.lat,a.lng),radius)

    @staticmethod
    def _supply_kind(building, room):
        text=(building.name+' '+building.type).lower()
        room_name=room['name'].lower()
        if any(word in text for word in ('hospital','clinic','pharmacy','medical')):return 'medical'
        if 'fire' in text:return 'fire_station'
        if 'police' in text:return 'police_station'
        if room_name in ('kitchen','bathroom','bedroom','garage'):return room_name
        if 'garage' in text or building.type=='shed':return 'garage'
        if any(word in text for word in ('hardware','workshop','warehouse','industrial')):return 'toolbox'
        if any(word in text for word in ('supermarket','grocery','food')):return 'kitchen'
        if building.type in ('house','residential','apartments','cabin','detached'):return 'kitchen'
        return 'medical' if room['name']=='Treatment room' else 'toolbox' if room['name'] in ('Storage','Stockroom') else 'bag' if room['name']=='Shop floor' else 'chest'

    def _building_loot(self):
        from app.rng import seeded
        for a in self.actors.values():
            if a.dead:continue
            for b in self.nearby_buildings(a):
                for i,r in enumerate(b.rooms):
                    sid='room:'+r['id']
                    if sid in self.stashes:continue
                    rng=seeded(sid)
                    kind=self._supply_kind(b,r)
                    table=STASH_LOOT[kind]
                    loot=[]
                    for _ in range(2):
                        code=_pick(rng,[(c,w) for c,w,_q in table])
                        lo,hi=next(q for c,_w,q in table if c==code)
                        loot.append((code,rng.randint(lo,hi)))
                    lat,lng=b.ll(r['pos'])
                    self.stashes[sid]={'id':sid,'lat':lat,'lng':lng,'kind':kind,'loot':loot,
                                       'building':b.id,'room':r['name'],'floor_level':a.floor_level}
            for bid,record in list(a.building_searches.items()):
                # a placeholder shelter that gave way to the real map while this survivor was away
                if bid.startswith('generated:') and bid not in self.buildings.items and bid[10:16] in getattr(self,'resource_regions',()):
                    del a.building_searches[bid];continue
                for cache in record.get('caches',[]):
                    if cache.get('floor_level',0)==a.floor_level:self.stashes.setdefault(cache['id'],dict(cache,owner=a.id))
        # Random outdoor spawn points must not put a car or bag through a wall.
        stamp=self.buildings.stamp()
        if getattr(self,'_stash_stamp',None)!=stamp:self._stash_stamp=stamp;self._stash_outdoors=set()
        for s in self.stashes.values():
            # Once a bag or car is known to stand in the open it stays there until the map changes.
            if s.get('building') or s['id'] in self._stash_outdoors:continue
            self._stash_outdoors.add(s['id'])
            b=self.buildings.containing((s['lat'],s['lng']))
            if b:
                for r in b.rooms:
                    lat,lng=b.ll(r['pos'])
                    s.update(lat=lat,lng=lng,building=b.id,room=r['name'])
                    if s['kind']=='car':s['kind']='chest'
                    break

    def _stash_seen(self,a,s,inside):
        """Is a shelf in the room in view? The client asks this only of shelves in the building the
        survivor stands in: one in another building is never drawn, and one outdoors is drawn by
        distance alone. A sight line to every shelf within 180 m was most of the cost of a view."""
        if not s.get('building'):return None
        if inside is None or s['building']!=inside.id:return False
        return self.visible((a.lat,a.lng),(s['lat'],s['lng']))

    def _stash_accessible(self,a,s):
        if s.get('floor_level',0)!=a.floor_level:return False
        if s.get('owner',a.id)!=a.id:return False
        reach=2.5 if s.get('building') else self.T['stash_reach_m']
        return dist_m(a.lat,a.lng,s['lat'],s['lng'])<=reach and self.buildings.clear((a.lat,a.lng),(s['lat'],s['lng']))

    def _do_sprint(self,a,op="start",**_):
        if op not in ("start","stop"):return {"ok":False,"why":"unknown sprint action"}
        if op=="start" and a.end<self.T["sprint_start_end"]:
            return {"ok":False,"why":"recover some stamina first"}
        a.sprinting=op=="start"
        if a.sprinting:a.quiet=False
        return {"ok":True,"sprinting":a.sprinting}

    def _do_quiet(self,a,op="start",**_):
        if op not in ("start","stop"):return {"ok":False,"why":"unknown quiet action"}
        a.quiet=op=="start"
        if a.quiet:a.sprinting=False
        return {"ok":True,"quiet":a.quiet}

    def _do_opening(self,a,opening='',op='open',**_):
        b,o=self.buildings.opening(opening)
        if o is None:return {'ok':False,'why':'no opening here'}
        center=tuple((p+q)/2 for p,q in zip(o['a'],o['b']))
        lat,lng=b.ll(center)
        # Reach the passage itself, including its edges, as the exit planner does.
        if point_segment(b.xy((a.lat,a.lng)),o['a'],o['b'])>2.7:
            return {'ok':False,'why':'too far from the opening'}
        if op not in ('open','close','smash','knock'):return {'ok':False,'why':'unknown opening action'}
        if op=='knock':return self._knock(a,b,o,(lat,lng))
        if op=='smash' and o['kind']!='window':return {'ok':False,'why':'only windows can be smashed'}
        if o['broken']:return {'ok':False,'why':'already broken open'}
        if op in ('open','smash') and any(h.get('defenses',{}).get(opening,{}).get('hp',0)>0 for h in self.homes.values()):
            return {'ok':False,'why':'remove the barricade before opening this passage'}
        forced=False
        if op=='open' and o.get('locked'):
            if not b.contains((a.lat,a.lng)):
                pry=survival.tool(a,'crowbar') or survival.tool(a,'hammer') or survival.tool(a,'axe')
                if not pry:return {'ok':False,'why':'locked: use a hammer, crowbar or axe; windows are another route'}
                pry['cond']=max(0,pry['cond']-1);a.end=max(0,a.end-6);a.busy_until=self.now+1.5;a.dirty=True;forced=True
            o['locked']=False
        if op=='close':
            bodies=[(x.lat,x.lng) for x in self.actors.values() if not x.dead]+[(x.lat,x.lng) for x in self.zeds.values() if x.alive]
            if any(point_segment(b.xy(p),o['a'],o['b'])<.55 for p in bodies):
                return {'ok':False,'why':'someone is in the opening'}
            o['open']=False
        else:
            o['open']=True
            if op=='smash':
                o['broken']=True;o['damage']=1
                from app.game import windows
                if not windows.tool(a):windows.cut(self,a,o)
                a.end=max(0,a.end-4);a.busy_until=self.now+.8;a.dirty=True
        self.buildings.dirty.add(o['id']);self.buildings.revision+=1
        self.noise(lat,lng,45 if op=='smash' or forced else 10,a)
        entrance=next((x for x in b.openings if x['label']=='Entrance'),None)
        if op!='close' and entrance and entrance.get('alarm') and not entrance.get('alarm_triggered'):
            entrance['alarm_triggered']=True;self.buildings.dirty.add(entrance['id'])
            self.noise(lat,lng,90,a,certain=True);self._ev(a,'alarm',name=b.name)
        if forced:self._ev(a,'pried',name=o['label'])
        self._ev(a,'opening',name=o['label'],op=op)
        return {'ok':True,'opening':o['id'],'op':op}

    def _knock(self,a,b,o,at):
        """Rap on a closed door or window. What is inside answers in its own time; nothing is shown."""
        if o['open'] or o['broken']:return {'ok':False,'why':'it is already open'}
        T=self.T
        a.busy_until=self.now+.6;a.dirty=True
        self.noise(at[0],at[1],T['knock_noise_m'],a)
        for z in self.zeds.values():
            if not z.alive or z.state not in ('idle','investigate'):continue
            if dist_m(at[0],at[1],z.lat,z.lng)>T['knock_inside_m'] or not b.contains((z.lat,z.lng)):continue
            z.state,z.goal,z.sleep_until='investigate',at,0.0
            z.next_groan=self.now+self.rng.uniform(.7,2.2)
        self._ev(a,'opening',name=o['label'],op='knock')
        return {'ok':True,'opening':o['id'],'op':'knock'}

    def _zed_obstacle(self,z,goal,stepm):
        start=(z.lat,z.lng)
        blocking=self.buildings.first_blocking(start,goal)
        if blocking is None:return goal
        b=blocking
        # Aim for a passage through the barrier, rather than grab through a wall.
        choices=[]
        for o in b.openings:
            center=tuple((p+q)/2 for p,q in zip(o['a'],o['b']))
            edge=(o['b'][0]-o['a'][0],o['b'][1]-o['a'][1]);n=math.hypot(*edge)
            points=[b.ll((center[0]-edge[1]/n*t,center[1]+edge[0]/n*t)) for t in (-.8,.8)]
            near=min(points,key=lambda p:dist_m(*start,*p));far=points[1] if near==points[0] else points[0]
            if not self.buildings.clear(start,near):continue
            score=dist_m(*start,*near)+dist_m(*far,*goal)
            choices.append((score,o,near,far))
        if choices:
            _,o,near,far=min(choices,key=lambda c:c[0])
            if dist_m(*start,*near)<.65:
                if (o['open'] or o['broken']) and not o.get('barricaded'):return far
                if survival.batter_opening(self,o['id'],stepm):return near
                o['damage']=min(1,o['damage']+stepm*(.12 if o['kind']=='window' else .07))
                self.buildings.dirty.add(o['id'])
                if o['damage']>=1:
                    o['broken']=o['open']=True;self.buildings.revision+=1
                    lat,lng=b.ll(tuple((p+q)/2 for p,q in zip(o['a'],o['b'])))
                    self.noise(lat,lng,35)
                    for a in self.actors.values():
                        if dist_m(a.lat,a.lng,lat,lng)<40:self._ev(a,'opening',name=o['label'],op='broken')
                return start
            return near
        # Outside obstacles: steer around a visible outer corner.
        center=(sum(p[0] for p in b.poly)/len(b.poly),sum(p[1] for p in b.poly)/len(b.poly))
        corners=[]
        for p in b.poly:
            dx,dy=p[0]-center[0],p[1]-center[1];n=math.hypot(dx,dy) or 1
            q=b.ll((p[0]+dx/n,p[1]+dy/n))
            if self.buildings.clear(start,q) and dist_m(*start,*q)>.7:
                corners.append(q)
        return min(corners,key=lambda q:dist_m(*start,*q)+dist_m(*q,*goal)) if corners else start


    def carry_capacity(self, a: Actor) -> float:
        return max(1.,self.T["carry_max"] + 0.4 * skill_level(a, "fitness") + equipment.bag_bonus(a)+backgrounds.factor(a,'carry',0.))

    def movement_speed(self, a: Actor) -> float:
        """The same pace is used for authority and client prediction."""
        if self.now<a.window_until or a.channel and a.channel['kind']=='window_work' and a.channel['op']=='vault':return 0.
        T = self.T
        leg_wounds = sum(1 for w in a.wounds if w["part"] in
                         ("left thigh", "right thigh", "left shin", "right shin"))
        endurance = min(1.0, max(0.0, a.end / T["end_max"]))
        fatigue = T["walk_speed_tired_floor"] + (1.0 - T["walk_speed_tired_floor"]) * endurance
        injury = max(0.48, T["walk_speed_leg_wound"] ** leg_wounds)
        critical = T["walk_speed_critical_hp"] if a.hp < 35 else 1.0
        combat = self.now-a.last_threat<2 or any(
            z.alive and z.target==a.id and (z.state=="engaged" or
            z.state in ("chase","alert") and dist_m(a.lat,a.lng,z.lat,z.lng)<7 and
            self.visible((a.lat,a.lng),(z.lat,z.lng))) for z in self.zeds.values())
        burden=max(.45,self.carry_capacity(a)/max(self.carry_capacity(a),a.weight()))
        multiplier = 1.0 if combat else T["walk_speed_explore_mult"]
        if a.sprinting and a.end>0:multiplier*=T["sprint_mult"]
        pace = min(T["pos_max_speed"], T["walk_speed_fresh"] * multiplier * fatigue * injury * critical * burden * equipment.speed_factor(a) * backgrounds.factor(a,'pace') * (1-.2*max(a.hunger,a.thirst,a.sleep)/100))
        pace *= a.mods.get("speed", 1.0)
        return min(pace, T["quiet_speed"]*backgrounds.factor(a,'pace')) if a.quiet else pace

    def heard_m(self, a: Actor) -> float:
        """How far this survivor's feet carry. Faster is louder; a sprint is heard a street away."""
        T = self.T
        if a.speed <= 0.4:
            return T["noise_still_m"]
        if a.sprinting:
            return T["noise_sprint_m"]*backgrounds.factor(a,'noise')
        if a.speed <= T["quiet_speed"] + 0.1:
            return T["noise_quiet_m"]*backgrounds.factor(a,'noise')
        if a.speed <= T["walk_speed_fresh"] * 1.3:
            return T["noise_walk_m"]*backgrounds.factor(a,'noise')
        return T["noise_travel_m"]*backgrounds.factor(a,'noise')

    def creeping(self, a: Actor) -> bool:
        return a.quiet and not a.sprinting and a.speed <= self.T["quiet_speed"] + 0.1

    def _step_actor(self, a: Actor, dt: float):
        T = self.T
        if a.location_loading_until:
            mapped = (a.gps_anchor is not None or getattr(self,'named_starts',False)) and hasattr(self,'resource_regions') and cell_of(a.lat,a.lng,6) in self.resource_regions
            if mapped or self.now >= a.location_loading_until:
                a.location_loading_until = 0
                a.transit_until = min(a.transit_until, self.now)
                a.placed_at = self.now
                a.dirty = True
        if a.lantern and not survival.tool(a,"lantern"):a.lantern=False;a.dirty=True
        if a.mods.get("regen") and a.hp > 0:
            a.hp = min(T["hp_max"], a.hp + a.mods["regen"] * dt)
        survival.update(self,a,dt)
        if not a.pending_learning:
            trial=copy.deepcopy(a) if getattr(self,'durable_learning',False) and a.study and a.study.get('kind','book')!='book' and study.progress(self,a)>=a.study['need_s'] else a
            told=study.update(self,trial)
            if trial is not a and a.study and trial.study is None:
                a.pending_learning=True
            elif trial is not a and told:
                a.study=trial.study;a.dirty=True
                self._ev(a,'work',message=told)
            elif told:self._ev(a,'work',message=told)
        memory.observe(self, a)
        weather.step(self, a)
        # --- real GPS stays aligned with the walk; desk movement is limited by injury/fatigue
        if a.raw is not None:
            lat, lng, acc = a.raw
            dx, dy = delta_m(a.lat, a.lng, lat, lng)
            d = math.hypot(dx, dy)
            if d > T["transit_jump_m"]:
                a.lat, a.lng = lat, lng
                self._wall_clearance(a)
                a.transit_until = self.now + T["transit_s"]
                a.speed = 0.0
            elif d > (.12 if a.position_mode=='desk' else min(T["pos_deadband_m"], max(1.0, acc * 0.5))) or (a.speed > 0.2 and d > (.08 if a.position_mode=='desk' else .5)):
                pace = T["walk_speed_fresh"] if a.position_mode == "gps" else self.movement_speed(a)
                stepm = min(d, min(T["pos_max_speed"], pace) * dt)
                if stepm > 0:
                    ox, oy = dx / d * stepm, dy / d * stepm
                    engaged = [z for z in self.zeds.values()
                               if z.state == "engaged" and z.target == a.id]
                    old_cell = cell_of(a.lat, a.lng, 7)
                    before=(a.lat,a.lng)
                    a.lat, a.lng = self.buildings.move(before,shift(a.lat,a.lng,ox,oy))
                    from app.game import windows
                    windows.crossing(self,a,before,(a.lat,a.lng))
                    ox,oy=delta_m(*before,a.lat,a.lng)
                    stepm=math.hypot(ox,oy)
                    for z in engaged:               # whatever has hold of you comes with you
                        z.lat, z.lng = self.buildings.move((z.lat,z.lng),shift(z.lat,z.lng,ox,oy))
                    a.walked_m += stepm
                    a.training_m += stepm
                    if a.training_m >= 100:
                        units = int(a.training_m // 100)
                        a.training_m -= units * 100
                        award(a, "fitness", units * 10)
                    new_cell = cell_of(a.lat, a.lng, 7)
                    if not a.explored:
                        a.explored.append(old_cell)
                    if new_cell not in a.explored:
                        a.explored.append(new_cell)
                        award(a, "scavenging", 10)
                    walk_cost = T["walk_end_per_m"] * (1 - .06 * skill_level(a, "fitness"))
                    a.end = max(0.0, a.end - walk_cost * stepm - (T["sprint_end_per_s"]*dt if a.sprinting else 0))
                    if a.end<=0:a.sprinting=False
                    a.dirty = True
                    a.heading = (math.degrees(math.atan2(ox, oy)) + 360.0) % 360.0
                    a.speed += (stepm / dt - a.speed) * min(1.0, dt * 3) if dt > 0 else 0.0
            else:
                a.speed += (0.0 - a.speed) * min(1.0, dt * 3)
        if dt <= 0:
            return
        engaged = chasers = 0
        for z in self.zeds.values():
            if z.target != a.id or not z.alive:
                continue
            if z.state == "engaged":
                engaged += 1
            if z.state in ("chase", "engaged", "alert") and dist_m(a.lat, a.lng, z.lat, z.lng) < 15.0:
                chasers += 1
        if engaged or chasers:
            a.last_threat = self.now
        # --- bleeding
        for w in a.wounds:
            if w["bleeding"]:
                rate = T["bleed"][w["kind"]] * (T["neck_bleed_mult"] if w["part"] == "neck" else 1.0)
                a.hp -= rate * dt
                a.dirty = True
                if w["kind"] == "scratch" and self.now - w["t"] > T["scratch_clot_s"]:
                    w["bleeding"] = False
                if a.hp <= 0 and not a.death:
                    a.death = {"cause": "bled out", "part": w["part"]}
        # --- infection runs on real hours
        if a.turns_at is not None and self.now >= a.turns_at and not a.dead:
            a.hp = 0
            a.death = {"cause": "turned"}
        # --- endurance only comes back when nothing has hold of you
        heavy = a.weight() > self.carry_capacity(a)
        working=a.channel and a.channel["kind"]=="work" and a.channel.get("op")!="rest"
        if not working and engaged == 0 and a.speed < 0.2 and self.now - a.last_action > T["end_regen_delay_s"] and a.end < T["end_max"]:
            a.end = min(T["end_max"], a.end + T["end_regen"] * backgrounds.factor(a,'regen') * (0.5 if heavy else 1.0) * dt)
        if a.mods.get("breathe"):                        # siege only: adrenaline, even with them on you
            a.end = min(T["end_max"], a.end + a.mods["breathe"] * dt)
        # --- panic follows what is around you
        target = min(100.0, T["panic_per_chaser"] * chasers + T["panic_per_engaged"] * engaged
                     + (20.0 if a.hp < 40 else 0.0))
        if a.panic < target:
            a.panic = min(target, a.panic + T["panic_up"] * backgrounds.factor(a,'panic') * dt)
        else:
            a.panic = max(target, a.panic - T["panic_down"] * dt)
        # --- severe panic can give away your position, even without pressing scream
        if (a.connected and not a.dead and a.hp > 0 and a.raw is not None
                and a.panic > T["panic_scream_min"] and self.now >= a.scream_ready_at
                and self.now >= a.panic_scream_ready_at):
            intensity = (a.panic - T["panic_scream_min"]) / (100.0 - T["panic_scream_min"])
            chance = 1.0 - math.exp(-T["panic_scream_per_s"] * intensity * dt)
            if self.rng.random() < chance:
                self._scream(a, involuntary=True)
        # --- timed actions
        ch = a.channel
        if ch and self.now >= ch["ends"]:
            a.channel = None
            self._finish_channel(a, ch)

    # ------------------------------------------------------------------ world loading
    def _load_cells(self):
        for a in self.actors.values():
            if a.dead or (a.lat == 0.0 and a.lng == 0.0):
                continue
            night = self.light_fn(a.lat, a.lng, self.now) < 0.4
            for cell in self.spawner.cells_near(a.lat, a.lng):
                key = (self.spawner.bucket(self.now), night)
                if self.loaded.get(cell) == key:
                    continue
                self.loaded[cell] = key
                for spec in self.spawner.zeds(cell, self.now):
                    if spec["id"] in self.zeds or self.dead_until.get(spec["id"], 0) > self.now:
                        continue
                    if spec.get("night") and not night:
                        continue
                    point = self.spawn_point(spec["lat"], spec["lng"])
                    if point is None:continue
                    self.zeds[spec["id"]] = Zed(
                        id=spec["id"], lat=point[0], lng=point[1], kind=spec["kind"],
                        hp=spec["hp"], hp_max=spec["hp"], speed=spec["speed"] * self.T["zed_speed_mult"],
                        variant=spec["variant"], home=point,
                        night=bool(spec.get("night")),
                        next_groan=self.now + self.rng.uniform(4, 30))
                    self.zeds[spec["id"]].spawn_unmapped = hasattr(self,"resource_regions") and cell_of(point[0],point[1],6) not in self.resource_regions
                    self._wall_clearance(self.zeds[spec['id']])
                for st in self.spawner.stashes(cell, self.now):
                    self.stashes.setdefault(st["id"], st)
        # forget what nobody is near
        if self.rng.random() < 0.02:
            self._unload()

    def _unload(self):
        live = [a for a in self.actors.values() if not a.dead]
        far = self.T["unload_m"]
        for zid, z in list(self.zeds.items()):
            if z.state == "engaged":
                continue
            if all(dist_m(a.lat, a.lng, z.lat, z.lng) > far for a in live):
                del self.zeds[zid]
                continue
            # The director's zombies were sent after someone. Once they have lost interest, and nobody
            # could see them, they go: at a busy start city nobody is ever 420 m away, and they piled up.
            if z.temp and z.state == "idle" and z.target is None:
                lost = self.now - max(z.last_seen or 0.0, z.spawned_at)
                if lost > self.T["temp_forget_s"] and all(dist_m(a.lat, a.lng, z.lat, z.lng) > self.sight_m(a) + 10.0 for a in live):
                    del self.zeds[zid]
        for sid, s in list(self.stashes.items()):
            if all(dist_m(a.lat, a.lng, s["lat"], s["lng"]) > far for a in live):
                del self.stashes[sid]
        keep = set()
        if self.spawner is not None:
            for a in live:
                keep.update(self.spawner.cells_near(a.lat, a.lng))
        for cell in list(self.loaded):
            if cell not in keep:
                del self.loaded[cell]

    # ------------------------------------------------------------------ zombies
    def _nearest_actor(self, z: Zed, limit: float):
        best, bd = None, limit
        for a in self.actors.values():
            if a.dead or a.transit_until > self.now:
                continue
            d = dist_m(z.lat, z.lng, a.lat, a.lng)
            if d < bd:
                best, bd = a, d
        return best, bd

    def _zed_range(self, z: Zed, a: Actor, hunting: bool = False) -> float:
        T = self.T
        light = self.light_fn(a.lat, a.lng, self.now)
        sight = T["zed_sight_night_m"] + (T["zed_sight_day_m"] - T["zed_sight_night_m"]) * light
        # Keeping low only helps before it has noticed you: one already chasing is not fooled.
        if not hunting and self.creeping(a):
            sight *= T["quiet_sight_mult"]
        return max(sight+(12 if a.lantern else 0), self.heard_m(a))

    def _step_zeds(self, dt: float):
        T, rng, now = self.T, self.rng, self.now
        live = [a for a in self.actors.values() if not a.dead]
        if not live:
            return
        engaged_count: dict[int, int] = {}
        for z in self.zeds.values():
            if z.state == "engaged" and z.target is not None:
                engaged_count[z.target] = engaged_count.get(z.target, 0) + 1
        for z in list(self.zeds.values()):
            if not z.alive:
                continue
            if z.sleep_until > now:
                continue
            if z.state in ("idle", "investigate"):
                near, nd = self._nearest_actor(z, T["active_m"])
                if near is None:                            # nobody around: it stands still
                    z.sleep_until = now + 5.0
                    continue
                if nd > 95.0 and z.state == "idle":         # nothing can close 20 m in under 6 s
                    z.sleep_until = now + (nd - 75.0) / 3.5
                    continue
                if nd > 75.0 and z.state == "idle":         # out of everyone's sight and earshot: no need to shuffle
                    z.sleep_until = now + 1.0
                    continue
            tgt = self.actors.get(z.target) if z.target is not None else None
            if tgt is not None and (tgt.dead or tgt.transit_until > now):
                tgt, z.target = None, None
                if z.state in ("chase", "engaged", "alert"):
                    z.state, z.goal = "idle", None

            # --- timed states
            if z.state == "stagger":
                if now >= z.t_state:
                    z.state = "chase" if tgt else "idle"
                continue
            if z.state == "down":
                if now >= z.t_state:
                    z.state, z.t_state = "rising", now + T["rise_s"]
                continue
            if z.state == "rising":
                if now >= z.t_state:
                    z.state = "chase" if tgt else "idle"
                continue
            if z.state == "alert":
                if now >= z.t_state:
                    z.state = "chase" if tgt else "idle"
                continue

            # --- groans carry further than sight
            if now >= z.next_groan:
                hunting = z.state in ("chase", "engaged")
                z.next_groan = now + (rng.uniform(3, 6) if hunting else rng.uniform(12, 30))
                self._groan(z, loud=hunting)

            # --- noticing
            if z.state in ("idle", "investigate"):
                a, d = self._nearest_actor(z, 60.0)
                if a is not None and not self.arriving(a):
                    rngm = self._zed_range(z, a)
                    # Feet are heard through a wall too, but a wall takes most of the sound.
                    if d <= rngm and (self.visible((z.lat,z.lng),(a.lat,a.lng)) or
                                      a.speed>.4 and d<self.heard_m(a)*T["noise_wall_mult"]):
                        rate = T["notice_rate_near"] if d < rngm * 0.5 else T["notice_rate_far"]
                        if now - a.born < T["grace_h"] * 3600:
                            rate *= T["grace_notice"]
                        if self.early(a):
                            rate *= T["early_notice"]
                        if rng.random() < 1.0 - math.exp(-rate * dt):
                            self._notice(z, a)
                            continue
                if z.state == "idle" and T["wander_step_s"] > dt:
                    # An idle zombie's shuffle (0.22 m/s) costs as much wall-steering as a chase. Taken in
                    # 0.6 s steps it covers the same ground for a third of the work; noticing above still
                    # runs every tick. Staggered so they don't all step on the same tick.
                    if z.wander_dt <= 0.0:
                        z.wander_dt = (zlib.crc32(z.id.encode()) % 1000) / 1000.0 * T["wander_step_s"]
                    z.wander_dt += dt
                    if z.wander_dt < T["wander_step_s"]:
                        continue
                    step_dt, z.wander_dt = z.wander_dt, 1e-9
                    self._wander(z, step_dt)
                    continue
                self._wander(z, dt)
                continue

            if tgt is None:
                z.state = "idle"
                continue
            d = dist_m(z.lat, z.lng, tgt.lat, tgt.lng)

            if z.state == "chase":
                if d <= self._zed_range(z, tgt, hunting=True) and self.visible((z.lat,z.lng),(tgt.lat,tgt.lng)):
                    z.last_seen = now
                elif d > T["lose_dist_m"] or now - z.last_seen > T["lose_after_s"]:
                    z.state, z.target = "investigate", None
                    z.goal = (tgt.lat, tgt.lng)
                    continue
                n_eng = engaged_count.get(tgt.id, 0)
                if d <= T["lunge_range_m"] and n_eng < T["max_engaged"] and self.buildings.clear((z.lat,z.lng),(tgt.lat,tgt.lng)):
                    z.state = "engaged"
                    z.attack_at = now + rng.uniform(*T["first_lunge_s"])
                    engaged_count[tgt.id] = n_eng + 1
                    if n_eng == 0:
                        self._ev(tgt, "grabbed", z=z.id)
                    if tgt.channel and tgt.channel["kind"] in ("search","search_building"):
                        tgt.channel = None
                        self._ev(tgt, "interrupted", what="search")
                    continue
                stop_at = T["ring_m"] if n_eng >= T["max_engaged"] else 0.0
                if d > stop_at + 0.1:
                    pace = z.speed * (T["early_speed"] if self.early(tgt) else 1.0)
                    self._walk(z, tgt.lat, tgt.lng, pace * dt, d - stop_at)
                continue

            if z.state == "engaged":
                z.last_seen = now
                if d > 1.5:                                 # shuffle in close
                    self._walk(z, tgt.lat, tgt.lng, 1.5 * dt, d - 1.2)
                if now >= z.attack_at:
                    z.attack_at = now + rng.uniform(*T["attack_every_s"])
                    self._attack(z, tgt, engaged_count.get(tgt.id, 1))

    def _walk(self, z: Zed, lat, lng, stepm: float, max_m: float):
        self._wall_clearance(z)
        survival.batter_object(self,z,stepm)
        lat,lng=self._zed_obstacle(z,(lat,lng),stepm)
        dx, dy = delta_m(z.lat, z.lng, lat, lng)
        d = math.hypot(dx, dy)
        if d < 1e-6:
            return
        m = min(stepm, d, max(0.0, max_m))
        z.lat, z.lng = self.buildings.move((z.lat,z.lng),shift(z.lat,z.lng,dx/d*m,dy/d*m))

    def _wander(self, z: Zed, dt: float):
        T, rng = self.T, self.rng
        if z.goal is None:
            if rng.random() < 0.05 * dt * 5:
                ang, r = rng.uniform(0, math.tau), rng.uniform(2, T["wander_r_m"])
                z.goal = shift(z.home[0], z.home[1], math.cos(ang) * r, math.sin(ang) * r)
            return
        d = dist_m(z.lat, z.lng, z.goal[0], z.goal[1])
        speed = z.speed * 0.8 if z.state == "investigate" else T["wander_speed"]
        if d < 1.0:
            z.goal = None
            if z.state == "investigate":
                z.state = "idle"
                z.home = (z.lat, z.lng)
            return
        before = (z.lat, z.lng)
        self._walk(z, z.goal[0], z.goal[1], speed * dt, d)
        # A goal behind a building can be unreachable. Steering round it costs a wall test per door and
        # corner, and the zombie used to pay that every tick for ever. Three steps without headway and
        # it gives up, as it would on reaching the spot.
        if dist_m(before[0], before[1], z.lat, z.lng) < 0.25 * min(speed * dt, d):
            z.stuck += 1
            if z.stuck >= 3:
                z.goal, z.stuck = None, 0
                if z.state == "investigate":
                    z.state = "idle"
                    z.home = (z.lat, z.lng)
        else:
            z.stuck = 0

    def _notice(self, z: Zed, a: Actor):
        T, rng = self.T, self.rng
        z.state, z.target = "alert", a.id
        z.t_state = self.now + rng.uniform(*T["alert_s"])
        z.last_seen = self.now
        z.goal = None
        z.next_groan = self.now + rng.uniform(2, 4)
        self._groan(z, loud=True, noticed=a.id)
        for o in self.zeds.values():                         # others turn to look
            if o is z or o.state not in ("idle", "investigate"):
                continue
            if dist_m(z.lat, z.lng, o.lat, o.lng) <= T["groan_pull_m"] and rng.random() < T["groan_pull_chance"]:
                o.state, o.target, o.goal = "alert", a.id, None
                o.t_state = self.now + rng.uniform(*T["alert_s"]) + rng.uniform(0.2, 1.2)
                o.last_seen = self.now

    def _groan(self, z: Zed, loud: bool, noticed: int | None = None):
        for a in self.actors.values():
            if a.dead:
                continue
            d = dist_m(a.lat, a.lng, z.lat, z.lng)
            if d > self.T["hearing_m"] * (1.0 if loud else 0.6):
                continue
            seen = d <= self.sight_m(a) and self.visible((a.lat,a.lng),(z.lat,z.lng))
            ev = {"b": round(bearing_deg(a.lat, a.lng, z.lat, z.lng)), "d": round(d),
                  "loud": loud, "seen": seen}
            if seen:
                ev["z"] = z.id
            if noticed == a.id:
                ev["you"] = True
            self._ev(a, "groan", **ev)

    def noise(self, lat: float, lng: float, radius: float, src: Actor | None = None, certain: bool = False):
        """A loud sound: everything idle within the radius comes to look."""
        if self.herds:
            herds.heard(self, lat, lng, radius, src)
        for z in self.zeds.values():
            if z.state not in ("idle", "investigate"):
                continue
            d = dist_m(lat, lng, z.lat, z.lng)
            if d > radius:                 # out of earshot: skip the wall test, which is the costly part
                continue
            audible=radius if self.visible((lat,lng),(z.lat,z.lng)) else radius*.55
            if d <= audible and (certain or self.rng.random() < (1.0 if d < radius * 0.5 else 0.6)):
                z.state, z.goal, z.sleep_until = "investigate", (lat, lng), 0.0

    # ------------------------------------------------------------------ being hit
    def _attack(self, z: Zed, a: Actor, n_engaged: int):
        if not self.buildings.clear((z.lat,z.lng),(a.lat,a.lng)):
            z.state='chase'
            return
        T, rng = self.T, self.rng
        if rng.random() < T["attack_miss"]:
            self._ev(a, "miss_you", z=z.id)
            return
        dmg = rng.uniform(*ZED_KINDS[z.kind]["dmg"]) * (z.boss["dmg"] if z.boss else 1.0) * a.mods.get("armor", 1.0)
        if vehicles.intercept(self,a,dmg):return
        if a.pending_work:
            self._ev(a,'interrupted',what='work');a.pending_work=None
        weights = dict(T["wound_weights"])
        if n_engaged >= 3 or (a.channel and a.channel["kind"] in ("bandage", "disinfect")):
            weights["bite"] *= 1.5                           # mobbed or busy: easier to bite
        if self.now - a.born < T["grace_h"] * 3600:
            weights["bite"] *= T["grace_bite"]
        kind = _pick(rng, list(weights.items()))
        part = _pick(rng, BODY_PARTS)
        protected = equipment.intercept(a, part, kind, rng)
        if protected:
            if a.channel:
                self._ev(a, "interrupted", what=a.channel["kind"])
                a.channel = None
            a.hp -= dmg*.15
            a.panic = min(100, a.panic+5)
            a.last_threat = self.now
            self._ev(a, "armor", code=protected["code"], part=part, cond=protected["cond"])
            if a.hp <= 0 and not a.death:a.death={"cause":"killed","by":n_engaged,"part":part}
            return
        wound = {"id": a._next_wound_id, "kind": kind, "part": part, "bleeding": True,
                 "bandaged": False, "clean": False, "t": self.now}
        a._next_wound_id += 1
        a.wounds.append(wound)
        if a.infected_at is None and rng.random() < T["infect"][kind]:
            a.infected_at = self.now
            a.turns_at = self.now + rng.uniform(*T["turn_after_h"]) * 3600.0
        a.hp -= dmg
        a.panic = min(100.0, a.panic + 8.0)
        a.dirty = True
        a.last_threat = self.now
        self._ev(a, "hit_you", z=z.id, dmg=round(dmg, 1), wound=kind, part=part, wid=wound["id"])
        if a.channel and a.channel["kind"] in ("bandage", "disinfect", "search", "search_building", "work", "window_work", "use", "pickup"):
            self._ev(a, "interrupted", what=a.channel["kind"])
            a.channel = None
        if a.panic >= T["drop_panic"] and n_engaged >= 3 and a.hands is not None \
                and rng.random() < T["drop_chance"]:
            self._drop_hands(a)
        if a.hp <= 0 and not a.death:
            a.death = {"cause": "killed", "by": n_engaged, "wound": kind, "part": part}

    def _drop_hands(self, a: Actor):
        row = a.item(a.hands)
        a.hands = None
        if row is None:
            return
        a.items.remove(row)
        ang = self.rng.uniform(0, math.tau)
        lat, lng = shift(a.lat, a.lng, math.cos(ang) * 1.5, math.sin(ang) * 1.5)
        did = f"d{self._drop_seq}"
        self._drop_seq += 1
        self.drops[did] = {"id": did, "lat": lat, "lng": lng, "code": row["code"],
                           "qty": row["qty"], "cond": row["cond"], "t": self.now}
        a.dirty = True
        self._ev(a, "dropped", code=row["code"], drop=did)

    def _die(self, a: Actor, death: dict):
        if a.dead:return
        a.dead, a.hp, a.channel = True, 0.0, None
        a.death = dict(death, t=self.now, lat=a.lat, lng=a.lng, kills=a.kills,
                       walked_m=round(a.walked_m), lived_s=round(self.now - a.born),
                       items=[{"code": i["code"], "qty": i["qty"]} for i in a.items],
                       infected=a.infected_at is not None)
        body=corpse_system.survivor(a,self.now)
        self.corpses[body['id']]=copy.deepcopy(body)
        self.corpse_dirty.add(body['id'])
        a.dirty = True
        memory.note_death(self, a)
        for z in self.zeds.values():
            if z.target == a.id and z.alive:
                z.target, z.state, z.goal = None, "idle", None
                z.home = (z.lat, z.lng)
        self._ev(a, "died", card=a.death)

    # ------------------------------------------------------------------ what the survivor does
    def _penalty(self, a: Actor) -> tuple[float, float, float]:
        """(damage multiplier, recovery multiplier, hit-chance loss) from tiredness."""
        if a.end < 10:
            return 0.45, 1.6, 0.20
        if a.end < 25:
            return 0.65, 1.35, 0.10
        if a.end < 50:
            return 0.85, 1.15, 0.0
        return 1.0, 1.0, 0.0

    def _reachable(self, a: Actor, reach: float, finish: bool = False, vision: bool = False) -> list[Zed]:
        out = []
        for z in self.zeds.values():
            if not z.alive:
                continue
            d = dist_m(a.lat, a.lng, z.lat, z.lng)
            # one on the ground is worth a step forward to finish
            if not ((z.state == "engaged" and z.target == a.id) or d <= reach or
                    (finish and z.state in ("down", "rising") and d <= self.T["finish_reach_m"])):
                continue
            # Distance first: the wall test is the costly part and most zombies are nowhere near.
            if self.buildings.clear((a.lat,a.lng),(z.lat,z.lng),radius=0,vision=vision):
                out.append(z)
        return out

    def _pick_target(self, a: Actor, target: str | None, reach: float, prefer_down: bool, vision: bool = False):
        cands = self._reachable(a, reach, finish=prefer_down,vision=vision)
        if not cands:
            return None
        if target:
            z = next((c for c in cands if c.id == target), None)
            if z is not None:
                return z
        if prefer_down:
            down = [c for c in cands if c.state in ("down", "rising")]
            if down:
                return min(down, key=lambda c: c.hp)
        up = [c for c in cands if c.state == "engaged" and c.target == a.id]
        if up:
            return min(up, key=lambda c: c.attack_at)        # whichever bites next
        standing = [c for c in cands if c.state not in ("down", "rising")]
        pool = standing or cands
        return min(pool, key=lambda c: dist_m(a.lat, a.lng, c.lat, c.lng))

    def act(self, actor_id: int, action: str, **kw) -> dict:
        """Returns {"ok": bool, "why"?: str, ...}. Side effects arrive as events."""
        a = self.actors.get(actor_id)
        if a is None or a.dead:
            return {"ok": False, "why": "dead"}
        if action=="stairs":
            from app.game import floors
            return floors.stairs(self,a,kw.get("op","up"))
        level=self.for_actor(a)
        if level is not self:return level.act(actor_id,action,**kw)
        now = self.now
        if action in ("swing", "shove", "shoot", "back", "bandage", "disinfect", "use",
                      "search", "search_body", "search_building", "pickup", "equip", "wear", "work", "window", "light", "drop", "opening"):
            if now < a.busy_until - 0.05:
                return {"ok": False, "why": "busy", "ready_in": round(a.busy_until - now, 2)}
            if a.channel and a.channel["kind"] == "back":
                return {"ok": False, "why": "busy", "ready_in": round(a.channel["ends"] - now, 2)}
        if action == "memory":
            return memory.view(self, a, kw.get("lat"), kw.get("lng"))   # looking at the map changes nothing
        if action == "pin":
            return memory.pin(self, a, **kw)                            # nor does writing on it
        fn = getattr(self, f"_do_{action}", None)
        if fn is None:
            return {"ok": False, "why": "unknown"}
        if action in ("scream","sprint","quiet"):
            return fn(a, **kw)  # calling out does not cancel bandaging or block combat
        if a.pending_work and action not in ('memory','pin'):
            self._ev(a,'interrupted',what='work');a.pending_work=None
        if a.channel and action != "cancel":                  # doing something else drops the timed action
            self._ev(a, "interrupted", what=a.channel["kind"])
            a.channel = None
        res = fn(a, **kw)
        if res.get("ok"):
            a.last_action = now
        return res

    def _kill(self, z: Zed, by: Actor | None, skill: str = "melee"):
        if z.id not in self.zeds:
            return
        z.state, z.target = "dead", None
        from app.game import corpses
        body = corpses.create(self,z)
        self.corpses[body['id']] = body
        self.corpse_dirty.add(body['id'])
        until = self.spawner.expires(self.now) if self.spawner is not None else self.now + 86400
        if not z.temp:
            self.dead_until[z.id] = until
            self.new_dead.append((z.id, until))
        if by is not None:
            by.kills += 1
            award(by, skill, 20)
            by.dirty = True
        del self.zeds[z.id]

    def _wear(self, a: Actor, row: dict | None):
        if row is None:
            return None
        if self.rng.random() < ITEMS[row["code"]]["wear"]:
            row["cond"] -= 1
            a.dirty = True
            if row["cond"] <= 0:
                a.items.remove(row)
                a.hands = None
                self._ev(a, "broke", code=row["code"])
                return "broke"
        return None

    def _scream(self, a: Actor, involuntary: bool = False) -> float:
        radius = self.sight_m(a)
        self.noise(a.lat, a.lng, radius, a, certain=True)
        a.scream_ready_at = self.now + self.T["scream_cooldown_s"]
        a.panic_scream_ready_at = self.now + self.T["panic_scream_gap_s"]
        self._ev(a, "scream", radius=round(radius, 1), involuntary=involuntary)
        return radius

    def _do_scream(self, a: Actor, **_):
        if self.now < a.scream_ready_at:
            return {"ok": False, "why": "catch your breath", "ready_in": round(a.scream_ready_at - self.now, 1)}
        return {"ok": True, "radius": round(self._scream(a), 1)}

    def _do_swing(self, a: Actor, target: str | None = None, **_):
        T, rng = self.T, self.rng
        row = a.weapon()
        if row is not None and ITEMS[row["code"]]["kind"] == "gun":
            row = None                                        # a pistol is a poor club: use fists
        spec = ITEMS[row["code"]] if row else FISTS
        dmg_mult, rec_mult, hit_loss = self._penalty(a)
        rec_mult *= a.mods.get("rec", 1.0)
        a.end = max(0.0, a.end - spec["end"] * a.mods.get("endc", 1.0))
        a.busy_until = self.now + spec["rec"] * rec_mult
        z = self._pick_target(a, target, T["swing_reach_m"], prefer_down=True)
        out = {"ok": True, "rec": round(spec["rec"] * rec_mult, 2), "weapon": row["code"] if row else "fists"}
        if z is None:
            return dict(out, hit=False, whiff=True)
        down = z.state in ("down", "rising")
        chance = 1.0 if down else max(0.25, T["base_hit"] - hit_loss
                                      - T["panic_hit_penalty"] * a.panic / 100.0)
        if rng.random() > chance:
            return dict(out, hit=False, z=z.id)
        if down:
            dmg = (rng.uniform(*spec["dmg"]) * T["finish_mult"]) if row else rng.uniform(*FISTS["stomp"])
        else:
            dmg = rng.uniform(*spec["dmg"])
        dmg *= dmg_mult * (1 + .04 * skill_level(a, "melee")) * a.mods.get("dmg", 1.0)
        award(a, "melee", 3)
        z.hp -= dmg
        out.update(hit=True, z=z.id, dmg=round(dmg, 1), finish=down)
        broke = self._wear(a, row)
        if broke:
            out["broke"] = True
        if a.mods.get("cleave"):
            out["cleave"] = self._cleave(a, z, spec, dmg_mult, int(a.mods["cleave"]))
        if z.hp <= 0:
            self._kill(z, a)
            return dict(out, kill=True)
        if not down:
            if spec.get("knock", 0) and not z.boss and rng.random() < spec["knock"]:
                z.state, z.t_state = "down", self.now + rng.uniform(*T["down_s"])
                out["down"] = True
            else:
                if z.state == "engaged":
                    z.attack_at = self.now + rng.uniform(*T["hit_reset_s"])
                else:
                    z.state, z.t_state = "stagger", self.now + T["hit_stagger_s"]
            if z.target is None:
                z.target = a.id
        return out

    def _cleave(self, a: Actor, first: Zed, spec: dict, dmg_mult: float, n: int) -> list:
        """Siege's wide arc: the same swing also catches up to n more zombies in reach."""
        hits = []
        others = sorted((z for z in self._reachable(a, self.T["swing_reach_m"]) if z is not first and z.alive),
                        key=lambda z: dist_m(a.lat, a.lng, z.lat, z.lng))
        for z in others[:n]:
            dmg = self.rng.uniform(*spec["dmg"]) * dmg_mult * a.mods.get("dmg", 1.0) * 0.7
            z.hp -= dmg
            if z.hp <= 0:
                self._kill(z, a)
                hits.append({"z": z.id, "kill": True})
            else:
                if z.state != "engaged" and not z.boss:
                    z.state, z.t_state = "stagger", self.now + self.T["hit_stagger_s"]
                hits.append({"z": z.id, "kill": False})
        return hits

    def _do_shove(self, a: Actor, target: str | None = None, **_):
        T, rng = self.T, self.rng
        dmg_mult, rec_mult, _ = self._penalty(a)
        a.end = max(0.0, a.end - T["shove_cost"] * a.mods.get("endc", 1.0))
        a.busy_until = self.now + T["shove_recover_s"] * rec_mult
        cands = [z for z in self._reachable(a, T["swing_reach_m"]) if z.state not in ("down", "rising")]
        first = self._pick_target(a, target, T["swing_reach_m"], prefer_down=False)
        if first is not None and first.state in ("down", "rising"):
            first = None
        order = ([first] if first else []) + sorted(
            (z for z in cands if z is not first),
            key=lambda z: (0 if z.state == "engaged" else 1, z.attack_at))
        hit = []
        kd = (T["shove_knockdown"] + a.mods.get("shove_kd", 0.0)) * (0.5 if a.end < 10 else 1.0)
        push = T['shove_push_m'] * a.mods.get("shove_push", 1.0)
        for z in order[:T["shove_targets"]]:
            if z.boss:                                   # a siege boss doesn't budge
                hit.append({"z": z.id, "down": False, "boss": True})
                continue
            dx, dy = delta_m(a.lat, a.lng, z.lat, z.lng)
            d = math.hypot(dx, dy) or 1.0
            z.lat, z.lng = self.buildings.move((z.lat,z.lng),shift(z.lat,z.lng,dx/d*push,dy/d*push))
            if z.target is None:
                z.target = a.id
            if rng.random() < kd:
                z.state, z.t_state = "down", self.now + rng.uniform(*T["down_s"])
                hit.append({"z": z.id, "down": True})
            else:
                z.state, z.t_state = "stagger", self.now + T["shove_stagger_s"]
                hit.append({"z": z.id, "down": False})
        return {"ok": True, "rec": round(T["shove_recover_s"] * rec_mult, 2), "hit": hit}

    def _do_shoot(self, a: Actor, target: str | None = None, **_):
        T, rng = self.T, self.rng
        row = a.weapon()
        if row is None or ITEMS[row["code"]]["kind"] != "gun":
            return {"ok": False, "why": "no gun"}
        if not a.take("ammo", 1):
            return {"ok": False, "why": "no ammo"}
        spec = ITEMS[row["code"]]
        a.busy_until = self.now + spec["rec"]
        self.noise(a.lat, a.lng, T["gun_noise_m"], a)
        z = self._pick_target(a, target, T["gun_range_m"], prefer_down=False,vision=True)
        out = {"ok": True, "rec": spec["rec"], "ammo": a.count("ammo")}
        self._wear(a, row)
        if z is None:
            return dict(out, hit=False, whiff=True)
        d = dist_m(a.lat, a.lng, z.lat, z.lng)
        chance = min(.98, max(0.15, 0.95 - 0.02 * d - 0.45 * a.panic / 100.0 + .02 * skill_level(a, "shooting")))
        if rng.random() > chance:
            return dict(out, hit=False, z=z.id)
        dmg = rng.uniform(*spec["dmg"])
        award(a, "shooting", 3)
        z.hp -= dmg
        if z.hp <= 0:
            self._kill(z, a, skill="shooting")
            return dict(out, hit=True, z=z.id, kill=True, dmg=round(dmg, 1))
        z.state, z.t_state = "stagger", self.now + 1.0
        if z.target is None:
            z.target = a.id
        return dict(out, hit=True, z=z.id, dmg=round(dmg, 1))

    def _do_back(self, a: Actor, **_):
        T = self.T
        if self.now < a.back_ready_at:
            return {"ok": False, "why": "cooldown", "ready_in": round(a.back_ready_at - self.now, 1)}
        if a.end < T["back_cost"]:
            return {"ok": False, "why": "too tired"}
        if not any(z.state == "engaged" and z.target == a.id for z in self.zeds.values()):
            return {"ok": False, "why": "nothing has hold of you"}
        a.end -= T["back_cost"]
        a.back_ready_at = self.now + T["back_cooldown_s"]
        a.channel = {"kind": "back", "ends": self.now + T["back_channel_s"]}
        a.busy_until = self.now + T["back_channel_s"]
        return {"ok": True, "rec": T["back_channel_s"]}

    def _do_bandage(self, a: Actor, wound: int | None = None, **_):
        w = self._wound(a, wound, lambda x: x["bleeding"])
        if w is None:
            return {"ok": False, "why": "nothing to bandage"}
        if a.count("bandage") < 1:
            return {"ok": False, "why": "no bandage"}
        duration = self.T["bandage_s"] * (1 - .08 * skill_level(a, "first_aid"))
        a.channel = {"kind": "bandage", "ends": self.now + duration, "total": duration, "wound": w["id"]}
        return {"ok": True, "channel": duration, "wound": w["id"]}

    def _do_disinfect(self, a: Actor, wound: int | None = None, **_):
        w = self._wound(a, wound, lambda x: not x["clean"])
        if w is None:
            return {"ok": False, "why": "nothing to clean"}
        if a.count("disinfectant") < 1:
            return {"ok": False, "why": "no disinfectant"}
        duration = self.T["disinfect_s"] * (1 - .08 * skill_level(a, "first_aid"))
        a.channel = {"kind": "disinfect", "ends": self.now + duration, "total": duration, "wound": w["id"]}
        return {"ok": True, "channel": duration, "wound": w["id"]}

    def _wound(self, a: Actor, wid, pred):
        if wid is not None:
            return next((w for w in a.wounds if w["id"] == wid and pred(w)), None)
        cands = [w for w in a.wounds if pred(w)]
        order = {"bite": 0, "laceration": 1, "scratch": 2}
        return min(cands, key=lambda w: (0 if w["part"] == "neck" else 1, order[w["kind"]])) if cands else None

    def _do_use(self, a: Actor, code: str = "", **_):
        spec = ITEMS.get(code)
        if spec is None or spec["kind"] not in ("drink", "food") or not a.take(code, 1):
            return {"ok": False, "why": "you do not have that"}
        a.busy_until = self.now + 1.0
        if "end" in spec:
            a.end = min(self.T["end_max"], a.end + spec["end"])
        a.hunger=max(0,a.hunger-spec.get("hunger",0))
        a.thirst=max(0,a.thirst-spec.get("thirst",0))
        if "calm" in spec:
            a.panic = max(0.0, a.panic - spec["calm"])
        return {"ok": True, "code": code, "rec": 1.0}

    def _do_work(self,a,**args):
        return survival.start(self,a,args)

    def _do_radio(self,a,**args):
        return broadcasts.action(self,a,**args)

    def _do_study(self, a, **args):
        return study.action(self, a, **args)

    def _do_light(self,a,**_):
        if not survival.tool(a,'lantern'):return {'ok':False,'why':'need a working lantern'}
        a.lantern=not a.lantern;a.dirty=True
        return {'ok':True,'message':'Lantern '+('on' if a.lantern else 'off')}

    def _do_wear(self, a: Actor, item=None, slot=None, op="wear", **_):
        return equipment.wear(a,item,slot,op)

    def _do_equip(self, a: Actor, item: int | None = None, **_):
        if item is None:
            a.hands = None
            return {"ok": True, "hands": None}
        row = a.item(item)
        if row is None or ITEMS[row["code"]]["kind"] not in ("weapon", "gun"):
            return {"ok": False, "why": "not a weapon"}
        a.hands = row["id"]
        a.busy_until = self.now + 0.6
        a.dirty = True
        return {"ok": True, "hands": row["id"], "rec": 0.6}

    def _do_drop(self, a: Actor, item: int | None = None, **_):
        row = a.item(item)
        if row is None:
            return {"ok": False, "why": "not in your pack"}
        if row["id"] in a.worn.values():
            return {"ok":False,"why":"take off worn equipment first"}
        row["qty"] -= 1
        if row["qty"] <= 0:
            a.items.remove(row)
            if a.hands == row["id"]:
                a.hands = None
        did = f"d{self._drop_seq}"
        self._drop_seq += 1
        lat, lng = shift(a.lat, a.lng, 1.0, 0)
        self.drops[did] = {"id": did, "lat": lat, "lng": lng, "code": row["code"],
                           "qty": 1, "cond": row["cond"], "t": self.now}
        a.dirty = True
        self._ev(a, "dropped", code=row["code"], drop=did, deliberate=True)
        return {"ok": True, "code": row["code"]}

    def _do_pickup(self, a: Actor, drop: str = "", **_):
        d = self.drops.get(drop)
        if d is None or dist_m(a.lat, a.lng, d["lat"], d["lng"]) > self.T["pickup_m"] or not self.buildings.clear((a.lat,a.lng),(d['lat'],d['lng'])):
            return {"ok": False, "why": "too far"}
        del self.drops[drop]
        row = a.add(d["code"], d["qty"], d["cond"])
        a.busy_until = self.now + 0.7
        if a.hands is None and ITEMS[d["code"]]["kind"] in ("weapon", "gun"):
            a.hands = row["id"]
        return {"ok": True, "code": d["code"], "rec": 0.7}

    def _do_search_building(self,a,**_):
        b=self.buildings.containing((a.lat,a.lng))
        if b is None:return {'ok':False,'why':'go inside a building first'}
        if a.building_searches.get(b.id,{}).get('attempts',0)>=2:
            return {'ok':False,'why':'both building search attempts are used'}
        if any(z.alive and z.state=='engaged' and z.target==a.id for z in self.zeds.values()):
            return {'ok':False,'why':'not with that on you'}
        duration=4*(1-.06*skill_level(a,'scavenging'))
        a.sprinting=False
        a.channel={'kind':'search_building','building':b.id,'start':[a.lat,a.lng],'ends':self.now+duration,'total':duration}
        self.noise(a.lat,a.lng,22,a)
        return {'ok':True,'channel':duration}

    def _do_search(self, a: Actor, stash: str = "", **_):
        T = self.T
        s = self.stashes.get(stash)
        if a.pending_search:
            return {"ok": False, "why": "your search is being saved"}
        if s is None or stash in a.claimed:
            return {"ok": False, "why": "nothing here"}
        if not self._stash_accessible(a,s):
            return {"ok": False, "why": "too far"}
        if any(z.state == "engaged" and z.target == a.id for z in self.zeds.values()):
            return {"ok": False, "why": "not with that on you"}
        duration = T["search_s"] * (1 - .06 * skill_level(a, "scavenging"))
        a.channel = {"kind": "search", "ends": self.now + duration, "total": duration, "stash": stash}
        self.noise(s["lat"], s["lng"], T["search_noise_m"], a)
        return {"ok": True, "channel": duration, "stash": stash}

    def _do_search_body(self, a: Actor, corpse: str = "", **_):
        from app.game import corpses
        body=self.corpses.get(corpse)
        if body and not corpses.allowed(a,body):return {'ok':False,'why':'this recovery pack belongs to another survivor'}
        if a.pending_body_search:return {'ok':False,'why':'your search is being saved'}
        if not body or body['searched']:return {'ok':False,'why':'nothing to search; look inside'}
        if not corpses.reachable(self,a,body):return {'ok':False,'why':'approach the body first'}
        if any(z.alive and z.state=='engaged' and z.target==a.id for z in self.zeds.values()):
            return {'ok':False,'why':'escape the zombies first'}
        duration=self.T['search_s']*(1-.06*skill_level(a,'scavenging'))
        a.sprinting=False
        a.channel={'kind':'search_body','corpse':corpse,'ends':self.now+duration,'total':duration}
        self.noise(body['lat'],body['lng'],self.T['search_noise_m'],a)
        return {'ok':True,'channel':duration}

    def _do_cancel(self, a: Actor, **_):
        a.channel = None
        a.pending_window=None
        a.pending_work=None
        return {"ok": True}

    def _do_window(self,a,**args):
        from app.game import windows
        return windows.start(self,a,**args)

    def _finish_channel(self, a: Actor, ch: dict):
        T = self.T
        kind = ch["kind"]
        if kind == 'window_work':
            if getattr(self,'durable_corpses',False):a.pending_window=ch
            else:
                from app.game import windows
                windows.finish(self,a,ch)
        elif kind == "work":
            if getattr(self,'durable_loot',False) and a.home and a.home.get('_shared'):a.pending_work=ch
            else:survival.finish(self,a,ch)
        elif kind == "back":
            for z in self.zeds.values():
                if z.state == "engaged" and z.target == a.id:
                    dx, dy = delta_m(a.lat, a.lng, z.lat, z.lng)
                    d = math.hypot(dx, dy) or 1.0
                    z.lat, z.lng = self.buildings.move((z.lat,z.lng),shift(z.lat,z.lng,dx/d*T['back_push_m'],dy/d*T['back_push_m']))
                    z.state, z.t_state = "stagger", self.now + T["back_stagger_s"]
            self._ev(a, "broke_free")
        elif kind == "bandage":
            w = next((x for x in a.wounds if x["id"] == ch["wound"]), None)
            if w is not None and w["bleeding"] and a.take("bandage", 1):
                w["bleeding"], w["bandaged"] = False, True
                a.dirty = True
                self._ev(a, "bandaged", wid=w["id"], part=w["part"])
                award(a, "first_aid", 20)
        elif kind == "disinfect":
            w = next((x for x in a.wounds if x["id"] == ch["wound"]), None)
            if w is not None and not w["clean"] and a.take("disinfectant", 1):
                w["clean"] = True
                a.dirty = True
                self._ev(a, "cleaned", wid=w["id"], part=w["part"])
                award(a, "first_aid", 15)
        elif kind == "search_building":
            b=self.buildings.containing((a.lat,a.lng))
            if b is None or b.id!=ch['building'] or dist_m(a.lat,a.lng,*ch['start'])>1:
                self._ev(a,'interrupted',what='search_building');return
            record=a.building_searches.setdefault(b.id,{'attempts':0,'caches':[]})
            if record['attempts']>=2:return
            attempt=record['attempts'];record['attempts']+=1;a.dirty=True
            from app.rng import seeded
            rng=seeded(f'building-search:{a.id}:{a.born}:{b.id}:{attempt}')
            found=rng.random()<.7+.02*skill_level(a,'scavenging')
            cache=None
            if found and b.rooms:
                room=min(b.rooms,key=lambda r:dist_m(a.lat,a.lng,*b.ll(r['pos'])))
                lat,lng=b.ll(room['pos'])
                # Separate discovered chests from the original room container.
                sign=1 if attempt==0 else -1
                for dx,dy in ((3*sign,0),(0,3*sign),(-3*sign,0),(0,-3*sign),(1.4*sign,0),(0,1.4*sign)):
                    pos=shift(lat,lng,dx,dy)
                    if b.contains(pos) and self.buildings.clear((lat,lng),pos):
                        lat,lng=pos;break
                kind=self._supply_kind(b,room)
                table=STASH_LOOT[kind];loot=[];condition={}
                for _ in range(3):
                    code=_pick(rng,[(c,w) for c,w,_q in table])
                    lo,hi=next(q for c,_w,q in table if c==code)
                    loot.append([code,rng.randint(lo,hi)])
                    if ITEMS[code]['kind'] in ('weapon','gun'):condition[code]=rng.randint(5,9)
                cache={'id':f'hidden:{b.id}:{a.id}:{attempt}','building':b.id,'room':room['name'],
                       'lat':lat,'lng':lng,'kind':kind,'loot':loot,'condition':condition}
                cache['floor_level']=a.floor_level;record['caches'].append(cache)
                self.stashes[cache['id']]=dict(cache,owner=a.id)
                award(a,'scavenging',10)
            self._ev(a,'building_searched',building=b.id,left=2-record['attempts'],
                     found=cache is not None,stash=cache['id'] if cache else None,room=cache['room'] if cache else None)
        elif kind == "search_body":
            from app.game import corpses
            body=self.corpses.get(ch['corpse'])
            if not body or not corpses.reachable(self,a,body):
                self._ev(a,'interrupted',what='search_body');return
            if getattr(self,'durable_corpses',False):a.pending_body_search=body['id']
            else:corpse_system.reveal(a,body)
        elif kind == "search":
            s = self.stashes.get(ch["stash"])
            if s is not None and ch["stash"] not in a.claimed:
                if not self._stash_accessible(a,s):
                    self._ev(a, "interrupted", what="search")
                    return
                if getattr(self, 'durable_loot', False):
                    import copy
                    a.pending_search = copy.deepcopy(s)
                else:
                    loot_system.reveal(a, s)

    # ------------------------------------------------------------------ what one survivor is sent
    def moodles(self, a: Actor) -> list:
        """Status icons, shown only when something is wrong. [(code, level 1..4)]"""
        T = self.T
        out = []
        for code,value in (("hungry",a.hunger),("thirsty",a.thirst),("sleepy",a.sleep)):
            if value>35:out.append((code,min(4,1+int((value-35)/20))))
        bleed = sum(1 for w in a.wounds if w["bleeding"])
        if bleed:
            out.append(("bleeding", min(4, bleed + (1 if any(w["part"] == "neck" and w["bleeding"] for w in a.wounds) else 0))))
        if a.hp < 80:
            out.append(("hurt", 1 if a.hp >= 60 else 2 if a.hp >= 40 else 3 if a.hp >= 20 else 4))
        if a.panic >= 20:
            out.append(("panic", 1 if a.panic < 40 else 2 if a.panic < 60 else 3 if a.panic < 80 else 4))
        if a.end < 50:
            out.append(("winded", 1 if a.end >= 25 else 2 if a.end >= 10 else 3 if a.end > 0 else 4))
        if a.weight() > self.carry_capacity(a):
            out.append(("heavy", 1 if a.weight() < self.carry_capacity(a) * 1.25 else 2))
        if a.infected_at is not None and a.turns_at:
            frac = (self.now - a.infected_at) / max(1.0, a.turns_at - a.infected_at)
            if frac >= 0.75:
                out.append(("fever", 3 if frac < 0.9 else 4))
            elif frac >= 0.4:
                out.append(("queasy", 1 if frac < 0.6 else 2))
        return out

    # ------------------------------------------------------------------ other players
    OTHERS_MAX = 12

    def presence_state(self, o: Actor) -> str:
        """A one-word answer to "what is that survivor doing?" for other players' screens."""
        ch = o.channel
        if o.vehicle_id:
            return "driving"
        if any(z.alive and z.target == o.id and z.state == "engaged" for z in self.zeds.values()) or self.now - o.last_action < 1.5 and self.now - o.last_threat < 3.0:
            return "fighting"
        if ch:
            k = ch.get("kind", "")
            return "searching" if k.startswith("search") else "treating" if k in ("bandage", "disinfect") else "reading" if k in ("study", "learn") else "working"
        if o.pending_work:
            return "working"
        if o.sprinting and o.speed > 0.4:
            return "running"
        if self.creeping(o) and o.speed > 0.2:
            return "sneaking"
        return "walking" if o.speed > 0.4 else "standing"

    def presence_id(self, o: Actor) -> str:
        """Opaque, and new with every life and every server start: not the account, not the survivor."""
        import hashlib
        salt = getattr(self, "_presence_salt", None)
        if salt is None:
            import secrets
            salt = self._presence_salt = secrets.token_bytes(16)
        return hashlib.blake2b(f"{o.id}:{o.life_id}".encode(), key=salt, digest_size=5).hexdigest()

    def others_near(self, a: Actor, sight: float) -> list:
        """Other players this survivor can see, nearest first: [id, lat, lng, name, state, heading].

        Only on servers without real GPS (`show_others`), where every position is a spot in a public
        city centre rather than somebody's street. Teammates already arrive as `allies`. The same
        rules as zombies: within sight, not through walls, on the same floor of the same building."""
        if not getattr(self, "show_others", False):
            return []
        mine = bases.owner(a)
        near = []
        for o in self.actors.values():
            if o.id == a.id or o.dead or not o.connected or (o.lat == 0.0 and o.lng == 0.0):
                continue
            if o.floor_level != a.floor_level or o.floor_building != a.floor_building or bases.owner(o) == mine:
                continue
            d = dist_m(a.lat, a.lng, o.lat, o.lng)
            if d <= sight:
                near.append((d, o))
        near.sort(key=lambda t: t[0])
        out = []
        for d, o in near:
            if len(out) >= self.OTHERS_MAX:
                break
            if not self.visible((a.lat, a.lng), (o.lat, o.lng)):
                continue
            out.append([self.presence_id(o), round(o.lat, 7), round(o.lng, 7),
                        o.name if getattr(self, "others_names", True) else "Survivor",
                        self.presence_state(o), round(o.heading, 2)])
        return out

    def view(self, actor_id: int, known=None) -> dict:
        """What one survivor can see. `known` is the "building_key" of the last view that reached
        their screen: while it still matches, the walls around them are not described again
        (drawing up some 150 outlines five times a second, to be thrown away, was half the cost)."""
        a = self.actors[actor_id]
        level=self.for_actor(a)
        if level is not self:return level.view(actor_id,known)
        sight = self.sight_m(a)
        # Asked from a 40 m grid, so walking changes this list every few seconds, not twice a second:
        # each change re-sends every outline in range, some 165 kB. 180 m from the grid point still
        # covers 150 m from the survivor, nearly three times the furthest anyone can see.
        grid = 40.0 / 111320.0
        near = self.buildings.near((round(a.lat / grid) * grid, round(a.lng / grid) * grid), 180)
        barriers = survival.barrier_snapshots(self, a)
        building_key = (self.buildings.revision, tuple(b.id for b in near) + tuple(b['id'] for b in barriers),a.floor_level,a.floor_building)
        zs = []
        for z in self.zeds.values():
            if not z.alive:
                continue
            mine = z.target == a.id
            d = dist_m(a.lat, a.lng, z.lat, z.lng)
            if d > sight and not (mine and z.state == "engaged"):
                continue
            if not self.visible((a.lat,a.lng),(z.lat,z.lng)):continue
            row = [z.id, round(z.lat, 7), round(z.lng, 7), z.state, z.kind, z.variant,
                   1 if mine else 0,
                   round(max(0.0, z.attack_at - self.now), 2) if (mine and z.state == "engaged") else -1,
                   round(max(0.0, z.hp / z.hp_max), 2)]
            zs.append(row)
        weapon = a.weapon()
        swing_target=self._pick_target(a,None,self.T["swing_reach_m"],prefer_down=True)
        shove_target=self._pick_target(a,None,self.T["swing_reach_m"],prefer_down=False)
        if shove_target and shove_target.state in ("down","rising"):shove_target=None
        shot_target=self._pick_target(a,None,self.T["gun_range_m"],prefer_down=False,vision=True) if weapon and ITEMS[weapon["code"]]["kind"]=="gun" else None
        inside = self.buildings.containing((a.lat,a.lng))
        return {
            "now": round(self.now, 2),
            "others": self.others_near(a, sight),
            "vehicles":vehicles.view(self,a),
            "allies":[{'id':other.id,'name':other.name,'lat':round(other.lat,9),'lng':round(other.lng,9),
                       'speed':round(other.speed,2),'heading':round(other.heading,2),'hp':round(other.hp,1)}
                      for other in sorted(self.actors.values(),key=lambda x:dist_m(a.lat,a.lng,x.lat,x.lng))
                      if other.id!=a.id and not other.dead and bases.owner(other)==bases.owner(a)
                      and other.floor_level==a.floor_level and other.floor_building==a.floor_building
                      and dist_m(a.lat,a.lng,other.lat,other.lng)<=sight
                      and self.visible((a.lat,a.lng),(other.lat,other.lng))][:16],
            "you": {
                "lat": round(a.lat, 9), "lng": round(a.lng, 9), "hp": round(a.hp, 1),
                "vehicle":a.vehicle_id,
                "end": round(a.end, 1), "panic": round(a.panic), "speed": round(a.speed, 2),
                "lantern": a.lantern, "needs": {"hunger":round(a.hunger),"thirst":round(a.thirst),"sleep":round(a.sleep)},
                "walk_speed": round(self.movement_speed(a), 3), "sprinting": a.sprinting,
                "quiet": a.quiet, "heard_m": round(self.heard_m(a)),
                "building_search_left": max(0,2-a.building_searches.get(inside.id,{}).get("attempts",0)) if inside else 0,
                "scream": round(max(0.0, a.scream_ready_at - self.now), 1),
                "busy": round(max(0.0, a.busy_until - self.now), 2),
                "back": round(max(0.0, a.back_ready_at - self.now), 1),
                "channel": ({"kind": a.channel["kind"], "left": round(a.channel["ends"] - self.now, 2), "stash": a.channel.get("stash"), "total": a.channel.get("total")}
                            if a.channel else {'kind':'work','left':0,'total':.1} if a.pending_work else None),
                "hands": ({"id": weapon["id"], "code": weapon["code"], "cond": weapon["cond"]} if weapon else None),
                "ammo": a.count("ammo"), "moodles": self.moodles(a), "kills": a.kills,
                "weight": round(a.weight(), 1), "dead": a.dead,"life_id":a.life_id,
                "combat":{"swing":swing_target.id if swing_target else None,"shoot":shot_target.id if shot_target else None,"shove":shove_target.id if shove_target else None},
                "transit": a.transit_until > self.now, "arriving": self.arriving(a),
                "placement_epoch": a.placement_epoch,"floor":a.floor_level,"floor_epoch":a.floor_epoch,
            },
            "sight": round(sight, 1),
            "mapping": hasattr(self, "resource_regions") and cell_of(a.lat, a.lng, 6) not in self.resource_regions,
            **({} if known is not None and known == building_key else {"buildings": [b.snapshot() for b in near] + barriers}),
            "building_revision": self.buildings.revision, "building_key": building_key,
            "room": inside.room_at((a.lat,a.lng)) if inside else None,
            "inside": inside.id if inside else None,
            "z": zs,
            "herds": herds.view(self, a) if self.herds else [],
            "stashes": [[s["id"], round(s["lat"], 7), round(s["lng"], 7), s["kind"], s["id"] in a.claimed, s.get('building'), s.get('room'), self._stash_accessible(a,s), self._stash_seen(a,s,inside)]
                        for s in loot_system.containers(self, a)
                        if s.get("owner",a.id)==a.id and dist_m(a.lat, a.lng, s["lat"], s["lng"]) <= 180.0],
            "loot": loot_system.visible(self, a),
            "corpses": corpse_system.visible(self,a),
            "drops": self._visible_drops(a, sight),
        }

    def _visible_drops(self, a: Actor, sight: float) -> list:
        """Nearest first, at most DROP_VIEW_LIMIT, so the wall tests stay few however many lie about."""
        box = sight / 111320.0
        near = sorted((dist_m(a.lat, a.lng, d["lat"], d["lng"]), did) for did, d in self.drops.items()
                      if abs(d["lat"] - a.lat) <= box)
        out = []
        for dm, did in near:
            if dm > sight or len(out) >= DROP_VIEW_LIMIT:
                break
            d = self.drops[did]
            if self.visible((a.lat, a.lng), (d["lat"], d["lng"])):
                out.append([d["id"], round(d["lat"], 7), round(d["lng"], 7), d["code"]])
        return out

    def body(self, a: Actor) -> dict:
        level=self.for_actor(a)
        if level is not self:return level.body(a)
        """The slower-changing half of the survivor: wounds and what they carry."""
        return {"wounds": [{k: w[k] for k in ("id", "kind", "part", "bleeding", "bandaged", "clean")}
                           for w in a.wounds],
                "items": [{"id": i["id"], "code": i["code"], "qty": i["qty"], "cond": i["cond"]}
                          for i in a.items],
                "hands": a.hands, "weight": round(a.weight(), 1), "carry_max": self.carry_capacity(a),
                "worn": dict(a.worn), "home": home.summary(self,a), "survival": survival.view(self,a),
                "study": study.view(self, a), "studied": list(a.studied), "knowledge":list(a.knowledge), "lessons":study.catalog(a),
                "background":backgrounds.view(a),
                "base":bases.view(a),
                "day": weather.life_day(a, self.now), "weather": weather.view(self, a),
                "progression": progression_view(a),
                "building_searches": {bid:{"attempts":r.get("attempts",0),"caches":len(r.get("caches",[]))} for bid,r in a.building_searches.items()}}
