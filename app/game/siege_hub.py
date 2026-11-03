"""Runs every siege: each one a solo SiegeRun with its own small world, stepped five times a second on
its own loop beside the survival hub. Frames are survival frames plus a `siege` block, so the client
draws them with the code it already has. Design: ~/osz-stack/SIEGE.md."""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import random
import time

from app.game import siege
from app.game.content import ITEMS

log = logging.getLogger("osz.siege")
TICK_S = 0.2
STATS_EVERY_S = 60.0
BODY_EVERY_S = 1.0
KEEP_OVER_S = 120.0            # an ended run's card stays this long for a reconnecting client
# How many sieges this machine runs at once. Measured (SIEGE.md, DEVLOG 2026-11-03); each also takes a
# place under MAX_PLAYERS.
MAX_SIEGES = int(os.environ.get("OSZ_MAX_SIEGES", "8") or 8)
# Load tests only: start every new siege this many seconds in, to measure the heaviest minutes. Never set
# on a server people play on.
START_S = float(os.environ.get("OSZ_SIEGE_START_S", "0") or 0)


class Session:
    def __init__(self, run, send):
        self.run, self.send = run, send
        self.building_key = None
        self.body_sent = None
        self.body_at = 0.0
        self.corpse_key = None
        self.over_at = None
        self.delivered = None
        self.kick = None
        self.wall = time.time()


