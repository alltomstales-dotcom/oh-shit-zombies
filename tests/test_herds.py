"""A herd is one walking thing until it notices someone.

It comes from a schedule that depends only on the place and the real clock, it is brought into the
world out of sight, it costs one object while it walks, and it turns into its zombies once.
"""
import math
import random

from app.game import herds
from app.game.buildings import Building
from app.game.content import TUNE
from app.game.sim import Actor, World, dist_m, shift
from tools.geometry_load import BASE, town

T0 = 5_000_000.0


def _world(at=BASE, now=T0, **tune):
    w = World(rng=random.Random(3), tune=tune or None)
    a = Actor(id=1); a.lat, a.lng = at; w.add_actor(a, now)
    return w, a


def _run(w, seconds, hz=5):
    for _ in range(int(seconds * hz)):
        w.step(w.now + 1 / hz)


def _said(a, op):
    return [e for e in a.events if e["e"] == "herd" and e["op"] == op]


def test_the_schedule_is_the_same_for_everyone_and_walks_a_straight_line():
    c = herds.next_crossing(*BASE, T0); assert c is not None
    herds._crossing.cache_clear()
    assert herds.next_crossing(*BASE, T0) == c                       # nothing but place and clock goes into it
    assert TUNE["herd_min"] <= c["count"] <= TUNE["herd_max"] and c["t1"] - c["t0"] == TUNE["herd_cross_s"]
    assert herds.planned(c, c["t0"] - 50) == c["start"]
    end = herds.planned(c, c["t1"] + 50)
    assert abs(dist_m(*c["start"], *end) - TUNE["herd_speed"] * TUNE["herd_cross_s"]) < 1
    mid = herds.planned(c, (c["t0"] + c["t1"]) / 2)
    assert [d["id"] for d in herds.due(*mid, c["t0"] + 5)] .count(c["id"]) == 1
    assert c["id"] not in [d["id"] for d in herds.due(*mid, c["t0"] - 5)]
    blocks = [herds._crossing(c["id"].split(":")[0], b) for b in range(4000)]
    share = sum(x is not None for x in blocks) / len(blocks)
    assert abs(share - TUNE["herd_chance"]) < 0.04


def test_a_scheduled_herd_comes_in_out_of_sight_and_never_beside_a_new_survivor():
    c = herds.next_crossing(*BASE, T0); now = c["t0"] + 600; p = herds.planned(c, now)
    w, a = _world(shift(*p, 200, 0), now); _run(w, 1)
    h = w.herds[c["id"]]
    assert h.count == c["count"] and not w.zeds and dist_m(h.lat, h.lng, *p) < 2
    near, _ = _world(shift(*p, 60, 0), now); _run(near, 1)
    assert not near.herds                                            # it would have appeared in plain view
    new, b = _world(shift(*p, 200, 0), now); b.born = now - 100; _run(new, 1)
    assert not new.herds
    far, _ = _world(shift(*p, 400, 0), now); _run(far, 1)
    assert not far.herds                                             # nobody near enough for it to matter


def test_walking_it_is_one_thing_heard_first_then_seen_and_hidden_by_a_wall():
    w, a = _world()
    h = w.add_herd(shift(*BASE, 130, 0), 60, heading=math.pi / 2)
    _run(w, 10)
    assert not w.zeds and len(w.herds) == 1
    assert 4.5 < dist_m(h.lat, h.lng, *shift(*BASE, 130, 0)) < 5.1 and h.lat > BASE[0]     # half a metre a second, north
    assert len(_said(a, "heard")) == 1 and not _said(a, "seen") and w.view(1)["herds"] == []
    h.lat, h.lng = shift(*BASE, 90, 0)
    _run(w, 2)
    rows = w.view(1)["herds"]
    assert len(_said(a, "seen")) == 1 and len(_said(a, "heard")) == 1 and not w.zeds
    assert [r[0] for r in rows] == [h.id] and rows[0][3] == 60 and rows[0][4] == h.seed % 720
    house = Building(id="house", outline=[list(shift(*BASE, x, y)) for x, y in ((5, -5), (14, -5), (14, 5), (5, 5))])
    w.buildings.items[house.id] = house
    assert w.view(1)["herds"] == []
    a.lat, a.lng = shift(*BASE, 0, 900); _run(w, 1)
    assert not w.herds                                               # nobody left to meet it


