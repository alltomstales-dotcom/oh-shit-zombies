"""Getting ready for strangers: a 25-player cap with its own screen, and start cities mapped from boot."""
from types import SimpleNamespace

import httpx
import pytest

from app.config import Settings, get_settings
from app.game.buildings import Buildings
from app.game.building_loader import BuildingLoader, UNLOAD_AFTER_S, start_regions
from app.game.starts import STARTS
from app.geo import cell_of


def test_the_cap_is_twenty_five_by_default():
    assert Settings(_env_file=None).max_players == 25


def test_start_regions_cover_every_start_and_its_neighbourhood():
    regions = start_regions()
    for st in STARTS:
        assert cell_of(st["lat"], st["lng"], 6) in regions
    assert len(regions) == len(set(regions)) <= 9 * len(STARTS)


def test_only_the_public_running_server_pins_the_start_cities(monkeypatch):
    from app.game import hub as hubmod
    assert BuildingLoader(SimpleNamespace(buildings=Buildings(), actors={}, zeds={})).pinned == []
    for real, expect in (("0", start_regions()), ("1", [])):
        monkeypatch.setenv("REAL_GPS", real); get_settings.cache_clear(); hubmod.reset_hub()
        assert hubmod.get_hub().building_loader.pinned == expect
    get_settings.cache_clear(); hubmod.reset_hub()


@pytest.mark.asyncio
async def test_pinned_regions_are_never_forgotten(maker):
    region = cell_of(STARTS[1]["lat"], STARTS[1]["lng"], 6)
    world = SimpleNamespace(buildings=Buildings(), actors={}, zeds={}, named_starts=True)
    loader = BuildingLoader(world); loader.pinned = start_regions()
    async def offline(request): return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        assert await loader.load(region, client)
    loader.loaded.add(region)
    assert await loader.forget_far(1000.0) == []
    assert await loader.forget_far(1000.0 + UNLOAD_AFTER_S * 10) == []
    assert region in loader.loaded and world.buildings.items


def test_a_full_server_says_so_with_its_size_and_when_to_retry():
    from app.routes.ws_routes import full_message
    cfg = Settings(_env_file=None)
    assert full_message(cfg, 0, 24, False) is None
    m = full_message(cfg, 0, 25, False)
    assert m["t"] == "full" and m["max"] == 25 and m["retry_s"] == 30 and "All 25 places are taken" in m["why"]
    assert full_message(cfg, 0, 25, True) is None                 # a reconnect keeps its place
    assert "Too many players from your connection" in full_message(cfg, cfg.max_conns_per_ip, 0, False)["why"]


async def test_an_action_inside_a_tick_is_judged_without_another_full_world_step(maker, monkeypatch):
    from app.auth import create_anonymous_player
    from app.game import hub as hubmod
    from app.game.hub import Hub
    async with maker() as s:
        player = (await create_anonymous_player(s, "e" * 20, "Tester"))["player"]
    hub = Hub(); hub.world.spawner = None; hub.director.policy = lambda *a: "quiet"
    clock = [1_000_000.0]; hub.clock = lambda: clock[0]
    async def send(m): pass
    conn, actor, _ = await hub.join(player, send)
    hub.world.set_position(player.id, 41.8807, -87.6278, 1.0)
    await hub.tick()
    steps = []
    real = hub.world.step
    hub.world.step = lambda now: (steps.append(now), real(now))[1]
    clock[0] += 0.05
    await hub.act(conn, "swing", {})
    assert steps == []                                   # 50 ms after the tick: the tick's world is current
    clock[0] += 0.3
    await hub.act(conn, "swing", {})
    assert steps == []                                   # a slow tick is not a reason to add more work
    clock[0] += 1.0
    await hub.act(conn, "swing", {})
    assert steps == [clock[0]]                           # the loop has stalled for a second: step first
    monkeypatch.setattr(hubmod, "ACT_STEP_MIN_S", 0.0)
    clock[0] += 0.01
    await hub.act(conn, "swing", {})
    assert len(steps) == 2                               # 0 restores stepping before every action
