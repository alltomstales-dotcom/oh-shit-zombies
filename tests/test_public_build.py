"""The public defaults: no real location, no typed text, bounded input, deleting a player."""
import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings, get_settings
from app.auth import create_anonymous_player, verify_token, hash_token
from app.game import hub as hubmod, placement
from app.game.starts import STARTS
from app.models import Player, PlayerHome, PlayerMemory, SessionToken, Survivor
from app.ratelimit import RateLimiter, client_ip
from app.routes.ws_routes import _args


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setenv("REAL_GPS", "0")
    monkeypatch.setenv("FREE_TEXT", "0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_are_private(monkeypatch):
    for k in ("REAL_GPS", "FREE_TEXT"):
        monkeypatch.delenv(k, raising=False)
    s = Settings(_env_file=None)
    assert s.real_gps is False and s.free_text is False


async def test_names_are_generated_and_tokens_hashed(public, maker):
    async with maker() as s:
        out = await create_anonymous_player(s, "d" * 32, "My Real Name")
        assert out["player"].name != "My Real Name"
        again = await create_anonymous_player(s, "d" * 32, "Another Name")
        assert again["player"].name == out["player"].name
        stored = (await s.execute(select(SessionToken.token))).scalars().all()
        assert out["token"] not in stored and hash_token(out["token"]) in stored
        assert await verify_token(s, out["token"]) == out["player"].id


async def test_session_rows_do_not_grow(public, maker):
    async with maker() as s:
        for _ in range(9):
            await create_anonymous_player(s, "e" * 32, "x")
        assert len((await s.execute(select(SessionToken.token))).scalars().all()) <= 4


class _A:
    id = 7
    life_id = 1
    lat = 0.0
    lng = 0.0


def test_public_start_replaces_any_coordinates():
    args = {"start": STARTS[0]["id"], "reason": "launch", "lat": 1.0, "lng": 2.0, "source": "gps"}
    assert placement.public_start(_A(), args, 1000.0) is None
    assert args["source"] == "manual"
    assert abs(args["lat"] - STARTS[0]["lat"]) < .001 and abs(args["lng"] - STARTS[0]["lng"]) < .001


def test_public_start_refuses_other_places_and_placed_survivors():
    assert placement.public_start(_A(), {"reason": "launch", "start": "my-house"}, 1.)["ok"] is False
    assert placement.public_start(_A(), {"reason": "travel", "start": STARTS[0]["id"]}, 1.)["ok"] is False
    placed = _A()
    placed.lat = 41.0
    assert placement.public_start(placed, {"reason": "launch", "start": STARTS[0]["id"]}, 1.)["ok"] is False


def _pos_in_world(hub, pid, lat, lng):
    a = hub.world.actors[pid]
    hub.world.set_position(pid, lat, lng, 1.0, mode="desk")
    hub.world.step(hub.clock() + .2)
    return a


async def test_no_gps_anchor_and_no_teleport(public, maker):
    h = hubmod.get_hub()
    async with maker() as s:
        p = (await create_anonymous_player(s, "f" * 32, "x"))["player"]
    sent = []

    async def send(m):
        sent.append(m)
    conn, actor, _ = await h.join(p, send)
    res = await h.act(conn, "place", {"start": "chicago", "reason": "launch", "lat": 10.0, "lng": 10.0, "accuracy": 5.0,
                                      "timestamp": time.time() * 1000, "source": "gps", "ticket": conn.placement_ticket,
                                      "request": "abcdefgh12345678"})
    assert res["ok"] and res["anchor"] is None
    a = h.world.actors[p.id]
    assert a.gps_anchor is None and abs(a.lat - 41.88) < .01
    before = (a.lat, a.lng)
    a.transit_until = 0
    a = _pos_in_world(h, p.id, 48.85, 2.35)       # Paris, in one message
    assert abs(a.lat - before[0]) < .01 and abs(a.lng - before[1]) < .01


def test_args_reject_non_finite_and_oversize():
    for bad in ({"east": float("nan")}, {"north": float("inf")}, {"ticket": "x" * 500}, {"qty": 10 ** 12}):
        with pytest.raises(ValueError):
            _args(bad)
    with pytest.raises(OverflowError):
        _args({"qty": float("inf")})
    assert _args({"east": 1.0, "qty": 3}) == {"east": 1.0, "qty": 3}


def test_limiter_forgets_idle_keys():
    r = RateLimiter(limit=2, window_s=10)
    for i in range(1000):
        r.allow(f"ip{i}", now=0.0)
    r.allow("later", now=100.0)
    assert len(r._hits) == 1


def test_forwarding_header_only_believed_from_the_named_proxy():
    class C:
        host = "10.0.0.1"
    h = {"cf-connecting-ip": "1.1.1.1", "x-real-ip": "2.2.2.2"}
    assert client_ip(h, C, "none") == "10.0.0.1"
    assert client_ip(h, C, "cloudflare") == "1.1.1.1"
    assert client_ip(h, C, "railway") == "2.2.2.2"


async def test_forget_player_removes_everything(public, maker):
    h = hubmod.get_hub()
    async with maker() as s:
        p = (await create_anonymous_player(s, "g" * 32, "x"))["player"]
        s.add(PlayerMemory(player_id=p.id, state={"v": 1, "cells": {}, "marks": {}, "death": None}))
        s.add(PlayerHome(player_id=p.id, state={"name": "x"}))
        await s.commit()

    async def send(m):
        pass
    conn, _, _ = await h.join(p, send)
    await h.forget_player(p.id)
    assert p.id not in h.conns and p.id not in h.world.actors
    async with maker() as s:
        for model, col in ((Player, Player.id), (Survivor, Survivor.player_id), (PlayerHome, PlayerHome.player_id),
                           (PlayerMemory, PlayerMemory.player_id), (SessionToken, SessionToken.player_id)):
            assert (await s.execute(select(model).where(col == p.id))).first() is None


async def test_retention_deletes_only_the_long_gone(public, maker):
    h = hubmod.get_hub()
    async with maker() as s:
        old = (await create_anonymous_player(s, "h" * 32, "x"))["player"]
        new = (await create_anonymous_player(s, "i" * 32, "x"))["player"]
        old.last_seen = int(time.time()) - 91 * 86400
        await s.commit()
        old_id, new_id = old.id, new.id
    assert await h.purge_inactive() == 1
    async with maker() as s:
        assert await s.get(Player, old_id) is None and await s.get(Player, new_id) is not None


def test_public_headers_block_geolocation(public, monkeypatch):
    from app.main import create_app
    app = create_app()
    from starlette.testclient import TestClient as TC
    c = TC(app)         # no lifespan: only the headers are under test
    r = c.get("/healthz")
    assert "geolocation=()" in r.headers["permissions-policy"]
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
    cfg = c.get("/api/config").json()
    assert cfg["real_gps"] is False and cfg["free_text"] is False and len(cfg["starts"]) >= 2


async def test_delete_me_gives_back_its_connection_before_queueing_for_the_world(monkeypatch):
    """Deletes holding a connection while waiting for the lock starved the lock's holder: the game froze."""
    from app.routes.auth_routes import delete_me
    order = []

    class Session:
        async def close(self):order.append('closed')

    class Hub:
        async def forget_player(self, pid):order.append(('forget', pid))

    monkeypatch.setattr(hubmod, 'get_hub', lambda: Hub())
    await delete_me(type('P', (), {'id': 7})(), Session())
    assert order == ['closed', ('forget', 7)]


def test_walking_does_not_resend_the_walls_every_few_steps():
    from app.game.sim import World, Actor, shift
    w = World()
    a = Actor(id=1, name='a', lat=41.88, lng=-87.63)
    w.actors[1] = a
    first = w.view(1)['building_key']
    changes = 0
    for _ in range(10):                                  # 20 m in 2 m steps, on a map with nothing near
        a.lat, a.lng = shift(a.lat, a.lng, 2, 0)
        changes += w.view(1, first)['building_key'] != first
    assert changes == 0