def test_the_figures_are_a_narrow_column_along_the_way_it_faces():
    L, W = herds.spread(60); pts = herds.offsets(60, 77, 0.0)
    assert len(pts) == 60 and max(abs(x) for x, _ in pts) <= L and max(abs(y) for _, y in pts) <= W and L > 3 * W
    turned = herds.offsets(60, 77, math.pi / 2)
    assert all(abs(x + ty) < 1e-9 and abs(y - tx) < 1e-9 for (x, y), (ty, tx) in zip(turned, [(y, x) for x, y in pts]))
    assert herds.offsets(60, 77, 0.0) == pts and herds.offsets(60, 78, 0.0) != pts


def test_noticing_someone_turns_it_into_its_zombies_once():
    c = herds.next_crossing(*BASE, T0); now = c["t0"] + 600; p = herds.planned(c, now)
    w, a = _world(shift(*p, 200, 0), now); _run(w, 1)
    h = w.herds[c["id"]]; n = h.count
    a.lat, a.lng = shift(h.lat, h.lng, 8, 0)
    _run(w, 0.4)
    assert not w.herds and len(w.zeds) == n
    assert all(z.id.startswith(f"h:{c['id']}:") and z.kind == "shambler" and z.target == 1 and z.temp for z in w.zeds.values())
    assert len({z.id for z in w.zeds.values()}) == n and len(_said(a, "woke")) == 1 and _said(a, "woke")[0]["mine"]
    spots = {(round(z.lat, 6), round(z.lng, 6)) for z in w.zeds.values()}
    assert len(spots) > n * 0.9                                      # spread as the crowd was drawn, not a pile
    w.zeds.clear(); w.herd_woken.clear()
    a.lat, a.lng = shift(*herds.planned(c, w.now), 200, 0); _run(w, 3)
    assert not w.herds and c["id"] in w.herd_spent                   # the schedule does not bring it back


def test_keeping_low_gets_past_and_a_new_arrival_is_not_noticed():
    w, a = _world(); a.quiet = True
    w.add_herd(shift(*BASE, 15, 0), 60, heading=math.pi / 2)
    _run(w, 12)
    assert w.herds and not w.zeds
    a.quiet = False
    _run(w, 12)
    assert not w.herds and len(w.zeds) == 60                          # standing in the open at fifteen metres does not
    w, a = _world(); a.placed_at = w.now
    w.add_herd(shift(*BASE, 8, 0), 60, heading=math.pi / 2)
    _run(w, 5)
    assert w.herds and not w.zeds


def test_a_loud_noise_turns_all_of_it_and_one_made_beside_it_shows_who_made_it():
    w, a = _world()
    h = w.add_herd(shift(*BASE, 0, 80), 60, heading=0.0)
    w.noise(a.lat, a.lng, 140, a)
    assert w.herds and not w.zeds
    _run(w, 20)
    assert w.herds and dist_m(h.lat, h.lng, *BASE) < 72 and abs(dist_m(h.lat, h.lng, *shift(*BASE, 0, 80)) - 10) < 0.6
    w, a = _world()
    w.add_herd(shift(*BASE, 0, 40), 60, heading=0.0)
    w.noise(a.lat, a.lng, 140, a)
    assert not w.herds and len(w.zeds) == 60 and all(z.target == 1 for z in w.zeds.values())
    w, a = _world()
    h = w.add_herd(shift(*BASE, 0, 80), 60, heading=0.0)
    w.noise(a.lat, a.lng, 45, a)                                     # out of earshot: nothing
    assert h.detour_until == 0.0


def test_those_left_gather_again_when_none_of_them_is_after_anyone():
    w, a = _world(herd_regather_s=5.0)
    b = Actor(id=2); b.lat, b.lng = shift(*BASE, 0, 300); w.add_actor(b, T0)
    h = w.add_herd(shift(*BASE, 8, 0), 60, heading=0.0); hid = h.id
    _run(w, 0.4)
    assert len(w.zeds) == 60 and hid in w.herd_woken
    for z in list(w.zeds.values())[:20]:
        z.state = "dead"
    a.lat, a.lng = shift(*BASE, 0, 310)                               # gone: they lose whoever it was
    _run(w, 40)
    assert hid in w.herds and w.herds[hid].count == 40 and hid not in w.herd_woken
    assert not [z for z in w.zeds.values() if z.alive]
    assert dist_m(w.herds[hid].lat, w.herds[hid].lng, *BASE) < 60


