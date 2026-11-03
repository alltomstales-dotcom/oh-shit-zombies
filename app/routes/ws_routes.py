"""The realtime socket. Messages are small JSON objects with a one-letter type `t`."""
from __future__ import annotations

import asyncio
import logging
import math
from collections import Counter

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth import verify_token
from app.db import get_sessionmaker
from app.config import get_settings
from app.game.content import ITEMS, TUNE
from app.game.backgrounds import catalog as background_catalog
from app.game.hub import get_hub
from app.models import Player
from app.ratelimit import RateLimiter, client_ip

log = logging.getLogger("osz.ws")
router = APIRouter()

ACTIONS = {"radio", "vehicle", "base", "background", "window", "stairs", "place", "loot", "body_loot", "search_body", "drop", "scream", "swing", "shove", "shoot", "back", "bandage", "disinfect", "use", "search", "pickup",
           "equip", "cancel", "opening", "route", "exit_route", "sprint", "quiet", "memory", "pin", "search_building", "wear", "home", "transfer", "work", "light", "study"}
ARGS = {"pick":int,"start":str,"lesson":str,"vehicle":str,"east":float,"north":float,"throttle":float,"invite":str,"role":str,"member":int,"owner":int,"life_id":int,"occupation":str,"trait":str,"corpse": str, "ticket": str, "source": str, "reason": str, "accuracy": float, "timestamp": float, "target": str, "wound": int, "code": str, "stash": str, "drop": str, "item": int, "opening": str, "op": str, "lat": float, "lng": float, "slot": str, "name": str, "qty": int, "revision": int, "request": str, "object": str, "recipe": str, "rotation": int, "container": str, "kind": str, "pin": str}
CLIENT_TUNE = ("quiet_speed", "lunge_range_m", "swing_reach_m", "finish_reach_m", "stash_reach_m", "pickup_m",
               "gun_range_m", "carry_max", "bandage_s", "search_s", "back_cost", "shove_cost")


MAX_ARG_CHARS = 200
MAX_ARG_INT = 10 ** 9
OUTBOX = 40                 # about eight seconds of snapshots; a client this far behind is not reading
SEND_TIMEOUT_S = 15.0
ACT_LIMIT, ROUTE_LIMIT = (40, 5), (12, 5)
FLOOD_DROPS = 400           # dropped messages in one connection before it is closed
_ip_conns: Counter = Counter()


def _args(msg: dict) -> dict:
    """Typed, bounded action arguments. NaN or a huge string must not reach saved state."""
    out = {}
    for k, cast in ARGS.items():
        v = msg.get(k)
        if v is None:
            continue
        v = cast(v)
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("non-finite number")
        if isinstance(v, int) and abs(v) > MAX_ARG_INT:
            raise ValueError("number out of range")
        if isinstance(v, str) and len(v) > MAX_ARG_CHARS:
            raise ValueError("text too long")
        out[k] = v
    return out


def _hello(player, actor, hub, conn) -> dict:
    cfg = get_settings()
    return {"t": "hello", "name": player.name, "born": actor.born, "life_id":actor.life_id,"now": hub.clock(), "placement_ticket": conn.placement_ticket,
            "placement_epoch": actor.placement_epoch, "unplaced": actor.lat == 0 and actor.lng == 0,
            "tune": {k: TUNE[k] for k in CLIENT_TUNE},
            "items": {k: {p: v[p] for p in ("name","kind","w","slot","cond","covers","scratch","bite","pace","capacity","perishable","hunger","thirst","description","teaches") if p in v} for k,v in ITEMS.items()},
            "backgrounds":background_catalog(),
            "tiles": {"url": cfg.tile_url, "max_z": cfg.tile_max_z, "dark": cfg.tile_dark,
                      "credit": cfg.tile_credit}}


def _coord(d: dict) -> tuple[float, float, float]:
    lat, lng = float(d["lat"]), float(d["lng"])
    acc = float(d.get("acc", 10.0) or 10.0)
    if not (math.isfinite(lat) and math.isfinite(lng) and math.isfinite(acc)):
        raise ValueError("non-finite coordinate")
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        raise ValueError("coordinate out of range")
    return lat, lng, max(1.0, min(100.0, acc))


FULL_RETRY_S = 30      # the "server full" screen tries again by itself after this long


