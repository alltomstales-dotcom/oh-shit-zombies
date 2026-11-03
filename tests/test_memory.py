"""A player's remembered map: bounded, honest about age, kept across lives."""
import random

from app.game import memory
from app.game.sim import Actor, World, shift

LAT, LNG = 44.9778, -93.2650
DAY = 86400.0


def make(now=10 * DAY):
    w = World(rng=random.Random(1))
    a = Actor(id=1, lat=LAT, lng=LNG, born=now - DAY)
    w.add_actor(a, now)
    w.set_position(1, LAT, LNG, 1.0)
    w.step(now)
    return w, a, now


def walk_east(w, a, t, metres, pace=6.0, hz=5):
    x = 0.0
    while x < metres:
        x += pace / hz
        t += 1.0 / hz
        w.set_position(1, *shift(LAT, LNG, x, 0), 1.0)
        w.step(t)
    return t


def test_standing_still_remembers_only_what_is_around_and_costs_nothing_more():
    w, a, t = make()
    cells = dict(w.memories[1]["cells"])
    assert 6 <= len(cells) <= 15                       # the street in view, not the town
    w.memory_dirty.clear()
    for _ in range(50):
        t += 0.2
        w.step(t)
    assert w.memories[1]["cells"] == cells and not w.memory_dirty


def test_walking_extends_the_remembered_strip_and_the_view_is_clipped_to_the_viewport():
    w, a, t = make()
    t = walk_east(w, a, t, 400)
    mem = w.memories[1]
    assert 1 in w.memory_dirty and len(mem["cells"]) > 40
    near = memory.view(w, a)
    assert near["ok"] and near["known"] == len(mem["cells"]) and near["span"] == list(memory.CELL_SPAN)
    assert len(near["cells"]) == len(mem["cells"]) and all(c[2] == 0 for c in near["cells"])
    # asked about somewhere 5 km away, none of this strip is sent
    far = w.act(1, "memory", lat=LAT + 0.045, lng=LNG)
    assert far["ok"] and far["cells"] == [] and far["known"] == len(mem["cells"])
    # a nonsense point falls back to where the survivor is
    assert len(w.act(1, "memory", lat=float("nan"), lng=LNG)["cells"]) == len(mem["cells"])


def test_looking_at_the_map_does_not_cancel_work_or_count_as_an_action():
    w, a, t = make()
    a.channel = {"kind": "work", "ends": t + 30, "op": "rest"}
    last = a.last_action
    assert w.act(1, "memory")["ok"]
    assert a.channel is not None and a.last_action == last and not any(e["e"] == "interrupted" for e in a.events)


def test_age_is_reported_in_days_and_the_oldest_ground_is_forgotten_first():
    w, a, t = make()
    old = dict(w.memories[1]["cells"])
    w.step(t + 3 * DAY + 1)
    aged = memory.view(w, a)
    assert {c[2] for c in aged["cells"]} == {0}        # still standing here: seen again today
    # fill past the cap with ground last seen long ago, then walk: the old ground goes first
    mem = w.memories[1]
    for i in range(memory.MAX_CELLS + 50):
        mem["cells"]["zz%06d" % i] = 1
    walk_east(w, a, t + 3 * DAY + 1, 60)
    assert len(mem["cells"]) <= memory.MAX_CELLS
    assert all(c in mem["cells"] for c in old)
    assert sum(1 for c in mem["cells"] if c.startswith("zz")) < memory.MAX_CELLS


def test_an_opened_container_is_marked_with_what_was_left_and_when():
    w, a, t = make()
    pos = shift(LAT, LNG, 6, 0)
    a.loot_shelves["box"] = {"id": "box", "lat": pos[0], "lng": pos[1], "kind": "kitchen",
                             "items": [{"id": 1, "code": "beans", "qty": 2}, {"id": 2, "code": "water", "qty": 1}], "revision": 1}
    for _ in range(20):
        t += 0.2
        w.step(t)
    mark = w.memories[1]["marks"]["box"]
    assert mark["kind"] == "kitchen" and mark["left"] == 3 and mark["t"] <= t
    seen_at = mark["t"]
    a.loot_shelves["box"]["items"][0]["qty"] = 0
    for _ in range(20):
        t += 0.2
        w.step(t)
    assert w.memories[1]["marks"]["box"]["left"] == 1 and w.memories[1]["marks"]["box"]["t"] > seen_at
    out = memory.view(w, a)["marks"]
    assert out == [{"id": "box", "kind": "kitchen", "lat": mark["lat"], "lng": mark["lng"], "left": 1,
                    "age_s": out[0]["age_s"]}] and out[0]["age_s"] < 10
    # nothing about a container this player never opened
    w.stashes["secret"] = {"id": "secret", "lat": pos[0], "lng": pos[1], "kind": "chest", "loot": [("bandage", 1)]}
    w.step(t + 5)
    assert "secret" not in w.memories[1]["marks"]