def test_a_handful_left_stay_zombies():
    w, a = _world(herd_regather_s=5.0)
    b = Actor(id=2); b.lat, b.lng = shift(*BASE, 0, 300); w.add_actor(b, T0)
    w.add_herd(shift(*BASE, 8, 0), 60, heading=0.0)
    _run(w, 0.4)
    for zid in list(w.zeds)[5:]:
        del w.zeds[zid]
    a.lat, a.lng = shift(*BASE, 0, 310)
    _run(w, 40)
    assert not w.herds and not w.herd_woken and len(w.zeds) == 5


def test_it_keeps_to_the_streets():
    c, records = town(0, 144)
    w, a = _world(shift(*c, -5, -230)); w.buildings.add(records)
    start = shift(*c, -5, -7)
    h = w.add_herd(start, 60, heading=0.3)
    for _ in range(900):
        w.step(w.now + 0.2)
        assert w.buildings.containing((h.lat, h.lng)) is None
    assert w.herds and not w.zeds and dist_m(h.lat, h.lng, *start) > 12


def test_an_open_door_does_not_let_the_crowd_indoors():
    c, records = town(0, 16)
    w, a = _world(shift(*c, -5, -230)); w.buildings.add(records)
    b = next(iter(w.buildings.items.values())); door = next(o for o in b.openings if o["label"] == "Entrance")
    door["open"] = True; w.buildings.revision += 1
    mid = ((door["a"][0] + door["b"][0]) / 2, (door["a"][1] + door["b"][1]) / 2)
    out, inn = b.ll((mid[0] + 2.0, mid[1])), b.ll((mid[0] - 2.0, mid[1]))
    assert w.buildings.containing(inn) is b and w.buildings.containing(out) is None
    assert w.buildings.move(out, inn) == inn                          # one zombie could walk in here
    h = w.add_herd(out, 60, heading=math.pi)
    for _ in range(150):
        w.step(w.now + 0.2)
        assert w.buildings.containing((h.lat, h.lng)) is None
    assert h.detour_until > 0                                         # it turned aside instead


def test_a_building_mapped_on_top_of_it_does_not_trap_it():
    c, records = town(0, 16)
    w, a = _world(shift(*c, -5, -230))
    late = World(); late.buildings.add(records); b = next(iter(late.buildings.items.values()))
    x0, y0, x1, y1 = b.bounds; inside = b.ll(((x0 + x1) / 2, (y0 + y1) / 2))
    h = w.add_herd(inside, 60, heading=0.0)
    _run(w, 2)
    w.buildings.add(records)                                          # the footprints of this street arrive
    assert w.buildings.containing((h.lat, h.lng)) is not None
    _run(w, 0.4)
    assert w.herds and w.buildings.containing((h.lat, h.lng)) is None and dist_m(h.lat, h.lng, *inside) < 15
    there = (h.lat, h.lng)
    _run(w, 30)
    assert dist_m(h.lat, h.lng, *there) > 5                           # and it walks on


def test_it_goes_round_a_long_building_one_way_instead_of_bouncing_off_it():
    w, a = _world(shift(*BASE, 0, -230))
    hall = Building(id="hall", outline=[list(shift(*BASE, x, y)) for x, y in ((-30, 10), (30, 10), (30, 22), (-30, 22))])
    w.buildings.items[hall.id] = hall
    h = w.add_herd(BASE, 60, heading=math.pi / 2)                     # due north, into the middle of the long side
    for _ in range(1500):
        w.step(w.now + 0.2)
        assert w.buildings.containing((h.lat, h.lng)) is None
        if h.lat > shift(*BASE, 0, 24)[0]:
            break
    assert h.lat > shift(*BASE, 0, 24)[0], "still on the near side after five minutes"
