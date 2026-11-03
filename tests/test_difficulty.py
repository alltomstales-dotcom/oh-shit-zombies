"""Difficulty profiles: classic is the old game exactly; the escalating director never eases off."""
import random

import pytest

from app.game import difficulty
from app.game.content import TUNE
from app.game.director import Director, escalate_policy, default_policy
from app.game.hub import Hub
from app.game.sim import Actor, World, shift
from app.game.spawn import Spawner

LAT, LNG = 41.8807, -87.6278


def test_classic_is_the_old_tuning_number_for_number():
    d = difficulty.resolve("classic")
    assert d["density"] == 1.3 and d["director"]["mode"] == "ease"
    h = Hub(difficulty=d)
    for k in ("grace_notice", "grace_bite", "notice_rate_near", "notice_rate_far") + difficulty.NOISE_KEYS:
        assert h.world.T[k] == TUNE[k]
    assert h.world.T["zed_speed_mult"] == 1.0
    assert h.world.spawner.density == 1.3 and h.world.spawner.night_packs == 1.0
    assert h.director.mode == "ease" and h.director.lull_s == (45.0, 100.0)


def test_unknown_profile_falls_back_to_classic_and_unknown_dials_are_refused():
    assert difficulty.resolve("nonsense") == difficulty.resolve("classic")
    with pytest.raises(ValueError):
        difficulty.resolve("classic", '{"zombie_lasers": 1}')


def test_overrides_layer_on_top_and_scale_the_right_numbers():
    d = difficulty.resolve("classic", '{"noise": 1.5, "notice": 2, "zed_speed": 1.3, "director": "escalate"}')
    t = difficulty.tune_for(d, TUNE)
    assert t["noise_walk_m"] == pytest.approx(TUNE["noise_walk_m"] * 1.5)
    assert t["notice_rate_near"] == pytest.approx(TUNE["notice_rate_near"] * 2)
    assert d["director"]["mode"] == "escalate" and d["director"]["gentle_s"] == 60.0
    d2 = difficulty.resolve("public", {"director": {"gentle_s": 30.0}})
    assert d2["director"]["mode"] == "escalate" and d2["director"]["gentle_s"] == 30.0
    assert difficulty.resolve("public")["director"]["gentle_s"] == 60.0     # the profile itself is untouched


def test_night_packs_one_is_the_original_draw_and_more_means_more():
    cells = Spawner().cells_near(LAT, LNG)
    old, same, more = Spawner(density=1.3), Spawner(density=1.3, night_packs=1.0), Spawner(density=1.3, night_packs=3.0)
    for c in cells:
        assert old.zeds(c, 1_000_000) == same.zeds(c, 1_000_000)
    count = lambda sp: sum(1 for c in cells for z in sp.zeds(c, 1_000_000) if z["night"])
    assert count(more) > count(old)


def test_zombie_speed_dial_reaches_spawned_and_director_zombies():
    w = World(rng=random.Random(3), tune={"zed_speed_mult": 2.0})
    a = Actor(id=1, lat=LAT, lng=LNG, born=0.0)
    w.add_actor(a, 1000.0)
    w.set_position(1, LAT, LNG, 1.0)
    d = Director(w, config=difficulty.DIRECTOR_ESCALATE)
    z = d._spawn(a, 0.0, 40.0, "shambler", chase=True)
    assert z is not None and z.speed >= 0.70 * 2.0


def _walk(w, d, seconds, t0=1000.0, hp=None):
    t = t0
    for i in range(int(seconds / 0.2)):
        t += 0.2
        if hp is not None:
            w.actors[1].hp = hp
        w.set_position(1, *shift(LAT, LNG, 0, 1.3 * 0.2 * (i + 1)), 1.0)
        w.step(t)
        d.tick()
    return t


def test_escalate_keeps_the_first_minute_to_the_opening_then_climbs():
    w = World(rng=random.Random(5))
    w.add_actor(Actor(id=1, lat=LAT, lng=LNG, born=0.0), 1000.0)
    w.set_position(1, LAT, LNG, 1.0)
    d = Director(w, config=difficulty.DIRECTOR_ESCALATE, policy=lambda rng, a, s: "noise", opening_s=None)
    _walk(w, d, 59.0)
    assert d.log == []                                  # nothing at all in the gentle minute
    _walk(w, d, 400.0, t0=w.now)
    beats = [e for e in d.log if e["beat"] != "opening"]
    assert beats and all(e["t"] - 1000.0 >= 60.0 for e in beats)
    pressures = [e["pressure"] for e in beats]
    assert pressures == sorted(pressures) and pressures[-1] == 1.0
    gaps = [b["t"] - a["t"] for a, b in zip(beats, beats[1:])]
    assert gaps[-1] < gaps[0]                           # the lulls shrink as pressure climbs