def test_memory_outlives_the_survivor_and_records_where_they_fell():
    w, a, t = make()
    t = walk_east(w, a, t, 120)
    cells = dict(w.memories[1]["cells"])
    a.hp = 0
    a.death = {"cause": "killed"}
    w.step(t + 0.2)
    assert a.dead
    death = w.memories[1]["death"]
    assert death["cause"] == "killed" and abs(death["lat"] - a.lat) < 1e-5
    # the next life is a new Actor with the same player id: the memory is still there
    w.remove_actor(1)
    b = Actor(id=1, lat=0.0, lng=0.0, born=t)
    w.add_actor(b, t)
    w.step(t + 1)                                       # not placed yet: nothing is observed at 0,0
    assert w.memories[1]["cells"] == cells
    here = shift(LAT, LNG, 900, 0)
    b.lat, b.lng = here
    w.set_position(1, *here, 1.0)
    w.step(t + 2)
    assert set(cells) < set(w.memories[1]["cells"])
    assert memory.view(w, b)["death"]["age_s"] >= 0


def test_first_use_seeds_whole_blocks_from_the_current_life_without_inventing_contents():
    w = World(rng=random.Random(1))
    a = Actor(id=7, lat=LAT, lng=LNG, born=5 * DAY)
    a.explored = ["9zvxvf2", "9zvxvf3"]
    w.add_actor(a, 9 * DAY)
    mem = memory.for_player(w, a)
    assert len(mem["cells"]) == 64 and set(mem["cells"].values()) == {5}
    assert mem["marks"] == {} and mem["death"] is None and 7 in w.memory_dirty


async def test_memory_is_saved_reloaded_by_a_new_process_and_kept_by_the_next_life(maker):
    from app.auth import create_anonymous_player
    from app.game.hub import Hub
    from app.models import PlayerMemory

    async with maker() as s:
        player = (await create_anonymous_player(s, "m" * 20, "Rememberer"))["player"]

    async def send(_):
        pass

    def fresh_hub(now):
        hub = Hub()
        hub.world.spawner = None
        hub.director.policy = lambda *a: "quiet"
        hub.clock = lambda: now[0]
        return hub

    now = [2_000_000.0]
    hub = fresh_hub(now)
    conn, actor, _ = await hub.join(player, send)
    actor.lat, actor.lng = LAT, LNG
    hub.world.set_position(player.id, LAT, LNG, 1.0)
    for i in range(1, 120):                              # walk about 140 m east
        now[0] += 0.2
        hub.world.set_position(player.id, *shift(LAT, LNG, i * 1.2, 0), 1.0)
        hub.world.step(now[0])
    cells = dict(hub.world.memories[player.id]["cells"])
    assert len(cells) > 20
    await hub.save_all(force=True)
    async with maker() as s:
        assert (await s.get(PlayerMemory, player.id)).state["cells"] == cells

    # a replacement process knows nothing until the player returns
    hub2 = fresh_hub(now)
    assert player.id not in hub2.world.memories
    conn2, actor2, _ = await hub2.join(player, send)
    assert hub2.world.memories[player.id]["cells"] == cells
    hub2.world.step(now[0] + 1)
    assert set(cells) <= set(hub2.world.memories[player.id]["cells"])

    # death and a new survivor: the same remembered ground, plus where the last one fell
    actor2.hp, actor2.death = 0, {"cause": "killed"}
    hub2.world.step(now[0] + 2)
    assert actor2.dead
    reborn = await hub2.new_survivor(player, conn2)
    assert reborn is not actor2 and not reborn.dead
    mem = hub2.world.memories[player.id]
    assert set(cells) <= set(mem["cells"]) and mem["death"]["cause"] == "killed"
    await hub2.save_all(force=True)
    async with maker() as s:
        saved = (await s.get(PlayerMemory, player.id)).state
    assert set(cells) <= set(saved["cells"]) and saved["death"]["cause"] == "killed"

    # once the player has gone and everything is saved, the memory leaves RAM
    await hub2._drop(player.id, conn2, hub2.world.actors[player.id])
    await hub2.save_all(force=True)
    assert player.id not in hub2.world.memories