def full_message(cfg, from_ip: int, playing: int, already_in: bool):
    """None if this connection may play, else the "server full" message the client shows.
    Someone already in (a reconnect) is never turned away by the cap."""
    if from_ip >= cfg.max_conns_per_ip:
        why = "Too many players from your connection. Close another tab and try again."
    elif not already_in and playing >= cfg.max_players:
        why = f"All {cfg.max_players} places are taken right now. A place frees up whenever someone leaves."
    else:
        return None
    return {"t": "full", "max": cfg.max_players, "retry_s": FULL_RETRY_S, "why": why}


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, token: str = ""):
    async with get_sessionmaker()() as s:
        pid = await verify_token(s, token)
        player = await s.get(Player, pid) if pid is not None else None
    if player is None:
        await websocket.close(code=4401)
        return
    cfg = get_settings()
    await websocket.accept()
    hub = get_hub()
    ip = client_ip(websocket.headers, websocket.client, cfg.trust_proxy)
    refusal = full_message(cfg, _ip_conns[ip], len(hub.conns), player.id in hub.conns)
    if refusal:
        await websocket.send_json(refusal)
        await websocket.close(code=4503)
        return
    _ip_conns[ip] += 1
    # The game loop sends to everybody while holding the world lock, so it must never wait on one
    # phone. It drops messages in a box; this task writes them out; a client that stops reading is cut.
    outbox: asyncio.Queue = asyncio.Queue(maxsize=OUTBOX)
    reader = asyncio.current_task()
    closing = False

    def kick():
        nonlocal closing
        if not closing:
            closing = True
            reader.cancel()

    async def writer():
        try:
            while True:
                msg = await outbox.get()
                await asyncio.wait_for(websocket.send_json(msg), SEND_TIMEOUT_S)
        except asyncio.CancelledError:
            raise
        except Exception:
            kick()

    async def send(msg: dict):
        try:
            outbox.put_nowait(msg)
        except asyncio.QueueFull:
            kick()
            raise ConnectionError("client stopped reading")

    writing = asyncio.create_task(writer())
    conn = None
    limiter, acts, routes = RateLimiter(limit=80, window_s=5), RateLimiter(*ACT_LIMIT), RateLimiter(*ROUTE_LIMIT)
    drops = 0
    try:
        conn, actor, report = await hub.join(player, send)
        conn.kick = kick
        await send({**_hello(player, actor, hub, conn), "away": report, "dead": actor.dead,
                    "card": actor.death if actor.dead else None})
        while True:
            msg = await websocket.receive_json()
            if not isinstance(msg, dict):
                continue
            if not limiter.allow("ws"):
                drops += 1
                if drops > FLOOD_DROPS:
                    break
                continue
            t = msg.get("t")
            try:
                if t == "pos":
                    lat, lng, acc = _coord(msg)
                    async with hub.state_lock:
                        actor = hub.world.actors.get(player.id)
                        # With no real GPS a survivor only gets onto the map through a named start.
                        if not cfg.real_gps and actor and actor.lat == 0 and actor.lng == 0:
                            continue
                        if hub.conns.get(player.id) is conn and actor and msg.get('placement_epoch', actor.placement_epoch) == actor.placement_epoch and msg.get('floor_epoch',0)==actor.floor_epoch:
                            hub.world.set_position(player.id, lat, lng, acc, mode="gps" if cfg.real_gps and msg.get("mode") == "gps" else "desk")
                elif t == "act":
                    a = str(msg.get("a", ""))
                    if a not in ACTIONS:
                        await send({"t": "r", "id": msg.get("id"), "ok": False, "why": "unknown"})
                        continue
                    # Steering is cheap and frequent; a route costs a path search off the loop.
                    busy = a != "vehicle" and not acts.allow("act")
                    if not busy and a in ("route", "exit_route"):
                        busy = not routes.allow("route")
                    if busy:
                        await send({"t": "r", "id": msg.get("id"), "a": a, "ok": False, "why": "slow down"})
                        continue
                    res = await hub.act(conn, a, _args(msg))
                    await send({"t": "r", "id": msg.get("id"), "a": a, **res})
                elif t == "ping":
                    await send({"t": "pong", "c": msg.get("c"), "now": hub.clock()})
                elif t == "new":
                    if hub.conns.get(player.id) is not conn:continue
                    a = hub.world.actors.get(player.id)
                    if a is None or a.dead:
                        actor = await hub.new_survivor(player, conn)
                        await send({**_hello(player, actor, hub, conn), "fresh": True, "dead": False})
            except (KeyError, ValueError, TypeError, OverflowError) as e:
                await send({"t": "err", "why": f"bad message: {e}"})
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        if not closing:
            raise
        reader.uncancel()
    except (ConnectionError, ValueError):
        pass                    # a client that stopped reading, or one sending junk: nothing to log
    except Exception:
        log.exception("ws loop crashed")
    finally:
        writing.cancel()
        _ip_conns[ip] -= 1
        if _ip_conns[ip] <= 0:
            del _ip_conns[ip]
        if conn is not None:
            hub.leave(player.id, conn)
        if closing:
            try:
                await asyncio.wait_for(websocket.close(code=4408), 1.0)
            except Exception:
                pass


# ---------------------------------------------------------------------------------------- siege
SIEGE_ACTIONS = {"swing", "shove", "back", "bandage", "disinfect", "sprint", "cancel", "scream", "use", "equip", "pickup", "route", "siege_pick"}


