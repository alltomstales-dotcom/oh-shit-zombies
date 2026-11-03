"""Seeing other players: only on servers without real GPS, only what you could see anyway, and
nothing that identifies the account."""
import random

import pytest

from app.config import get_settings
from app.game.hub import Hub
from app.game.sim import Actor, World, Zed, shift

LAT, LNG = 41.8807, -87.6278


def two(show=True, gap_m=6.0):
    w = World(rng=random.Random(2))
    w.show_others = show
    a = Actor(id=1, lat=LAT, lng=LNG, born=0.0, name="Rusty Otter 42", life_id=1)
    b = Actor(id=2, lat=LAT, lng=LNG, born=0.0, name="Quiet Heron 7", life_id=1)
    w.add_actor(a, 1000.0); w.add_actor(b, 1000.0)
    w.set_position(1, LAT, LNG, 1.0); w.set_position(2, *shift(LAT, LNG, gap_m, 0), 1.0)
    w.step(1000.2)
    return w, a, b


def test_two_survivors_in_sight_see_each_other_with_name_and_state():
    w, a, b = two()
    b.speed = 0.0
    mine, theirs = w.view(1)["others"], w.view(2)["others"]
    assert len(mine) == 1 and len(theirs) == 1
    oid, lat, lng, name, state, heading = mine[0]
    assert name == "Quiet Heron 7" and state == "standing"
    assert abs(lat - b.lat) < 1e-6 and abs(lng - b.lng) < 1e-6
    assert theirs[0][3] == "Rusty Otter 42"


def test_the_id_is_opaque_and_changes_with_a_new_life():
    w, a, b = two()
    first = w.view(1)["others"][0][0]
    assert first != str(b.id) and len(first) == 10
    b.life_id += 1
    assert w.view(1)["others"][0][0] != first


def test_off_unless_the_server_has_no_real_gps():
    w, a, b = two(show=False)
    assert w.view(1)["others"] == []
    assert not hasattr(World(), "show_others") or World().show_others is False


def test_hub_turns_it_on_only_without_real_gps(monkeypatch):
    for real, expect in (("0", True), ("1", False)):
        monkeypatch.setenv("REAL_GPS", real)
        get_settings.cache_clear()
        assert Hub().world.show_others is expect
    get_settings.cache_clear()


def test_out_of_sight_dead_or_disconnected_survivors_are_not_shown():
    w, a, b = two(gap_m=w_sight() + 15)
    assert w.view(1)["others"] == []
    w, a, b = two()
    b.connected = False
    assert w.view(1)["others"] == []
    b.connected = True; b.dead = True
    assert w.view(1)["others"] == []


def w_sight():
    return World().sight_m(Actor(id=9, lat=LAT, lng=LNG))


def test_states_follow_what_they_are_doing():
    w, a, b = two()
    b.channel = {"kind": "search", "ends": w.now + 4}
    assert w.view(1)["others"][0][4] == "searching"
    b.channel = None
    z = Zed(id="z1", lat=b.lat, lng=b.lng, kind="shambler", hp=20, hp_max=20, speed=0.8, variant=0, home=(b.lat, b.lng))
    z.state, z.target = "engaged", b.id
    w.zeds[z.id] = z
    assert w.view(1)["others"][0][4] == "fighting"


def test_at_most_twelve_nearest_and_never_yourself():
    w = World(rng=random.Random(1)); w.show_others = True
    for i in range(1, 20):
        o = Actor(id=i, lat=LAT, lng=LNG, born=0.0, name=f"S{i}")
        w.add_actor(o, 1000.0); w.set_position(i, *shift(LAT, LNG, 0.5 * i, 0), 1.0)
    w.step(1000.2)
    rows = w.view(1)["others"]
    assert len(rows) == World.OTHERS_MAX and "S1" not in [r[3] for r in rows]
    assert [r[3] for r in rows] == [f"S{i}" for i in range(2, 14)]


def test_generated_names_only_when_free_text_is_on_elsewhere():
    w, a, b = two()
    w.others_names = False
    assert w.view(1)["others"][0][3] == "Survivor"
