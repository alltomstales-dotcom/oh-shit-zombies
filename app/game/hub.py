"""The running game: one World, one clock, everybody's connection.

The loop steps the world five times a second and sends each survivor what they can perceive.
Actions do not wait for the loop: they are applied the moment they arrive.
"""
from __future__ import annotations

import asyncio
import logging
import time
import secrets

from app.daylight import light_level
from app.db import get_sessionmaker
from app.config import get_settings
from app.game import store, home, survival, placement, loot, corpses, floors, bases, vehicles, broadcasts, study, privacy
from sqlalchemy import select, update
from app.models import Player, PlayerHome, PlayerMemory, WorldCorpse, BuildingLevel, BuildingOpening, WorldVehicle, WorldEvent
from functools import wraps

def serialized(fn):
    @wraps(fn)
    async def run(self,*args,**kwargs):
        async with self.state_lock:
            return await fn(self,*args,**kwargs)
    return run
from app.game.director import Director
from app.game import difficulty as difficulty_profiles
from app.game.building_loader import BuildingLoader
import math
import copy
from app.game.sim import Actor, World, bearing_deg
from app.game.spawn import Spawner

log = logging.getLogger("osz.hub")
TICK_S = 0.2
SLOW_TICK_S = 1.5          # a tick this long is worth a line in the log
STALL_EXIT_S = 45.0        # the whole server is frozen: print where, and let the host restart it
SAVE_EVERY_S = 10.0
LINKDEAD_S = 20.0          # quitting mid-fight does not save you: the body stays this long
RETENTION_EVERY_S = 6 * 3600.0
# An action steps the world first only if the loop has fallen this far behind. It was 0.2 s (a tick),
# but under load ticks run long, the world is then always that old, and stepping for actions made the
# loop slower still: the soak of 2 November spiralled that way. 0 steps before every action, as it used to.
ACT_STEP_MIN_S = float(__import__("os").environ.get("OSZ_ACT_STEP_MIN_S", "1.0"))
BODY_EVERY_S = 1.0         # the slow half of a frame is rebuilt this often, or at once after an action or event
STATS_EVERY_S = 60.0       # a line of counts for the operator: loop time, survivors, zombies, corpses
# Off unless set: every this many seconds, profile PROFILE_TICKS ticks in-process and log the costliest
# functions. The soak of 2 November slowed for hours and nobody could attach a profiler to the container.
PROFILE_EVERY_S = float(__import__("os").environ.get("OSZ_PROFILE_EVERY_S", "0") or 0)
PROFILE_TICKS = int(__import__("os").environ.get("OSZ_PROFILE_TICKS", "50") or 50)


class Conn:
    def __init__(self, player_id: int, survivor_id: int, send):
        self.player_id = player_id
        self.survivor_id = survivor_id
        self.send = send
        self.gone_at: float | None = None
        self.last_full = 0.0
        self.body_sent = None
        self.building_key = None
        self.corpse_key = None
        self.stashes_sent = None
        self.body_at = 0.0
        self.placement_ticket = secrets.token_urlsafe(24)
        self.launch_placed = False
        self.placement_receipts = {}
        self.kick = None


