"""Siege mode v0 (app/game/siege.py, siege_hub.py; design in ~/osz-stack/SIEGE.md)."""
import asyncio
import types

import pytest

from app.game import siege
from app.game.siege_hub import SiegeHub
from app.game.sim import Actor, World, Zed, dist_m


def run(**kw):
    return siege.SiegeRun(7, "Calm Fox 68", [], seed=kw.pop("seed", 3), **kw)


def test_wave_table_is_data_a_sawtooth_with_a_quiet_start():
    w = siege.WAVES
    assert len(w) == 30 and [r["minute"] for r in w] == list(range(30))
    floors = [r["floor"] for r in w]
    rises = sum(1 for a, b in zip(floors, floors[1:]) if b > a)
    falls = sum(1 for a, b in zip(floors, floors[1:]) if b < a)
    assert rises >= 6 and falls >= 6                     # it climbs and falls back, again and again
    assert max(floors[:5]) < max(floors[20:])
    assert w[-1]["hp"] > w[0]["hp"] and w[-1]["speed"] > w[0]["speed"]
    assert [b["at"] for b in siege.BOSSES] == [300, 600, 900, 1200, 1500]


def test_floor_is_refilled_from_outside_the_arena_and_every_zombie_hunts():
    r = run()
    for _ in range(50):
        r.step(0.2)
    zs = r.alive_zeds()
    assert len(zs) >= siege.WAVES[0]["floor"]
    assert all(z.target == r.actor.id for z in zs)
    assert all(z.state in ("chase", "engaged", "alert", "stagger", "down", "rising") for z in zs)


def test_boss_is_telegraphed_then_walks_in_where_it_was_shown():
    r = run()
    r.world.zeds.clear()
    r.t = 300 - siege.BOSS_WARN_S - 0.1
    r.step(0.2)
    warn = r.info()["boss_warn"]
    assert warn and warn["name"] == siege.BOSSES[0]["name"]
    assert any(e["e"] == "siege_boss_warn" for e in r.events)
    assert dist_m(r.arena["lat"], r.arena["lng"], warn["lat"], warn["lng"]) > r.arena["r"]
    while r.t < 300.2:
        r.step(0.2)
    boss = r.world.zeds[r.boss_id]
    assert boss.boss["n"] == 1 and boss.hp == siege.BOSSES[0]["hp"]
    assert dist_m(boss.lat, boss.lng, warn["lat"], warn["lng"]) < 6.0
    assert r.info()["boss"]["hp_max"] == siege.BOSSES[0]["hp"]


def test_level_up_offers_three_and_pauses_the_run_until_one_is_picked():
    r = run()
    r.xp = siege.xp_needed(1)
    r.step(0.2)
    assert r.choice and len(set(r.choice)) == 3
    t = r.t
    for _ in range(10):
        r.step(0.2, wall=1.0)
    assert r.t == t                                      # paused while choosing
    r.choice = ["heavy", "quick", "arc"]
    assert r.pick(0)["picked"] == "heavy"
    assert r.actor.mods["dmg"] == pytest.approx(1.15)
    r.step(0.2)
    assert r.t > t


def test_an_unanswered_choice_takes_the_first_after_the_timeout():
    r = run()
    r.xp = siege.xp_needed(1); r.step(0.2)
    first = r.choice[0]
    r.open_choice(100.0)
    r.step(0.2, wall=100.0 + siege.CHOICE_TIMEOUT_S + 0.1)
    assert r.choice is None and r.taken.get(first) == 1


def test_upgrades_change_the_fight_only_through_mods():
    w = World(); a = Actor(id=1, lat=41.88, lng=-87.63); w.add_actor(a, 10.0); w.now = 10.0
    assert a.mods == {}                                   # survival: nothing
    z = Zed(id="z", lat=41.88, lng=-87.63, hp=1000, hp_max=1000)
    w.zeds["z"] = z
    a.mods = {"dmg": 2.0}
    w.rng.seed(1); w.act(1, "swing", target="z")
    hit2 = 1000 - z.hp
    a.mods = {}; z.hp = 1000; a.busy_until = 0; a.end = 100
    w.rng.seed(1); w.act(1, "swing", target="z")
    assert hit2 == pytest.approx(2 * (1000 - z.hp))