def test_escalate_does_not_ease_off_when_hurt_but_the_old_director_does():
    hurt = {"hp": 20, "bleeding": True, "night": False, "pressure": 0.8}
    well = {**hurt, "hp": 100, "bleeding": False}
    seq = lambda pol, s: [pol(random.Random(i), None, s) for i in range(400)]
    assert seq(escalate_policy, hurt) == seq(escalate_policy, well)
    old_hurt, old_well = seq(default_policy, hurt), seq(default_policy, well)
    assert old_hurt.count("quiet") > old_well.count("quiet")


def test_hunt_only_comes_from_the_escalating_director():
    s = {"hp": 100, "bleeding": False, "night": False}
    assert "hunt" not in {escalate_policy(random.Random(i), None, {**s, "pressure": 0.5}) for i in range(500)}
    assert "hunt" in {escalate_policy(random.Random(i), None, {**s, "pressure": 1.0}) for i in range(500)}
    w = World(rng=random.Random(1))
    w.add_actor(Actor(id=1, lat=LAT, lng=LNG, born=0.0), 1000.0)
    w.set_position(1, LAT, LNG, 1.0)
    d = Director(w, policy=lambda *a: "hunt", lull_s=(5.0, 5.0), opening_s=None)
    _walk(w, d, 60.0)
    assert d.log and all(e["beat"] == "quiet" for e in d.log)     # ease mode turns a stray hunt into quiet


def test_the_gentle_first_moments_slow_noticing_and_chasing_then_end():
    w = World(rng=random.Random(8), tune={"early_s": 60.0, "early_notice": 0.2, "early_speed": 0.5})
    a = Actor(id=1, lat=LAT, lng=LNG, born=0.0, placed_at=1000.0)
    w.add_actor(a, 1000.0)
    w.now = 1030.0
    assert w.early(a)
    w.now = 1061.0
    assert not w.early(a)
    assert not World().early(a)                         # classic: off
    assert difficulty.resolve("classic")["early_s"] == 0.0


def test_public_is_exactly_the_setting_the_sweep_confirmed():
    # The dials as the sweep passed them (player/plans/phaseC.json in ~/osz-stack): classic plus these.
    p4 = {"director": {"mode": "escalate", "group_grow": 6, "hunt_size": [5, 8], "lull_end_s": [8.0, 15.0]},
          "density": 4.0, "zed_speed": 1.8, "notice": 2.0, "grace_notice": 1.0, "grace_bite": 1.0,
          "early_s": 60.0, "early_notice": 0.1, "early_speed": 0.5}
    swept, public = difficulty.resolve("classic", p4), difficulty.resolve("public")
    norm = lambda d: {k: ({a: tuple(b) if isinstance(b, (list, tuple)) else b for a, b in v.items()} if isinstance(v, dict) else v) for k, v in d.items()}
    assert norm(swept) == norm(public)


def test_director_zombies_that_lost_interest_and_are_unseen_are_removed():
    from app.game.sim import Zed
    w = World(rng=random.Random(4))
    a = Actor(id=1, lat=LAT, lng=LNG, born=0.0)
    w.add_actor(a, 1000.0)
    far = shift(LAT, LNG, 0, 120)
    def zed(zid, temp, spawned, state="idle"):
        z = Zed(id=zid, lat=far[0], lng=far[1], kind="shambler", hp=20, hp_max=20, speed=0.8, variant=0,
                home=far, temp=temp, spawned_at=spawned)
        z.state = state; w.zeds[zid] = z
    zed("t:old", True, 0.0); zed("t:new", True, 990.0); zed("z:fixed", False, 0.0); zed("t:hunting", True, 0.0, "chase")
    w.zeds["t:hunting"].target = 1
    w.now = 1000.0
    w._unload()
    assert set(w.zeds) == {"t:new", "z:fixed", "t:hunting"}
    near = shift(LAT, LNG, 0, 5)
    w.zeds["t:new"].lat, w.zeds["t:new"].lng = near
    w.now = 2000.0
    w._unload()
    assert "t:new" in w.zeds                                # in sight: it stays, however long


def test_sent_zombies_have_a_ceiling_a_lone_survivor_never_meets():
    from app.game.sim import Zed
    w = World(rng=random.Random(6))
    w.add_actor(Actor(id=1, lat=LAT, lng=LNG, born=0.0), 1000.0)
    w.set_position(1, LAT, LNG, 1.0)
    d = Director(w, config=difficulty.DIRECTOR_ESCALATE)
    assert not d._crowded()
    for i in range(63):                                  # 60 + 3 for the one survivor
        z = Zed(id=f"t:{i}", lat=LAT, lng=LNG, temp=True); w.zeds[z.id] = z
    assert d._crowded()
    d2 = Director(w, config=difficulty.DIRECTOR_ESCALATE, policy=lambda *a: "hunt", opening_s=None)
    d2.st[1] = {"next": 0, "walked": -999, "since": 0, "lull": 0, "last": 0, "open_at": None}
    w.now = 1000.0; d2.tick()
    assert d2.log and d2.log[-1]["beat"] == "quiet" and len(w.zeds) == 63