class Hub:
    def __init__(self, density: float = 1.0, difficulty: dict | None = None):
        real_gps = get_settings().real_gps
        # A long jump in a position report used to mean "travelled by car in real life". With no
        # real GPS it can only be a cheat, or a way to make the server map the whole planet.
        tune = {} if real_gps else {"transit_jump_m": float("inf")}
        self.difficulty = difficulty
        if difficulty is not None:
            from app.game.content import TUNE
            tune.update(difficulty_profiles.tune_for(difficulty, TUNE))
            density = difficulty["density"]
        self.world = World(light_fn=lambda lat, lng, now: light_level(lat, lng, int(now)),
                           spawner=Spawner(density=density,
                                           night_packs=difficulty["night_packs"] if difficulty else 1.0),
                           tune=tune or None)
        self.world.named_starts = not real_gps
        # Strangers see each other only where nobody's position is a real place (named city starts).
        self.world.show_others = not real_gps
        self.world.others_names = not get_settings().free_text      # generated names only
        self.world.durable_learning = True
        self.world.durable_loot = True
        self.world.durable_corpses = True
        self.director = Director(self.world, config=difficulty["director"] if difficulty else None)
        self.building_loader = BuildingLoader(self.world)
        self.conns: dict[int, Conn] = {}
        self._task: asyncio.Task | None = None
        self._last_save = 0.0
        self._last_vehicle_save=0.
        self.clock = time.time
        self.state_lock = asyncio.Lock()
        self.building_loader.state_lock=self.state_lock

    # ---------------------------------------------------------------- lifecycle
    async def start(self):
        try:
            async with get_sessionmaker()() as s:
                self.world.dead_until = await store.load_dead(s, self.clock())
                self.world.corpses = await corpses.load(s,self.clock())
                self.world.upper_corpses={cid:b for cid,b in self.world.corpses.items() if b.get('floor_level',0)>0}
                self.world.corpses={cid:b for cid,b in self.world.corpses.items() if not b.get('floor_level',0)}
                self.world.corpse_ready = set(self.world.corpses)
                rows=(await s.execute(select(PlayerHome))).scalars().all()
                self.world.homes={r.player_id:copy.deepcopy(r.state) for r in rows}
                self.world.vehicles=await vehicles.load(s)
                self.world.broadcast_fired=await broadcasts.load(s,self.clock())
        except Exception:
            log.exception("could not load dead zombies")
        self.building_loader.start()
        self._task = asyncio.create_task(self._loop())
        self._pulse_task = asyncio.create_task(self._pulse())
        self._start_watchdog()
        self._retention_task = asyncio.create_task(self._retention())

    async def _retention(self):
        while True:
            await asyncio.sleep(RETENTION_EVERY_S)
            try:
                await self.purge_inactive()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("retention sweep failed")

    async def purge_inactive(self) -> int:
        """Delete anonymous accounts nobody has opened for retention_days."""
        cutoff = self.clock() - get_settings().retention_days * 86400
        async with get_sessionmaker()() as s:
            ids = (await s.execute(select(Player.id).where(Player.last_seen < cutoff).limit(200))).scalars().all()
        gone = 0
        for pid in ids:
            if pid not in self.conns:
                await self.forget_player(pid)
                gone += 1
        return gone

    @staticmethod
    async def _touch(pid: int, now: float):
        async with get_sessionmaker()() as s:
            await s.execute(update(Player).where(Player.id == pid).values(last_seen=int(now)))
            await s.commit()

    @serialized
    async def forget_player(self, pid: int):
        """Everything held about one player goes, from memory and from the database, in one step."""
        w = self.world
        conn = self.conns.pop(pid, None)
        a = w.actors.get(pid)
        if a is not None:
            if a.vehicle_id and a.vehicle_id in w.vehicles:
                vehicles.release(a, w.vehicles[a.vehicle_id]);w.vehicle_dirty.add(a.vehicle_id)
            w.remove_actor(pid)
            self.director.forget(pid)
        w.memories.pop(pid, None);w.memory_state.pop(pid, None)
        w.memory_dirty.discard(pid);w.home_dirty.discard(pid)
        w.homes.pop(pid, None)
        for v in w.vehicles.values():
            if v.get('owner') == pid:
                v['owner'] = None;w.vehicle_dirty.add(v['id'])
        for context in [w, *w.levels.values()]:
            for store_ in (context.corpses, getattr(context, 'upper_corpses', {})):
                for cid in [c for c, b in store_.items() if b.get('owner') == pid]:
                    del store_[cid];context.corpse_dirty.discard(cid)
        async with get_sessionmaker()() as s:
            await privacy.delete_player(s, pid)
            # Anyone working from this player's shared base falls back to their own home.
            for other in w.actors.values():
                if bases.owner(other) == pid:
                    await bases.bind(s, w, other)
        if conn is not None and conn.kick:
            conn.kick()

    async def _pulse(self):
        while True:
            self._pulse_at = time.monotonic()
            await asyncio.sleep(1.0)

    def _start_watchdog(self):
        """One frozen calculation stops the game for everybody and no request can report it.

        A plain thread notices when the event loop has not run for STALL_EXIT_S, writes every
        thread's stack to the log and exits, so the host's restart policy brings the game back.
        Survivors are saved every few seconds, so little is lost.
        """
        import faulthandler, os, sys, threading
        self._pulse_at = time.monotonic()
        self._watching = True

        def watch():
            while self._watching:
                time.sleep(5.0)
                stalled = time.monotonic() - self._pulse_at
                if self._pulse_task.done():          # the loop was shut down, not frozen
                    return
                if self._watching and stalled > STALL_EXIT_S:
                    print(f"osz watchdog: event loop stalled for {stalled:.0f}s; stacks follow, then exit",
                          file=sys.stderr, flush=True)
                    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
                    sys.stderr.flush()
                    os._exit(70)

        threading.Thread(target=watch, name="osz-watchdog", daemon=True).start()

    async def stop(self):
        self._watching = False
        if getattr(self, "_pulse_task", None):
            self._pulse_task.cancel()
        if getattr(self, "_retention_task", None):
            self._retention_task.cancel()
        if self._task:
            self._task.cancel()
        await self.building_loader.stop()
        await self.save_all(force=True)

    async def _loop(self):
        while True:
            prof = self._profile_start()
            t0 = time.perf_counter()
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("tick failed")
            took = time.perf_counter() - t0
            if prof is not None:
                self._profile_stop(prof)
            self._stats_tick(took)
            if took > SLOW_TICK_S:
                w = self.world
                log.warning("slow tick %.1fs: %d survivors, %d zombies, %d buildings",
                            took, len(w.actors), len(w.zeds), len(w.buildings.items))
            await asyncio.sleep(max(0.01, TICK_S - took))

    def _profile_start(self):
        if PROFILE_EVERY_S <= 0:
            return None
        st = self.__dict__.setdefault("_prof", {"next": time.monotonic() + PROFILE_EVERY_S, "left": 0, "p": None})
        if st["p"] is None and time.monotonic() >= st["next"]:
            import cProfile
            st["p"], st["left"] = cProfile.Profile(), PROFILE_TICKS
        if st["p"] is not None:
            st["p"].enable()
        return st["p"]

    def _profile_stop(self, prof):
        prof.disable()
        st = self._prof
        st["left"] -= 1
        if st["left"] > 0:
            return
        import io, pstats
        out = io.StringIO()
        pstats.Stats(prof, stream=out).sort_stats("tottime").print_stats(28)
        st["dumps"] = st.get("dumps", 0) + 1
        try:
            prof.dump_stats(f"/tmp/osz-profile-{st['dumps'] % 8}.pstats")
        except OSError:
            pass
        w = self.world
        log.warning("profile over %d ticks, %d survivors, %d zombies, %d corpses, %d drops, %d stashes:\n%s",
                    PROFILE_TICKS, len(w.actors), len(w.zeds), len(w.corpses), len(w.drops), len(w.stashes),
                    out.getvalue()[-6000:])
        st["p"], st["next"] = None, time.monotonic() + PROFILE_EVERY_S

    def _stats_tick(self, took: float):
        """One line every STATS_EVERY_S for whoever runs the server: how busy the loop is and what
        the world holds. Counts only; nothing about any player."""
        st = self.__dict__.setdefault("_stats", {"n": 0, "sum": 0.0, "max": 0.0, "since": time.monotonic()})
        st["n"] += 1; st["sum"] += took; st["max"] = max(st["max"], took)
        if time.monotonic() - st["since"] < STATS_EVERY_S:
            return
        w = self.world
        zeds = {}
        for zid, z in w.zeds.items():
            if z.alive:
                k = zid.split(":", 1)[0]
                zeds[k] = zeds.get(k, 0) + 1
        live = sum(1 for a in w.actors.values() if not a.dead)
        sect = self.__dict__.pop("_sect", {})
        # How many zombies are near enough to someone to be awake: the step's cost follows this, not the total.
        alive_at = [(a.lat, a.lng) for a in w.actors.values() if not a.dead]
        near = sum(1 for z in w.zeds.values() if z.alive and any(
            abs(z.lat - p[0]) < 0.00068 and abs(z.lng - p[1]) < 0.0009 for p in alive_at))
        walking = sum(1 for z in w.zeds.values() if z.alive and z.goal is not None and z.state in ("idle", "investigate"))
        stuck = sum(1 for z in w.zeds.values() if z.alive and z.stuck)
        log.warning("stats: tick mean %.0f ms max %.0f ms over %d ticks; %d connections, %d survivors (%d alive); "
                    "zombies %s; corpses %d; buildings %d; director log %d; ms per tick by part %s; "
                    "zombies within ~75 m of someone %d, wandering %d, stuck %d; held: drops %d, stashes %d, dead zombies %d, homes %d, cells %d, levels %d, memories %d, herds %d",
                    1000 * st["sum"] / max(1, st["n"]), 1000 * st["max"], st["n"], len(self.conns), len(w.actors), live,
                    zeds, len(w.corpses), len(w.buildings.items), len(self.director.log),
                    {k: round(1000 * v / max(1, st["n"]), 1) for k, v in sorted(sect.items())},
                    near, walking, stuck, len(w.drops), len(w.stashes), len(w.dead_until), len(w.homes), len(w.loaded), len(w.levels),
                    len(w.memories), len(w.herds))
        self._stats = {"n": 0, "sum": 0.0, "max": 0.0, "since": time.monotonic()}

    # ---------------------------------------------------------------- joining and leaving
    @serialized
    async def join(self, player, send) -> Conn:
        now = self.clock()
        old = self.conns.get(player.id)
        async with get_sessionmaker()() as s:
            if old is not None and player.id in self.world.actors:     # reconnect to the body in the world
                actor, sid, report = self.world.actors[player.id], old.survivor_id, None
            else:
                actor, row, report = await store.load_or_create(s, player, now)
                sid = row.id
                if report and report.get("turned"):
                    actor.dead = True
                    actor.death = {"cause": "turned", "t": actor.turns_at, "lat": actor.lat, "lng": actor.lng,
                                   "kills": actor.kills, "walked_m": round(actor.walked_m),
                                   "lived_s": round(actor.turns_at - actor.born), "away": True,
                                   "items": [{"code": i["code"], "qty": i["qty"]} for i in actor.items],
                                   "infected": True}
                    await store.save(s, actor, sid, now)
                    body=actor.remains
                    if body:
                        if actor.floor_level:self.world.upper_corpses[body['id']]=copy.deepcopy(body)
                        else:self.world.corpses[body['id']]=copy.deepcopy(body);self.world.corpse_ready.add(body['id'])
                # What this player remembers outlives the life. Load it and add the body with no
                # await in between, so a step can never start a blank memory over a saved one.
                remembered = await s.get(PlayerMemory, player.id)
                if remembered is not None and remembered.state.get("v") == 1 and player.id not in self.world.memories:
                    self.world.memories[player.id] = copy.deepcopy(remembered.state)
                if actor.floor_level:await self._load_level(actor.floor_building,actor.floor_level)
                self.world.add_actor(actor, now)
        async with get_sessionmaker()() as s:await bases.bind(s,self.world,actor)
        if report is not None and not actor.dead:
            candidate=copy.deepcopy(actor)
            report["home"] = home.returning(self.world.for_actor(candidate),candidate)
            if report["home"] and candidate.dirty:
                async with get_sessionmaker()() as s:await store.save(s,candidate,sid,now)
                bases.publish(self.world,candidate);actor=candidate
        actor.connected = True
        actor.events.clear()
        conn = Conn(player.id, sid, send)
        self.conns[player.id] = conn
        await self._touch(player.id, now)
        return conn, actor, report

    def leave(self, player_id: int, conn: Conn):
        if self.conns.get(player_id) is conn:
            conn.gone_at = self.clock()
            a = self.world.actors.get(player_id)
            if a is not None:
                a.connected = False
                a.sprinting = False
                a.quiet = False

    @serialized
    async def new_survivor(self, player, conn: Conn) -> Actor:
        """After a death: a fresh survivor awaiting explicit current-location placement."""
        now = self.clock()
        old = self.world.actors.get(player.id)
        async with get_sessionmaker()() as s:
            if old is not None:
                await store.save(s, old, conn.survivor_id, now)
            self.world.remove_actor(player.id)
            self.director.forget(player.id)
            actor, row, _ = await store.load_or_create(s, player, now)
            conn.survivor_id = row.id
        async with get_sessionmaker()() as s:
            await bases.bind(s,self.world,actor)
        self.world.add_actor(actor, now)
        if actor.home is not None:self.world.homes[bases.owner(actor)]=actor.home
        conn.body_sent = None
        conn.corpse_key = None
        conn.placement_ticket = secrets.token_urlsafe(24)
        conn.launch_placed = False
        conn.placement_receipts = {}
        return actor

    # ---------------------------------------------------------------- the clock
    async def _seed_vehicles(self,a):
        w=self.world
        if a.dead or a.floor_level or not a.placed_at or a.location_loading_until:return
        from app.geo import cell_of
        cell=cell_of(a.lat,a.lng,7)
        if all(f'vehicle:{cell}:{i}' in w.vehicles for i in range(2)):return
        attempts=getattr(w,'vehicle_seed_attempts',None)
        if attempts is None:w.vehicle_seed_attempts={};attempts=w.vehicle_seed_attempts
        if self.clock()-attempts.get(cell,-99)<30:return
        candidates=[v for v in vehicles.seeds(w,a) if v['id'] not in w.vehicles]
        if not candidates:attempts[cell]=self.clock();return
        try:
            async with get_sessionmaker()() as s:
                published=[]
                for v in candidates:
                    row=await s.get(WorldVehicle,v['id'])
                    if row:v=vehicles.restore(row)
                    else:v['_version']=await vehicles.save(s,v)
                    published.append(v)
                await s.commit()
            for v in published:w.vehicles[v['id']]=v
            attempts[cell]=self.clock()
        except Exception:log.exception('parked vehicles were not saved; will retry')

    async def _broadcast_events(self):
        for e in broadcasts.due(self.world):
            try:
                async with get_sessionmaker()() as s:
                    if await s.get(WorldEvent,e['id']):
                        self.world.broadcast_fired.add(e['id']);continue
                    s.add(WorldEvent(id=e['id'],fired_at=e['at']));await s.commit()
                self.world.broadcast_fired.add(e['id'])
                self.world.noise(e['lat'],e['lng'],e['radius'],certain=True)
                for a in self.world.actors.values():
                    if not a.dead and not a.floor_level and survival.dist([a.lat,a.lng],[e['lat'],e['lng']])<=350:
                        self.world._ev(a,'broadcast_sound',kind=e['kind'],b=bearing_deg(a.lat,a.lng,e['lat'],e['lng']))
            except Exception:log.exception('regional event was not committed; retrying within its window')

    async def _save_vehicles(self):
        w=self.world
        ids=list(w.vehicle_dirty)
        if not ids:return
        try:
            async with get_sessionmaker()() as s:
                versions={vid:await vehicles.save(s,w.vehicles[vid]) for vid in ids if vid in w.vehicles}
                await s.commit()
            for vid,version in versions.items():w.vehicles[vid]['_version']=version
            w.vehicle_dirty.difference_update(ids)
        except vehicles.VehicleConflict:
            log.warning('vehicle motion conflicted; reloading durable state')
            for vid in ids:await self._refresh_vehicle(vid)
        except Exception:log.exception('vehicle motion was not saved; will retry')

    async def _vehicle_action(self,conn,args,now):
        w=self.world;a=w.actors.get(conn.player_id);v=w.vehicles.get(args.get('vehicle'))
        if a is None or v is None:return {'ok':False,'why':'vehicle unavailable'}
        if args.get('op')=='drive':return vehicles.control(w,a,v,args,now)
        candidate=copy.deepcopy(a);car=copy.deepcopy(v)
        res=vehicles.action(w,candidate,car,args,now)
        if not res['ok']:return res
        try:
            async with get_sessionmaker()() as s:
                version=await vehicles.save(s,car)
                await store.save(s,candidate,conn.survivor_id,now,commit=False)
                await s.commit()
        except Exception:
            log.exception('vehicle action was not saved')
            await self._refresh_vehicle(v['id'])
            return {'ok':False,'why':'vehicle change was not saved; try again'}
        car['_version']=version;w.vehicles[car['id']]=car;w.vehicle_dirty.discard(car['id'])
        if args.get('op') in ('enter_driver','enter_passenger','exit','engine'):w.vehicle_controls.pop(car['id'],None)
        candidate.dirty=False;bases.publish(w,candidate)
        await self._send_state(conn,candidate,now,force=True)
        return res

    async def _refresh_vehicle(self,vid):
        try:
            async with get_sessionmaker()() as s:row=await s.get(WorldVehicle,vid)
            if row:
                current=vehicles.restore(row);self.world.vehicles[vid]=current
                self.world.vehicle_dirty.discard(vid);self.world.vehicle_controls.pop(vid,None)
                for actor in self.world.actors.values():
                    if actor.vehicle_id==vid and vehicles.seated(actor,current) is None:
                        actor.vehicle_id=None;actor.raw=(actor.lat,actor.lng,1.);actor.dirty=True
                    elif actor.vehicle_id==vid:
                        actor.lat,actor.lng=current['lat'],current['lng'];actor.raw=None;actor.dirty=True
        except Exception:log.exception('vehicle refresh failed; retaining unsaved motion for retry')

    async def _base_action(self,conn,args,now):
        a=self.world.actors.get(conn.player_id)
        if a is None:return {'ok':False,'why':'survivor unavailable'}
        try:
            async with get_sessionmaker()() as s:
                # Flush personal/shared investment before changing the active binding.
                await store.save(s,a,conn.survivor_id,now,commit=False)
                res=await bases.change(s,self.world,a,{**args,'_survivor_id':conn.survivor_id},now)
                if not res['ok']:return res
                await s.commit()
        except Exception:
            log.exception('base membership change was not saved')
            return {'ok':False,'why':'base change was not saved; try again'}
        candidate=res.pop('_candidate',None)
        if candidate:bases.publish(self.world,candidate)
        async with get_sessionmaker()() as s:
            for actor in self.world.actors.values():
                previous=(bases.owner(actor),actor.base_role)
                await bases.bind(s,self.world,actor)
                if previous!=(bases.owner(actor),actor.base_role):
                    if actor.channel and actor.channel.get('kind')=='work':actor.channel=None
                    actor.pending_work=None;study.pause(self.world.for_actor(actor),actor)
        for pid,c in list(self.conns.items()):
            actor=self.world.actors.get(pid)
            if actor and c.gone_at is None:await self._send_state(c,actor,now,force=True)
        return res

    async def _refresh_base(self,a):
        try:
            async with get_sessionmaker()() as s:
                key=bases.owner(a);row=await s.get(PlayerHome,key)
                if row:self.world.homes[key]=copy.deepcopy(row.state)
                for actor in self.world.actors.values():
                    if bases.owner(actor)==key:
                        before=(bases.owner(actor),actor.base_role)
                        await bases.bind(s,self.world,actor)
                        if before!=(bases.owner(actor),actor.base_role):
                            actor.pending_work=None;actor.channel=None;study.pause(self.world.for_actor(actor),actor)
        except Exception:log.exception('could not refresh shared base')

    async def _commit_work(self,conn,a,now):
        w=self.world.for_actor(a);candidate=copy.deepcopy(a)
        ch=candidate.pending_work;candidate.pending_work=None
        trial=copy.copy(w);trial.buildings=w.buildings.local_copy((a.lat,a.lng),radius=12)
        if w._level_key:trial.buildings=copy.deepcopy(w.buildings)
        trial.homes={**w.homes,bases.owner(a):candidate.home}
        level_before=copy.deepcopy(self.world.level_states.get(w._level_key))
        from app.game.buildings import OPENING_STATE
        try:
            survival.finish(trial,candidate,ch)
            async with get_sessionmaker()() as s:
                if w._level_key:await self._save_level(s,trial)
                else:
                    for oid in trial.buildings.dirty:
                        _,opening=trial.buildings.opening(oid)
                        if opening:
                            state={k:copy.deepcopy(opening[k]) for k in OPENING_STATE}
                            row=await s.get(BuildingOpening,oid)
                            if row:row.state=state
                            else:s.add(BuildingOpening(id=oid,state=state))
                await store.save(s,candidate,conn.survivor_id,now,commit=False)
                await s.commit()
        except Exception:
            if w._level_key:
                if level_before is None:self.world.level_states.pop(w._level_key,None)
                else:self.world.level_states[w._level_key]=level_before
            log.exception('shared work was not saved; will retry')
            await self._refresh_base(a)
            return a
        for oid in trial.buildings.dirty:
            _,opening=trial.buildings.opening(oid);_,live=w.buildings.opening(oid)
            if opening and live:live.update({k:copy.deepcopy(opening[k]) for k in OPENING_STATE});w.buildings.dirty.add(oid);w.buildings.revision+=1
        candidate.dirty=False;bases.publish(self.world,candidate)
        return candidate

    @serialized
    async def tick(self):
        now = self.clock()
        w = self.world
        pc = time.perf_counter; sect = self.__dict__.setdefault("_sect", {}); t = pc()
        w.step_parts = sect
        def lap(name):
            nonlocal t
            t2 = pc(); sect[name] = sect.get(name, 0.0) + t2 - t; t = t2
        w.step(now)
        lap("step")
        await self._broadcast_events()
        if now-self._last_vehicle_save>=2:
            await self._save_vehicles();self._last_vehicle_save=now
        self.director.tick()
        await self._flush_corpses()
        lap("director+events+saves")
        # Work results and their world mutations commit before being advertised.
        for pid,conn in list(self.conns.items()):
            a=w.actors.get(pid)
            if a and any(e.get('e')=='work' for e in a.events):
                async with get_sessionmaker()() as s:await store.save(s,a,conn.survivor_id,now)
        for pid, conn in list(self.conns.items()):
            a = w.actors.get(pid)
            if a is None:
                self.conns.pop(pid, None)
                continue
            if conn.gone_at is not None:
                threatened = now - a.last_threat < 3.0 and not a.dead
                if not threatened or now - conn.gone_at > LINKDEAD_S:
                    await self._drop(pid, conn, a)
                continue
            await self._send_state(conn, a, now)
        lap("frames")
        if now - self._last_save > SAVE_EVERY_S:
            self._last_save = now
            await self.save_all()
        lap("save_all")

    async def _commit_learning(self,conn,a,now):
        candidate=copy.deepcopy(a);current=self.world.for_actor(candidate);current.now=now
        told=study.update(current,candidate);candidate.pending_learning=False
        if told:self.world._ev(candidate,'work',message=told)
        try:
            async with get_sessionmaker()() as s:await store.save(s,candidate,conn.survivor_id,now)
        except Exception:
            log.exception('learning completion was not saved; retaining pending reward')
            return a
        candidate.dirty=False;bases.publish(self.world,candidate)
        return candidate

    async def _send_state(self, conn: Conn, a: Actor, now: float, force: bool = False):
        w = self.world
        await self._seed_vehicles(a)
        if a.pending_learning and not a.dead:a=await self._commit_learning(conn,a,now)
        if a.pending_work and not a.dead:
            a=await self._commit_work(conn,a,now)
        if a.pending_window and not a.dead:
            a=await self._commit_window(conn,a,now)
        if a.pending_body_search and not a.dead:
            a = await self._commit_body_search(conn,a,now)
        if a.pending_search and not a.dead:
            candidate = copy.deepcopy(a)
            loot.reveal(candidate, candidate.pending_search)
            try:
                async with get_sessionmaker()() as s:
                    await store.save(s, candidate, conn.survivor_id, now)
            except Exception:
                log.exception('search reveal was not saved; will retry')
            else:
                a = candidate
                w.actors[a.id] = a
                bases.publish(self.world,a)
        tv = time.perf_counter()
        view = w.view(a.id, conn.building_key)
        sect = self.__dict__.setdefault("_sect", {}); sect["frames:view"] = sect.get("frames:view", 0.0) + time.perf_counter() - tv
        hot = bool(view["z"]) or bool(view["herds"]) or bool(view["others"]) or view["you"]["channel"] or a.events or view["you"]["busy"] > 0 or a.speed > 0.2
        if not (hot or force) and now - conn.last_full < 1.0:
            return
        conn.last_full = now
        view.pop('building_revision');key=view.pop('building_key')
        if 'buildings' in view:conn.building_key=key
        key=tuple((b['id'],b['revision'],b['reachable']) for b in view['corpses'])
        if key == conn.corpse_key:view.pop('corpses')
        else:conn.corpse_key=key
        # About 10 kB in the middle of a city, and it rarely changes.
        if view['stashes'] == conn.stashes_sent:view.pop('stashes')
        else:conn.stashes_sent=view['stashes']
        msg = {"t": "s", **view}
        happened = bool(a.events)
        if a.events:
            msg["ev"], a.events = a.events, []
        # Building the body (wounds, pack, home, skills) for everyone five times a second, only to find
        # it unchanged, was the biggest single cost of a tick at 20 players. Anything a player does
        # forces a frame, and anything done to them comes with an event, so both rebuild it at once.
        if force or happened or now - conn.body_at >= BODY_EVERY_S:
            tb = time.perf_counter()
            body = w.body(a)
            conn.body_at = now
            sect["frames:body"] = sect.get("frames:body", 0.0) + time.perf_counter() - tb
            if body != conn.body_sent:
                conn.body_sent = body
                msg["body"] = body
        try:
            await conn.send(msg)
        except Exception:
            self.leave(conn.player_id, conn)

    async def _load_level(self,bid,number):
        key=(bid,number)
        if not number or key in self.world.level_states:return
        async with get_sessionmaker()() as s:
            row=await s.get(BuildingLevel,bid+f':f{number}')
            self.world.level_states[key]=copy.deepcopy(row.state) if row else {}

    async def _save_level(self,s,w):
        if w._level_key is None:return
        key=w._level_key;state=floors.state(w)
        if not state:return
        id=key[0]+f':f{key[1]}'
        row=await s.get(BuildingLevel,id)
        if row is None:s.add(BuildingLevel(id=id,state=state))
        else:row.state=state
        self.world.level_states[key]=copy.deepcopy(state)

    @serialized
    async def act(self, conn: Conn, action: str, args: dict) -> dict:
        w = self.world
        now = self.clock()
        if self.conns.get(conn.player_id) is not conn:
            return {"ok":False,"why":"connection replaced"}
        if action=='vehicle':return await self._vehicle_action(conn,args,now)
        if action=='study':
            a=w.actors.get(conn.player_id)
            if a is None:return {'ok':False,'why':'survivor unavailable'}
            if a.pending_learning:
                a=await self._commit_learning(conn,a,now)
                if a.pending_learning:return {'ok':False,'why':'learning completion is being saved; try again'}
            candidate=copy.deepcopy(a);current=w.for_actor(candidate);current.now=now
            res=study.action(current,candidate,**args)
            if not res['ok']:return res
            try:
                async with get_sessionmaker()() as s:await store.save(s,candidate,conn.survivor_id,now)
            except Exception:
                log.exception('learning start was not saved')
                return {'ok':False,'why':'learning was not saved; try again'}
            bases.publish(w,candidate);await self._send_state(conn,candidate,now,force=True)
            return res
        actor=w.actors.get(conn.player_id)
        if actor and actor.vehicle_id and action in ('home','transfer','loot','body_loot','stairs','route','exit_route','work','window','search','search_body','search_building','pickup','drop','opening','sprint','quiet'):
            return {'ok':False,'why':'exit the vehicle first'}
        if action=='base':return await self._base_action(conn,args,now)
        if action == 'body_loot':
            return await self._take_body(conn,args,now)
        if action=='background':
            from app.game import backgrounds
            a=w.actors.get(conn.player_id)
            if a is None:return {'ok':False,'why':'survivor unavailable'}
            if args.get('life_id')!=a.life_id:return {'ok':False,'why':'background choice belongs to a different survivor life'}
            candidate=copy.deepcopy(a)
            res=backgrounds.choose(candidate,args.get('occupation','generalist'),args.get('trait','balanced'),now)
            if res.get('ok') and not res.get('replay'):
                try:
                    async with get_sessionmaker()() as s:await store.save(s,candidate,conn.survivor_id,now)
                except Exception:
                    log.exception('background was not saved')
                    return {'ok':False,'why':'background was not saved; retry before starting','retry':True}
                w.actors[a.id]=candidate
                bases.publish(self.world,candidate)
                await self._send_state(conn,candidate,now,force=True)
            return res
        if action == 'place':
            if args.get('ticket') != conn.placement_ticket:
                return {'ok': False, 'why': 'location request belongs to an old connection or life'}
            if not get_settings().real_gps:
                a = w.actors.get(conn.player_id)
                if a is None:return {'ok':False,'why':'dead'}
                refused = placement.public_start(a, args, now)
                if refused:return refused
            rid = str(args.get('request', ''))
            if not 8 <= len(rid) <= 80:
                return {'ok': False, 'why': 'missing location request identifier'}
            signature = {k: args.get(k) for k in ('lat','lng','accuracy','timestamp','source','reason')}
            previous = conn.placement_receipts.get(rid)
            if previous:
                return copy.deepcopy(previous[1]) if previous[0] == signature else {'ok':False,'why':'location identifier already used'}
            if args.get('reason') == 'launch' and conn.launch_placed:
                return {'ok':False,'why':'this launch is already placed'}
            a = w.actors.get(conn.player_id)
            if a is None:return {'ok':False,'why':'dead'}
            candidate = copy.deepcopy(a)
            parked=None;parked_version=None
            if candidate.vehicle_id and candidate.vehicle_id in w.vehicles:
                parked=copy.deepcopy(w.vehicles[candidate.vehicle_id]);vehicles.release(candidate,parked)
            res = placement.apply(w, candidate, args, now)
            if res.get('ok'):
                try:
                    async with get_sessionmaker()() as s:
                        if parked:parked_version=await vehicles.save(s,parked)
                        await store.save(s, candidate, conn.survivor_id, now,commit=False)
                        await s.commit()
                except Exception:
                    log.exception('location placement was not saved')
                    return {'ok':False,'why':'location was not saved; try again','retry':True}
                w.actors[a.id] = candidate
                if parked:parked['_version']=parked_version;w.vehicles[parked['id']]=parked;w.vehicle_dirty.discard(parked['id']);w.vehicle_controls.pop(parked['id'],None)
                bases.publish(self.world,candidate)
                if args['reason'] == 'launch':conn.launch_placed = True
                conn.placement_receipts[rid] = (signature, copy.deepcopy(res))
                if len(conn.placement_receipts) > 32:del conn.placement_receipts[next(iter(conn.placement_receipts))]
                await self._send_state(conn, candidate, now, force=True)
            return res
        if action=='stairs':
            a=w.actors.get(conn.player_id)
            if a is None:return {'ok':False,'why':'dead'}
            current=w.for_actor(a);b=current.buildings.containing((a.lat,a.lng))
            target=a.floor_level+(1 if args.get('op','up')=='up' else -1)
            if b and 0<target<floors.count(b):await self._load_level(b.id,target)
            candidate=copy.deepcopy(a);res=floors.stairs(w,candidate,args.get('op','up'))
            if res['ok']:
                try:
                    async with get_sessionmaker()() as session:
                        await self._save_level(session,current)
                        await self._save_level(session,w.for_actor(candidate))
                        await store.save(session,candidate,conn.survivor_id,now)
                except Exception:
                    log.exception('floor transition was not saved')
                    return {'ok':False,'why':'stairs were not saved; try again'}
                w.actors[a.id]=candidate
                await self._send_state(conn,candidate,now,force=True)
            return res
        if action in ("home","transfer", "loot"):
            a=w.actors.get(conn.player_id)
            if a is None:return {"ok":False,"why":"dead"}
            candidate=copy.deepcopy(a)
            active=w.for_actor(a)
            res=loot.take(active,candidate,args) if action == 'loot' else home.action(active,candidate,action,args)
            if res.get("ok"):
                try:
                    async with get_sessionmaker()() as s:
                        await store.save(s,candidate,conn.survivor_id,now)
                except Exception:
                    log.exception("durable home action failed")
                    if a.home and a.home.get('_shared'):await self._refresh_base(a)
                    return {"ok":False,"why":"storage was not saved; try again"}
                w.actors[a.id]=candidate
                bases.publish(self.world,candidate)
                await self._send_state(conn,candidate,now,force=True)
            return res
        if action=='exit_route':
            a=w.actors.get(conn.player_id)
            if a is None or a.dead:return {'ok':False,'why':'dead'}
            active=w.for_actor(a);active._wall_clearance(a)
            geometry=copy.deepcopy(active.buildings) if a.floor_level else w.buildings.local_copy((a.lat,a.lng))
            if a.floor_level:return floors.exit_plan(geometry,(a.lat,a.lng))
            plan=await asyncio.to_thread(geometry.exit_plan,(a.lat,a.lng),{oid for h in w.homes.values() for oid,d in h.get("defenses",{}).items() if d.get("hp",0)>0})
            # Walled in by the neighbours on every side: nobody stays stuck in a building.
            if not plan.get('ok') and plan.get('why')=='no walkable exit for this outline' and w.climb_out(a,checked=True):
                await self._send_state(conn,a,self.clock(),force=True)
                return {'ok':False,'why':'no door leads outside from here, so you climbed out over the roof'}
            return plan
        if action=='route':
            a=w.actors.get(conn.player_id)
            lat,lng=float(args.get('lat',0)),float(args.get('lng',0))
            if a is None or a.dead:return {'ok':False,'why':'dead'}
            if not (math.isfinite(lat) and math.isfinite(lng) and -90<=lat<=90 and -180<=lng<=180):return {'ok':False,'why':'invalid destination'}
            active=w.for_actor(a)
            geometry=copy.deepcopy(active.buildings) if a.floor_level else w.buildings.local_copy((a.lat,a.lng),(lat,lng))
            route=await asyncio.to_thread(geometry.route,(a.lat,a.lng),(lat,lng))
            far=math.hypot((lat-a.lat)*111320,(lng-a.lng)*111320*math.cos(math.radians(a.lat)))>60
            return {'ok':bool(route),'route':route,'why':None if route else ('no clear way there from here; walk closer first' if far else 'open a nearby door or window first')}
        # Bring the world to this instant before judging the action. A full step costs the same however
        # little time has passed, so within ACT_STEP_MIN_S of the last one the world is taken as current:
        # it is the world the player's last frame showed.
        if now - w.now >= ACT_STEP_MIN_S:
            ta = time.perf_counter()
            w.step(now)
            sect = self.__dict__.setdefault("_sect", {}); sect["act_step"] = sect.get("act_step", 0.0) + time.perf_counter() - ta
        res = w.act(conn.player_id, action, **args)
        actor=w.actors.get(conn.player_id)
        if actor and actor.floor_level and res.get('ok'):
            async with get_sessionmaker()() as session:
                await self._save_level(session,w.for_actor(actor))
                await store.save(session,actor,conn.survivor_id,now)
        await self._flush_corpses()
        a = w.actors.get(conn.player_id)
        if a is not None:
            await self._send_state(conn, a, now, force=True)
        return res

    async def _drop(self, pid: int, conn: Conn, a: Actor):
        if a.vehicle_id and a.vehicle_id in self.world.vehicles:
            v=self.world.vehicles[a.vehicle_id];vehicles.release(a,v);self.world.vehicle_dirty.add(v['id'])
        self.conns.pop(pid, None)
        try:
            await self._touch(pid, self.clock())
            async with get_sessionmaker()() as s:
                await store.save(s, a, conn.survivor_id, self.clock())
        except Exception:
            log.exception("save on leave failed")
        self.world.remove_actor(pid)
        self.director.forget(pid)

    async def save_all(self, force: bool = False):
        w = self.world
        await self._save_vehicles()
        await self._flush_corpses()
        try:
            async with get_sessionmaker()() as s:
                for pid, conn in list(self.conns.items()):
                    a = w.actors.get(pid)
                    if a is not None and (a.dirty or force):
                        await store.save(s, a, conn.survivor_id, self.clock())
                for level in w.levels.values():await self._save_level(s,level)
                for pid in list(w.home_dirty):
                    row=await s.get(PlayerHome,pid)
                    if row is not None:
                        active=next((a for a in w.actors.values() if bases.owner(a)==pid),None)
                        if active:await store.save_home(s,active)
                        else:await store.save_home(s,Actor(id=pid,home=w.homes[pid]))
                for pid in list(w.memory_dirty):
                    mem = w.memories.get(pid)
                    if mem is None:continue
                    row = await s.get(PlayerMemory, pid)
                    if row is None:
                        row = PlayerMemory(player_id=pid); s.add(row)
                    row.state = copy.deepcopy(mem)
                await s.commit();w.home_dirty.clear();w.memory_dirty.clear()
                for pid in [p for p in w.memories if p not in w.actors and p not in self.conns]:   # saved and gone: reload on return
                    w.memories.pop(pid, None); w.memory_state.pop(pid, None)
                if w.new_dead:
                    rows = list(w.new_dead)
                    await store.save_dead(s, rows)
                    del w.new_dead[:len(rows)]
                from sqlalchemy import delete
                await s.execute(delete(WorldCorpse).where(WorldCorpse.until <= self.clock()))
                await s.commit()
        except Exception:
            log.exception("save failed")

    async def _flush_corpses(self,w=None):
        if w is None:
            for context in [self.world,*self.world.levels.values()]:await self._flush_corpses(context)
            return
        ids=list(w.corpse_dirty)
        if not ids:return
        bodies=[copy.deepcopy(w.corpses[cid]) for cid in ids if cid in w.corpses]
        dead_rows=list(w.new_dead)
        try:
            async with get_sessionmaker()() as s:
                # A recovery pack and its dead life commit together: no duplicate gear after a crash.
                for body in bodies:
                    if body.get('owner') is not None:
                        if await s.get(WorldCorpse,body['id']) is not None:continue
                        actor=self.world.actors.get(body['owner']);conn=self.conns.get(body['owner'])
                        if not actor or not conn or not actor.dead or not actor.remains or actor.remains['id']!=body['id']:
                            raise RuntimeError('recovery pack has no matching dead life')
                        await store.save(s,actor,conn.survivor_id,self.clock(),commit=False)
                await corpses.save_new(s,bodies,dead_rows,commit=False)
                await s.commit()
                # Another process could already have conserved stock for this ID.
                for body in bodies:
                    row=await s.get(WorldCorpse,body['id'])
                    w.corpses[body['id']]=copy.deepcopy(row.state)
                    w.corpse_ready.add(body['id'])
        except Exception:
            log.exception('bodies were not saved; will retry')
            return
        w.corpse_dirty.difference_update(ids)
        del w.new_dead[:len(dead_rows)]

    async def _commit_window(self,conn,a,now):
        from app.game import windows
        from app.game.buildings import OPENING_STATE
        w=self.world.for_actor(a);candidate=copy.deepcopy(a);ch=candidate.pending_window
        # Keep geometry private until cloth, tool wear and opening state commit together.
        trial=copy.copy(w);trial.buildings=w.buildings.local_copy((a.lat,a.lng),radius=8)
        _,o=trial.buildings.opening(ch['opening'])
        level_key=w._level_key;level_before=copy.deepcopy(self.world.level_states.get(level_key))
        try:
            changed=windows.finish(trial,candidate,ch)
            async with get_sessionmaker()() as s:
                if changed:
                    if level_key:await self._save_level(s,trial)
                    else:
                        row=await s.get(BuildingOpening,o['id'])
                        state={k:copy.deepcopy(o[k]) for k in OPENING_STATE}
                        if row is None:s.add(BuildingOpening(id=o['id'],state=state))
                        else:row.state=state
                await store.save(s,candidate,conn.survivor_id,now,commit=False)
                await s.commit()
        except Exception:
            if level_key:
                if level_before is None:self.world.level_states.pop(level_key,None)
                else:self.world.level_states[level_key]=level_before
            log.exception('window work was not saved; will retry')
            return a
        if changed:
            _,published=w.buildings.opening(o['id'])
            if published:
                published.update({k:copy.deepcopy(o[k]) for k in OPENING_STATE})
                w.buildings.dirty.add(o['id']);w.buildings.revision+=1
        candidate.dirty=False;self.world.actors[a.id]=candidate
        if w is not self.world:w.actors[a.id]=candidate
        bases.publish(self.world,candidate)
        return candidate

    async def _commit_body_search(self,conn,a,now):
        cid=a.pending_body_search
        active=self.world.for_actor(a);body=active.corpses.get(cid)
        if not body or not corpses.reachable(active,a,body):
            a.pending_body_search=None
            a.events.append({'e':'interrupted','what':'search_body'})
            return a
        candidate=copy.deepcopy(a)
        try:
            async with get_sessionmaker()() as s:
                row=await s.get(WorldCorpse,cid)
                if not row or row.until <= now:
                    a.pending_body_search=None;return a
                body=copy.deepcopy(row.state);expected=row.revision
                corpses.reveal(candidate,body)
                if body['revision'] != expected and not await corpses.update_stock(s,body,expected):
                    await s.rollback();return a
                await store.save(s,candidate,conn.survivor_id,now,commit=False)
                await s.commit()
        except Exception:
            log.exception('body search was not saved; will retry')
            return a
        candidate.dirty=False
        active.corpses[cid]=body;self.world.actors[a.id]=candidate
        bases.publish(self.world,candidate)
        return candidate

    async def _take_body(self,conn,args,now):
        a=self.world.actors.get(conn.player_id)
        w=self.world.for_actor(a) if a is not None else self.world
        if a is None:return {'ok':False,'why':'dead'}
        candidate=copy.deepcopy(a);cid=args.get('corpse');committed=False
        try:
            async with get_sessionmaker()() as s:
                row=await s.get(WorldCorpse,cid) if cid else None
                body=copy.deepcopy(row.state) if row and row.until > now else None
                if body:w.corpses[cid]=copy.deepcopy(body);w.corpse_ready.add(cid)
                expected=body['revision'] if body else None
                res=corpses.take(w,candidate,body,args)
                # An identical receipt replay already committed; it changes nothing.
                if res['ok'] and body and body['revision'] != expected:
                    if not await corpses.update_stock(s,body,expected):
                        await s.rollback()
                        row=await s.get(WorldCorpse,cid,populate_existing=True)
                        if row:w.corpses[cid]=copy.deepcopy(row.state)
                        res={'ok':False,'why':'body changed; try again'}
                    else:
                        await store.save(s,candidate,conn.survivor_id,now,commit=False)
                        await s.commit()
                        committed=True
        except Exception:
            log.exception('body transfer was not saved')
            return {'ok':False,'why':'loot was not saved; try again'}
        if not res['ok']:
            await self._send_state(conn,a,now,force=True)
            return res
        if committed:candidate.dirty=False
        self.world.actors[a.id]=candidate;w.actors[a.id]=candidate
        if body:w.corpses[cid]=body
        bases.publish(self.world,candidate)
        await self._send_state(conn,candidate,now,force=True)
        return res


_hub: Hub | None = None


def get_hub() -> Hub:
    global _hub
    if _hub is None:
        from app.config import get_settings
        cfg = get_settings()
        d = difficulty_profiles.resolve(cfg.difficulty, cfg.difficulty_tune)
        if cfg.zed_density is not None:
            d["density"] = cfg.zed_density
        log.warning("difficulty: %s (%s)", cfg.difficulty, difficulty_profiles.describe(d))
        _hub = Hub(difficulty=d)
        if _hub.world.named_starts:
            from app.game.building_loader import start_regions
            _hub.building_loader.pinned = start_regions()
    return _hub


def reset_hub():
    global _hub
    _hub = None
