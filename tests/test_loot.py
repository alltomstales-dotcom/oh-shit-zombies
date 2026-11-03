"""The full container and pack flow, without a database or real clock."""
from types import SimpleNamespace

from app.game.content import ITEMS, STASH_KINDS
from app.game import loot
from app.game.sim import Actor, World, Zed, shift
from app.game.spawn import Spawner
from app.game.store import from_state, to_state

LAT, LNG = 44.9778, -93.2650


def setup():
    w = World()
    a = Actor(id=1, lat=LAT, lng=LNG)
    w.add_actor(a, 0)
    w.set_position(a.id, LAT, LNG, 1)
    w.stashes["box"] = {"id": "box", "lat": LAT, "lng": LNG, "kind": "chest",
                         "loot": [("axe", 1), ("bandage", 2)], "condition": {"axe": 6}}
    return w, a


def test_search_reveals_shelf_then_explicit_take_preserves_condition():
    w, a = setup()
    assert w.act(a.id, "search", stash="box")["ok"]
    assert a.items == []
    w.now = 4.1
    w._step_actor(a, .2)
    assert not a.items and a.hands is None
    shelf=a.loot_shelves['box']
    for item in list(shelf['items']):
        assert loot.take(w,a,{'stash':'box','item':item['id'],'qty':item['qty'],
                             'revision':shelf['revision'],'request':'take-box-'+str(item['id'])})['ok']
    assert a.count("axe") == 1 and a.count("bandage") == 2
    assert next(i for i in a.items if i["code"] == "axe")["cond"] == 6
    assert a.hands is None
    axe=next(i for i in a.items if i["code"]=="axe")
    assert w.act(a.id,"equip",item=axe["id"])["ok"]
    assert a.weapon()["code"] == "axe"
    assert w.view(a.id)["stashes"][0][4] is True
    assert not w.act(a.id, "search", stash="box")["ok"]
    assert sum(e["e"] == "found" for e in a.events) == 1


def test_search_cannot_collect_loot_after_walking_away():
    w, a = setup()
    assert w.act(a.id, "search", stash="box")["ok"]
    a.lat, a.lng = shift(LAT, LNG, 30, 0)
    w.now = 5
    w._finish_channel(a, a.channel)
    assert not a.items and "box" not in a.claimed
    assert a.events[-1] == {"e": "interrupted", "what": "search"}


def test_search_is_noisy_and_grab_blocks_it():
    w, a = setup()
    z = Zed(id="z", lat=LAT, lng=LNG, home=(LAT, LNG))
    w.zeds[z.id] = z
    assert w.act(a.id, "search", stash="box")["ok"]
    assert z.state == "investigate"
    z.state, z.target = "engaged", a.id
    assert not w.act(a.id, "search", stash="box")["ok"]


def test_drop_one_from_stack_and_pick_it_up():
    w, a = setup()
    row = a.add("water", 2)
    original_weight = a.weight()
    assert w.act(a.id, "drop", item=row["id"])["ok"]
    assert a.count("water") == 1
    assert a.weight() == original_weight - ITEMS["water"]["w"]
    did = next(iter(w.drops))
    assert w.act(a.id, "pickup", drop=did)["ok"]
    assert a.count("water") == 2 and not w.drops


def test_dropping_held_weapon_clears_hands_and_preserves_condition():
    w, a = setup()
    row = a.add("axe", cond=5)
    a.hands = row["id"]
    assert w.act(a.id, "drop", item=row["id"])["ok"]
    assert a.hands is None and not a.items
    did = next(iter(w.drops))
    assert w.act(a.id, "pickup", drop=did)["ok"]
    assert a.weapon()["cond"] == 5


def test_claimed_container_and_inventory_survive_store_roundtrip():
    w, a = setup()
    a.claimed.add("box")
    a.add("axe", cond=6)
    row = SimpleNamespace(state=to_state(a), player_id=1, born=a.born)
    loaded = from_state(row, "Survivor")
    assert "box" in loaded.claimed and loaded.items == a.items


def test_containers_are_deterministic_varied_and_have_valid_loot():
    spawner = Spawner()
    kinds = set()
    for cell in spawner.cells_near(LAT, LNG):
        one = spawner.stashes(cell, 123456)
        assert one == spawner.stashes(cell, 123456)
        assert 1 <= len(one) <= 3
        for s in one:
            kinds.add(s["kind"])
            assert s["kind"] in STASH_KINDS and s["loot"]
            assert all(code in ITEMS and qty > 0 for code, qty in s["loot"])
            assert all(4 <= cond <= 9 for cond in s["condition"].values())
    assert len(kinds) >= 3