@router.websocket("/ws/siege")
async def ws_siege(websocket: WebSocket, token: str = ""):
    """Siege: survive 30 minutes. Same login, same frame format plus a `siege` block (siege_hub.py)."""
    from app.game.siege_hub import get_siege_hub
    async with get_sessionmaker()() as s:
        pid = await verify_token(s, token)
        player = await s.get(Player, pid) if pid is not None else None
    if player is None:
        await websocket.close(code=4401)
        return
    cfg = get_settings()
    await websocket.accept()
    hub, sieges = get_hub(), get_siege_hub()
    ip = client_ip(websocket.headers, websocket.client, cfg.trust_proxy)
    again = player.id in sieges.sessions and not sieges.sessions[player.id].run.over
    refusal = full_message(cfg, _ip_conns[ip], len(hub.conns) + sieges.playing(), again)
    if refusal is None and not again and sieges.full():
        refusal = {"t": "full", "max": cfg.max_players, "retry_s": FULL_RETRY_S, "why": sieges.full()}
    if refusal is None and player.id in hub.conns:
        refusal = {"t": "full", "max": cfg.max_players, "retry_s": 5, "why": "Your survivor is still out in the street. Try again in a few seconds."}
    if refusal:
        await websocket.send_json(refusal)
        await websocket.close(code=4503)
        return
    _ip_conns[ip] += 1
    outbox: asyncio.Queue = asyncio.Queue(maxsize=OUTBOX)
    reader = asyncio.current_task()
    closing = False

    def kick():
        nonlocal closing
        if not closing:
            closing = True
            reader.cancel()

    async def writer():
        try:
            while True:
                msg = await outbox.get()
                await asyncio.wait_for(websocket.send_json(msg), SEND_TIMEOUT_S)
        except asyncio.CancelledError:
            raise
        except Exception:
            kick()

    async def send(msg: dict):
        try:
            outbox.put_nowait(msg)
        except asyncio.QueueFull:
            kick()
            raise ConnectionError("client stopped reading")

    writing = asyncio.create_task(writer())
    session = None
    limiter, acts = RateLimiter(limit=80, window_s=5), RateLimiter(*ACT_LIMIT)
    drops = 0
    try:
        session = sieges.join(player, send)
        session.kick = kick
        run = session.run
        await send({"t": "hello", "siege": True, "name": player.name, "born": run.actor.born, "life_id": run.actor.life_id,
                    "now": run.world.now, "placement_ticket": None, "placement_epoch": run.actor.placement_epoch,
                    "unplaced": False, "dead": False, "fresh": True,
                    "tune": {k: run.world.T[k] for k in CLIENT_TUNE},
                    "items": {k: {p: v[p] for p in ("name","kind","w","slot","cond","covers","scratch","bite","pace","capacity","perishable","hunger","thirst","description","teaches") if p in v} for k,v in ITEMS.items()},
                    "backgrounds": background_catalog(),
                    "tiles": {"url": cfg.tile_url, "max_z": cfg.tile_max_z, "dark": cfg.tile_dark, "credit": cfg.tile_credit}})
        while True:
            msg = await websocket.receive_json()
            if not isinstance(msg, dict):
                continue
            if not limiter.allow("ws"):
                drops += 1
                if drops > FLOOD_DROPS:
                    break
                continue
            t = msg.get("t")
            try:
                if t == "pos":
                    lat, lng, acc = _coord(msg)
                    sieges.position(session, lat, lng, acc)
                elif t == "act":
                    a = str(msg.get("a", ""))
                    if a not in SIEGE_ACTIONS:
                        await send({"t": "r", "id": msg.get("id"), "a": a, "ok": False, "why": "not in a siege"})
                        continue
                    if not acts.allow("act"):
                        await send({"t": "r", "id": msg.get("id"), "a": a, "ok": False, "why": "slow down"})
                        continue
                    res = sieges.act(session, a, _args(msg))
                    await send({"t": "r", "id": msg.get("id"), "a": a, **res})
                elif t == "ping":
                    await send({"t": "pong", "c": msg.get("c"), "now": session.run.world.now})
                elif t == "leave":
                    break
            except (KeyError, ValueError, TypeError, OverflowError) as e:
                await send({"t": "err", "why": f"bad message: {e}"})
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        if not closing:
            raise
        reader.uncancel()
    except (ConnectionError, ValueError):
        pass
    except Exception:
        log.exception("siege ws loop crashed")
    finally:
        writing.cancel()
        _ip_conns[ip] -= 1
        if _ip_conns[ip] <= 0:
            del _ip_conns[ip]
        if session is not None:
            await sieges.leave(player.id, session)
        if closing:
            try:
                await asyncio.wait_for(websocket.close(code=4408), 1.0)
            except Exception:
                pass