def test_pins_are_the_players_own_notes_bounded_and_not_an_action():
    w, a, t = make()
    a.channel = {"kind": "work", "ends": t + 30, "op": "rest"}
    last = a.last_action
    spot = shift(LAT, LNG, 120, -40)
    r = w.act(1, "pin", op="add", kind="supplies", lat=spot[0], lng=spot[1])
    assert r["ok"] and [p["kind"] for p in r["pins"]] == ["supplies"] and r["pins"][0]["age_s"] == 0
    assert a.channel is not None and a.last_action == last and not a.events      # writing on the map interrupts nothing
    assert 1 in w.memory_dirty
    w.act(1, "pin", op="add", kind="danger", lat=LAT, lng=LNG)
    seen = w.act(1, "memory", lat=LAT + 0.045, lng=LNG)                           # pins are few: all are sent, wherever one looks
    assert [p["kind"] for p in seen["pins"]] == ["supplies", "danger"]
    # nonsense is refused and stores nothing
    for bad in (dict(kind="treasure", lat=LAT, lng=LNG), dict(kind="note", lat=float("nan"), lng=LNG), dict(kind="note", lat="1", lng=LNG),
                dict(kind="note", lat=LAT + 0.2, lng=LNG), dict(kind="note")):
        assert not w.act(1, "pin", op="add", **bad)["ok"]
    assert not w.act(1, "pin", op="scribble")["ok"] and len(w.memories[1]["pins"]) == 2
    first = seen["pins"][0]["id"]
    assert [p["kind"] for p in w.act(1, "pin", op="remove", pin=first)["pins"]] == ["danger"]
    again = w.act(1, "pin", op="remove", pin=first)                               # a second tap on a slow connection
    assert not again["ok"] and len(again["pins"]) == 1
    for i in range(memory.MAX_PINS - 1):
        assert w.act(1, "pin", op="add", kind="note", lat=LAT + i * 1e-5, lng=LNG)["ok"]
    full = w.act(1, "pin", op="add", kind="note", lat=LAT, lng=LNG)
    assert not full["ok"] and "Remove one" in full["why"] and len(w.memories[1]["pins"]) == memory.MAX_PINS
    ids = [p["id"] for p in w.act(1, "memory")["pins"]]
    assert len(set(ids)) == memory.MAX_PINS and first not in ids                 # an id is never used twice


def test_used_up_resource_spots_are_marked_from_the_home_record():
    w, a, t = make()
    assert w.act(1, "memory")["spent"] == []
    near, far = shift(LAT, LNG, 60, 30), shift(LAT, LNG, 9000, 0)
    a.home = {"nodes": {"resource:9zvxvs1:0": 0, "resource:9zvxvs1:3": 2, "resource:9zvxvs1:4": 0, "resource:9zvxvs2:6": 0, "odd": 0},
              "node_positions": {"resource:9zvxvs1:0": list(near), "resource:9zvxvs1:3": list(near), "resource:9zvxvs2:6": list(far), "odd": list(near)}}
    spent = w.act(1, "memory")["spent"]
    assert [(m["id"], m["kind"]) for m in spent] == [("resource:9zvxvs1:0", "tree")]      # not the one with wood left, the far one or the one with no place
    assert abs(spent[0]["lat"] - near[0]) < 1e-5


def test_the_socket_lets_a_pin_and_its_fields_through():
    from app.routes.ws_routes import ACTIONS, ARGS
    assert "pin" in ACTIONS and {"op", "kind", "pin", "lat", "lng"} <= set(ARGS)       # a dropped `kind` made every pin a note
