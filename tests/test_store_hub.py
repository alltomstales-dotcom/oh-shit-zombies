"""Saving, time away, and the hub's join / act / die / new-survivor cycle."""
import random

import pytest

from app.auth import create_anonymous_player
from app.game import store
from app.game.director import Director
from app.game.hub import Hub
from app.game.sim import Actor, World, Zed, shift
from app.game.spawn import Spawner
from app.models import Survivor

LAT, LNG = 44.9778, -93.2650


def test_time_away_heals_closes_wounds_and_caps_bleeding():
    a = store.starter(1, "T", 0.0)
    a.hp = 50.0
    a.end = 10.0
    a.wounds = [{"id": 1, "kind": "scratch", "part": "torso", "bleeding": False, "bandaged": True, "clean": False, "t": 0.0},
                {"id": 2, "kind": "laceration", "part": "neck", "bleeding": True, "bandaged": False, "clean": False, "t": 0.0}]
    rep = store.apply_time_away(a, 8 * 3600, 8 * 3600.0)
    assert rep["closed"] == 1 and len(a.wounds) == 1          # the scratch healed, the cut has not
    assert not a.wounds[0]["bleeding"]                        # but it stopped bleeding
    assert rep["bled"] == pytest.approx(0.25 * 3 * 120, abs=0.2)
    assert a.hp == 85.0 and a.end == 100.0                    # bled to the floor of 5, then 8 h at 10 an hour


def test_a_short_break_does_not_heal():
    a = store.starter(1, "T", 0.0)
    a.hp = 50.0
    store.apply_time_away(a, 300, 300.0)
    assert a.hp == 50.0


def test_infection_runs_while_away():
    a = store.starter(1, "T", 0.0)
    a.infected_at, a.turns_at = 0.0, 30 * 3600.0
    assert store.apply_time_away(a, 31 * 3600, 31 * 3600.0)["turned"]


def test_state_round_trip():
    a = store.starter(7, "T", 5.0, LAT, LNG)
    a.claimed.add("s:x")
    a.kills = 3
    row = Survivor(player_id=7, born=5.0, state=store.to_state(a))
    b = store.from_state(row, "T")
    assert b.items == a.items and b.hands == a.hands and b.claimed == {"s:x"} and b.kills == 3
    assert b.weapon()["code"] == "bat"


def test_spawner_is_deterministic_and_clumpy():
    sp = Spawner()
    cells = sp.cells_near(LAT, LNG)
    assert len(cells) == 9
    a = [z for c in cells for z in sp.zeds(c, 1_000_000)]
    b = [z for c in cells for z in sp.zeds(c, 1_000_000)]
    assert a == b
    assert len({z["id"] for z in a}) == len(a)
    assert sp.zeds(cells[0], 1_000_000) != sp.zeds(cells[0], 1_000_000 + 86400) or not sp.zeds(cells[0], 1_000_000)
    for s in (st for c in cells for st in sp.stashes(c, 1_000_000)):
        assert s["loot"]


def test_director_fills_a_long_lull_and_never_spawns_in_sight():
    w = World(rng=random.Random(4))
    a = Actor(id=1, lat=LAT, lng=LNG, born=0.0)
    w.add_actor(a, 1000.0)
    w.set_position(1, LAT, LNG, 1.0)
    d = Director(w, policy=lambda rng, actor, s: "straggler", lull_s=(30.0, 30.0), opening_s=None)
    t = 1000.0
    for i in range(600):
        t += 0.2
        w.set_position(1, *shift(LAT, LNG, 0, 1.3 * 0.2 * (i + 1)), 1.0)
        w.step(t)
        d.tick()
        if d.log:
            break
    assert d.log and d.log[0]["beat"] == "straggler"
    z = next(iter(w.zeds.values()))
    from app.game.sim import dist_m
    assert dist_m(a.lat, a.lng, z.lat, z.lng) >= w.sight_m(a)
    assert z.temp and z.target == 1


