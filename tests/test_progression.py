"""Progression awards are earned once, persisted, and bounded."""
from types import SimpleNamespace
import random

from app.game.sim import Actor, World, Zed, shift
from app.game.progression import award, skill_level, view
from app.game.store import to_state, from_state, starter


def setup():
    w = World(rng=random.Random(1))
    a = Actor(id=1, lat=44.9778, lng=-93.265)
    w.add_actor(a, 0)
    w.set_position(1, a.lat, a.lng, 1)
    return w, a


def test_search_awards_xp_only_when_completed_and_not_twice():
    w, a = setup()
    w.stashes["box"] = {"id": "box", "lat": a.lat, "lng": a.lng, "kind": "chest", "loot": [("bandage", 1)]}
    assert w.act(1, "search", stash="box")["ok"]
    assert a.xp == 0
    ch = a.channel
    w._finish_channel(a, ch)
    assert a.xp == 25 and a.skill_xp["scavenging"] == 25
    w._finish_channel(a, ch)
    assert a.xp == 25
    assert not w.act(1, "search", stash="box")["ok"]
    assert a.xp == 25


def test_failed_empty_attacks_and_inventory_shuffling_award_nothing():
    w, a = setup()
    row = a.add("bat")
    a.hands = row["id"]
    assert w.act(1, "swing")["whiff"]
    w.now = 2
    assert w.act(1, "drop", item=row["id"])["ok"]
    assert w.act(1, "pickup", drop=next(iter(w.drops)))["ok"]
    assert a.xp == 0


def test_kill_award_happens_once_and_uses_correct_skill():
    w, a = setup()
    z = Zed(id="z", lat=a.lat, lng=a.lng, home=(a.lat,a.lng))
    w.zeds[z.id] = z
    w._kill(z, a, skill="shooting")
    w._kill(z, a, skill="shooting")
    assert a.xp == 20 and a.kills == 1
    assert a.skill_xp == {"shooting": 20}


def test_skill_benefits_are_capped_and_search_gets_faster():
    w, a = setup()
    award(a, "scavenging", 100000)
    award(a, "fitness", 100000)
    assert skill_level(a, "scavenging") == 5
    assert w.carry_capacity(a) == 14
    w.stashes["box"] = {"id": "box", "lat": a.lat, "lng": a.lng, "kind": "chest", "loot":[]}
    result = w.act(1, "search", stash="box")
    assert abs(result["channel"]-2.8)<.001
    assert view(a)["level"] == 20


def test_training_rewards_actual_distance_not_teleports_or_old_walks():
    w, a = setup()
    a.walked_m = 5000
    w.set_position(1, *shift(a.lat,a.lng,1000,0),1)
    w.step(.2)
    assert a.xp == 0 and a.training_m == 0
    a.training_m = 99.9
    w.set_position(1,*shift(a.lat,a.lng,0,10),1)
    w.step(.4)
    assert a.skill_xp["fitness"] == 10
    assert 0 <= a.training_m < 1.2


def test_first_aid_awards_only_for_real_treatment():
    w, a = setup()
    a.wounds=[{"id":1,"kind":"scratch","part":"left hand","bleeding":True,"bandaged":False,"clean":False,"t":0}]
    a.add("bandage",2)
    assert w.act(1,"bandage")["ok"]
    ch=a.channel
    w._finish_channel(a,ch)
    assert a.xp == 20 and a.skill_xp["first_aid"] == 20
    w._finish_channel(a,ch)
    assert a.xp == 20 and a.count("bandage") == 1


def test_progression_survives_save_and_new_life_resets_it():
    w, a = setup()
    award(a,"melee",70)
    a.explored=["cell"]
    a.training_m=25.5
    row=SimpleNamespace(state=to_state(a),player_id=1,born=a.born)
    loaded=from_state(row,"Survivor")
    assert loaded.xp == 70 and loaded.skill_xp == a.skill_xp
    assert loaded.explored == ["cell"] and loaded.training_m == 25.5
    fresh=starter(1,"Survivor",100)
    assert fresh.xp == 0 and fresh.skill_xp == {} and fresh.explored == []


def test_old_saved_survivors_load_with_zero_progression():
    row=SimpleNamespace(state={"lat":44.9,"lng":-93.2,"items":[],"claimed":["box"]},player_id=1,born=1)
    loaded=from_state(row,"Old survivor")
    assert loaded.xp == 0 and loaded.skill_xp == {} and loaded.claimed == {"box"}