def test_a_boss_cannot_be_shoved_over_and_bites_harder():
    w = World(); a = Actor(id=1, lat=41.88, lng=-87.63); w.add_actor(a, 10.0); w.now = 10.0
    boss = Zed(id="b", lat=41.88, lng=-87.63, state="engaged", target=1, boss={"n": 1, "name": "x", "dmg": 3.0})
    w.zeds["b"] = boss
    for _ in range(20):
        a.busy_until = 0; a.end = 100
        w.act(1, "shove")
    assert boss.state == "engaged"


def test_walking_onto_a_chest_opens_it_for_an_upgrade_and_a_find_for_the_haul():
    r = run()
    r.world.zeds.clear()
    r._add_chest((r.actor.lat, r.actor.lng), "arena")
    r.step(0.2)
    assert not r.chests and len(r.haul) == 1 and sum(r.taken.values()) == 1
    assert any(e["e"] == "siege_chest_open" for e in r.events)


def test_held_inside_the_arena():
    r = run()
    lat, lng = r.clamp(r.arena["lat"] + 0.01, r.arena["lng"])
    assert dist_m(r.arena["lat"], r.arena["lng"], lat, lng) == pytest.approx(r.arena["r"], abs=0.05)


def test_thirty_minutes_ends_in_extraction_with_the_bonus():
    r = run()
    r.world.zeds.clear(); r.boss_next = len(r.bosses)
    r.waves = [dict(row, floor=0) for row in r.waves]
    r.t = siege.LENGTH_S - 0.3
    r.step(0.2); r.step(0.2)
    assert r.over["result"] == "extracted"
    assert r.over["score"] >= siege.SCORE["extracted"]


def test_death_ends_the_run_and_the_timer_stops():
    r = run()
    r.actor.hp = 0; r.actor.death = {"cause": "killed"}
    r.step(0.2)
    assert r.over["result"] == "dead"
    t = r.over["t"]
    r.step(5.0)
    assert r.over["t"] == t


class FakeMain:
    def __init__(self):
        self.world = World(); self.state_lock = asyncio.Lock(); self.conns = {}


@pytest.mark.asyncio
async def test_haul_goes_into_the_home_cupboard_as_far_as_it_fits():
    main = FakeMain()
    main.world.homes[7] = {"name": "Flat", "items": [{"id": 1, "code": "plank", "qty": 60, "cond": None}],
                           "capacity": 40.0, "next_item": 2, "revision": 1}
    h = SiegeHub(main)
    out = await h.deliver(7, [{"code": "bandage", "qty": 2}, {"code": "plank", "qty": 20}])
    home = main.world.homes[7]
    assert {"code": "bandage", "qty": 2} in out["items"]
    weight = sum({"bandage": .1, "plank": .6}[i["code"]] * i["qty"] for i in home["items"])
    assert weight <= 40.0 + 1e-6 and out["left"]          # the planks didn't all fit
    assert 7 in main.world.home_dirty and home["revision"] == 2


@pytest.mark.asyncio
async def test_no_home_means_the_haul_stays_and_survival_is_untouched():
    main = FakeMain()
    h = SiegeHub(main)
    out = await h.deliver(9, [{"code": "snack", "qty": 1}])
    assert out["home"] is None and out["left"] == [{"code": "snack", "qty": 1}]
    assert not main.world.home_dirty and not main.world.actors


def test_hub_runs_a_session_and_frames_carry_the_siege_block():
    main = FakeMain()
    h = SiegeHub(main)
    sent = []
    async def send(m):
        sent.append(m)
    s = h.join(types.SimpleNamespace(id=7, name="Calm Fox 68"), send)
    asyncio.run(h.tick(0.2))
    f = sent[-1]
    assert f["t"] == "s" and f["siege"]["t"] > 0 and f["siege"]["arena"]["id"] == "daley"
    assert "you" in f and h.playing() == 1
    asyncio.run(h.leave(7, s))
    assert h.playing() == 0 and s.run.over["result"] == "left"