def test_director_opens_a_session_with_something_coming_out_of_the_fog():
    from app.game.sim import dist_m
    w = World(rng=random.Random(9))
    a = Actor(id=1, lat=LAT, lng=LNG, born=0.0)
    w.add_actor(a, 1000.0)
    w.set_position(1, LAT, LNG, 1.0)
    d = Director(w)
    t, first_seen = 1000.0, None
    for _ in range(600):                       # two minutes standing still
        t += 0.2
        w.step(t)
        d.tick()
        if d.log and len(d.log) == 1 and d.log[0]["t"] == w.now:
            assert d.log[0]["beat"] == "opening" and w.now - 1000.0 <= 10.0
            assert all(dist_m(a.lat, a.lng, z.lat, z.lng) >= w.sight_m(a) for z in w.zeds.values())
        if first_seen is None and w.view(1)["z"]:
            first_seen = t - 1000.0
    assert first_seen is not None and first_seen < 30.0
    assert 2 <= len([z for z in w.zeds.values() if z.temp]) <= 3


async def test_hub_join_fight_die_and_start_again(maker):
    async with maker() as s:
        player = (await create_anonymous_player(s, "d" * 20, "Tester"))["player"]
    hub = Hub()
    hub.world.spawner = None
    hub.director.policy = lambda *a: "quiet"
    sent = []

    async def send(m):
        sent.append(m)
    clock = [1_000_000.0]
    hub.clock = lambda: clock[0]
    conn, actor, report = await hub.join(player, send)
    assert report is None and actor.weapon()["code"] == "bat"
    hub.world.set_position(player.id, LAT, LNG, 1.0)
    await hub.tick()
    # one zombie already on the survivor
    zlat, zlng = shift(LAT, LNG, 0, 2)
    hub.world.zeds["a"] = Zed(id="a", lat=zlat, lng=zlng, state="engaged", target=player.id, attack_at=clock[0] + 99, hp=5, hp_max=5)
    clock[0] += 0.2
    await hub.tick()
    assert any(m["t"] == "s" and m["z"] for m in sent)
    res = None
    for _ in range(8):
        clock[0] += 1.0
        res = await hub.act(conn, "swing", {})
        if res.get("kill"):
            break
    assert res.get("kill") and "a" not in hub.world.zeds
    await hub.save_all()
    async with maker() as s:
        assert "a" in await store.load_dead(s, clock[0])
    # now kill the survivor
    actor.hp = 0.5
    actor.wounds.append({"id": 9, "kind": "bite", "part": "neck", "bleeding": True, "bandaged": False, "clean": False, "t": clock[0]})
    for _ in range(10):
        clock[0] += 0.2
        await hub.tick()
    assert actor.dead
    assert any(e["e"] == "died" for m in sent for e in m.get("ev", []))
    await hub.save_all(force=True)
    fresh = await hub.new_survivor(player, conn)
    assert not fresh.dead and fresh.hp == 100 and fresh.kills == 0 and fresh.weapon()["code"] == "bat"
    assert (fresh.lat, fresh.lng) == (0, 0)  # next life waits for current GPS/manual placement
    async with maker() as s:
        from sqlalchemy import select
        rows = (await s.execute(select(Survivor).order_by(Survivor.id))).scalars().all()
        assert [r.alive for r in rows] == [False, True]
        assert rows[0].death["cause"] == "bled out"
        assert (await store.last_death(s, player.id))["kills"] == 1


async def test_quitting_mid_fight_leaves_the_body_in_the_world(maker):
    async with maker() as s:
        player = (await create_anonymous_player(s, "e" * 20, "Quitter"))["player"]
    hub = Hub()
    hub.world.spawner = None
    clock = [2_000_000.0]
    hub.clock = lambda: clock[0]

    async def send(m):
        pass
    conn, actor, _ = await hub.join(player, send)
    hub.world.set_position(player.id, LAT, LNG, 1.0)
    await hub.tick()
    zlat, zlng = shift(LAT, LNG, 0, 2)
    hub.world.zeds["a"] = Zed(id="a", lat=zlat, lng=zlng, state="engaged", target=player.id, attack_at=clock[0] + 1)
    hub.world.T["attack_miss"] = 0.0
    hub.leave(player.id, conn)
    for _ in range(40):                                  # eight seconds later
        clock[0] += 0.2
        await hub.tick()
    assert player.id in hub.world.actors and actor.hp < 100      # still there, still being bitten
    for _ in range(80):
        clock[0] += 0.2
        await hub.tick()
    assert player.id not in hub.world.actors                     # gone after the grace period