class SiegeHub:
    def __init__(self, main_hub):
        self.main = main_hub
        self.sessions: dict[int, Session] = {}
        self._records = None
        self._task = None
        self._seq = 0
        self._stats = {"n": 0, "sum": 0.0, "max": 0.0, "since": time.monotonic()}

    # ------------------------------------------------------------------ the arena's map
    def records(self):
        """The plaza's buildings, copied from the survival world, which keeps the start cities loaded."""
        if self._records is None:
            w = self.main.world
            out = []
            for b in list(w.buildings.items.values()):
                outline = getattr(b, "outline", None)
                if not outline:
                    continue
                rec = {"id": b.id, "outline": [list(p) for p in outline], "name": getattr(b, "name", None),
                       "source": getattr(b, "source", None), "type": getattr(b, "type", None)}
                out.append(rec)
            near = siege.near_records(out)
            if near:
                self._records = near
            return near
        return self._records

    # ------------------------------------------------------------------ joining and leaving
    def playing(self) -> int:
        return sum(1 for s in self.sessions.values() if not s.run.over)

    def full(self) -> str | None:
        if self.playing() >= MAX_SIEGES:
            return f"All {MAX_SIEGES} siege places are taken right now. Try again in a minute, or play survival."
        return None

    def join(self, player, send) -> Session:
        old = self.sessions.get(player.id)
        if old is not None and not old.run.over:
            old.send = send                              # a reconnect picks the same run up
            old.building_key = None; old.body_sent = None; old.corpse_key = None
            return old
        self._seq += 1
        run = siege.SiegeRun(player.id, player.name, self.records() or [], seed=random.getrandbits(32),
                             wall=time.time(), run_id=self._seq, start_t=START_S)
        s = Session(run, send)
        self.sessions[player.id] = s
        log.warning("siege started: run %d, %d running", self._seq, self.playing())
        return s

    async def leave(self, pid: int, session: Session):
        if self.sessions.get(pid) is not session:
            return
        run = session.run
        if not run.over:
            run.leave()
        await self._finish(session)
        self.sessions.pop(pid, None)

    # ------------------------------------------------------------------ actions
    def act(self, session: Session, a: str, args: dict) -> dict:
        run = session.run
        if run.over:
            return {"ok": False, "why": "the siege is over"}
        if a == "siege_pick":
            return run.pick(args.get("pick"))
        if run.choice is not None:
            return {"ok": False, "why": "choose an upgrade first"}
        if a == "route":                                  # an open plaza: walk straight, held inside it
            if "lat" not in args or "lng" not in args:
                return {"ok": False, "why": "where to?"}
            return {"ok": True, "route": [list(run.clamp(args["lat"], args["lng"]))]}
        return run.world.act(run.actor.id, a, **args)

    def position(self, session: Session, lat: float, lng: float, acc: float):
        run = session.run
        if run.over or run.choice is not None:
            return
        lat, lng = run.clamp(lat, lng)
        run.world.set_position(run.actor.id, lat, lng, acc)

    # ------------------------------------------------------------------ the loop
    async def start(self):
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
        for pid, s in list(self.sessions.items()):
            await self.leave(pid, s)

    async def _loop(self):
        last = time.monotonic()
        while True:
            t0 = time.perf_counter()
            now = time.monotonic(); dt = now - last; last = now
            try:
                await self.tick(dt)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("siege tick failed")
            took = time.perf_counter() - t0
            self._stat(took)
            await asyncio.sleep(max(0.01, TICK_S - took))

    async def tick(self, dt: float):
        wall = time.time()
        for pid, s in list(self.sessions.items()):
            run = s.run
            run._wall = wall
            run.open_choice(wall)
            was_over = bool(run.over)
            run.step(dt, wall)
            if run.over and not was_over:
                await self._finish(s)
            if run.over and s.over_at and wall - s.over_at > KEEP_OVER_S:
                self.sessions.pop(pid, None)
                continue
            try:
                await s.send(self.frame(s))
            except Exception:
                if s.kick:
                    s.kick()

    def frame(self, s: Session) -> dict:
        run = s.run; w = run.world; a = run.actor
        view = w.view(a.id, s.building_key)
        view.pop("building_revision", None)
        key = view.pop("building_key", None)
        if "buildings" in view:
            s.building_key = key
        ck = tuple((b["id"], b["revision"], b["reachable"]) for b in view.get("corpses", []))
        if ck == s.corpse_key:
            view.pop("corpses", None)
        else:
            s.corpse_key = ck
        # Rooms nearby still hold survival's loot tables; the siege's finds come from chests only.
        view["stashes"] = []; view["loot"] = []
        msg = {"t": "s", **view, "siege": run.info()}
        if s.delivered is not None:
            msg["siege"]["delivered"] = s.delivered
        events = a.events
        if events:
            msg["ev"], a.events = events, []
        now = time.time()
        if events or now - s.body_at >= BODY_EVERY_S:
            body = w.body(a); s.body_at = now
            if body != s.body_sent:
                s.body_sent = body; msg["body"] = body
        return msg

    def _stat(self, took):
        st = self._stats
        st["n"] += 1; st["sum"] += took; st["max"] = max(st["max"], took)
        if time.monotonic() - st["since"] < STATS_EVERY_S or not self.sessions:
            if time.monotonic() - st["since"] >= STATS_EVERY_S:
                self._stats = {"n": 0, "sum": 0.0, "max": 0.0, "since": time.monotonic()}
            return
        zeds = sum(sum(1 for z in s.run.world.zeds.values() if z.alive) for s in self.sessions.values())
        log.warning("siege stats: tick mean %.0f ms max %.0f ms over %d ticks; %d sieges running, %d zombies",
                    1000 * st["sum"] / max(1, st["n"]), 1000 * st["max"], st["n"], self.playing(), zeds)
        self._stats = {"n": 0, "sum": 0.0, "max": 0.0, "since": time.monotonic()}

    # ------------------------------------------------------------------ the haul goes home
    async def _finish(self, s: Session):
        if s.over_at is not None:
            return
        s.over_at = time.time()
        run = s.run
        o = run.over or {}
        s.delivered = await self.deliver(run.player_id, o.get("haul", []))
        log.warning("siege over: run result %s at %.0f s, score %d, %d sieges running",
                    o.get("result"), o.get("t", 0), o.get("score", 0), self.playing())

    async def deliver(self, pid: int, haul: list) -> dict:
        """Into the personal home's cupboard, as far as its capacity allows. Minimal on purpose (v0)."""
        if not haul:
            return {"home": None, "items": [], "left": []}
        hub = self.main
        async with hub.state_lock:
            w = hub.world
            a = w.actors.get(pid)
            home = a.home if (a is not None and a.home is not None and (a.home_owner or a.id) == pid) else w.homes.get(pid)
            if home is None or home.get("_shared") or "items" not in home:
                return {"home": None, "items": [], "left": copy.deepcopy(haul)}
            weight = sum(ITEMS[i["code"]]["w"] * i["qty"] for i in home["items"])
            got, left = [], []
            for row in haul:
                fit = row["qty"]
                while fit and weight + ITEMS[row["code"]]["w"] * fit > home.get("capacity", 40.0) + 1e-6:
                    fit -= 1
                if fit:
                    cond = ITEMS[row["code"]].get("cond")
                    same = next((i for i in home["items"] if i["code"] == row["code"] and i.get("cond") == cond
                                 and "stack" in ITEMS[row["code"]]), None)
                    if same:
                        same["qty"] += fit
                    else:
                        home["items"].append({"id": home.get("next_item", 1), "code": row["code"], "qty": fit, "cond": cond})
                        home["next_item"] = home.get("next_item", 1) + 1
                    weight += ITEMS[row["code"]]["w"] * fit
                    got.append({"code": row["code"], "qty": fit})
                if fit < row["qty"]:
                    left.append({"code": row["code"], "qty": row["qty"] - fit})
            if got:
                home["revision"] = home.get("revision", 0) + 1
                w.homes[pid] = home
                w.home_dirty.add(pid)
                if a is not None:
                    a.dirty = True
        return {"home": home.get("name") or "home", "items": got, "left": left}


_siege_hub: SiegeHub | None = None


def get_siege_hub() -> SiegeHub:
    global _siege_hub
    if _siege_hub is None:
        from app.game.hub import get_hub
        _siege_hub = SiegeHub(get_hub())
    return _siege_hub
