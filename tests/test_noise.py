"""How loud a survivor is depends on pace; a knock wakes what is inside."""
import random

from app.game.buildings import Building
from app.game.sim import Actor, World, Zed, dist_m, shift

LAT, LNG = 44.9778, -93.2650


def make(seed=1, light=1.0, **tune):
    w = World(rng=random.Random(seed), tune=tune, light_fn=lambda *_: light)
    a = Actor(id=1, lat=LAT, lng=LNG, born=-10 * 86400)
    w.add_actor(a, 0.0)
    w.set_position(1, LAT, LNG, 1.0)
    return w, a


def zed_at(w, zid, east, north, **kw):
    lat, lng = shift(LAT, LNG, east, north)
    z = Zed(id=zid, lat=lat, lng=lng, home=(lat, lng), **kw)
    w.zeds[zid] = z
    return z


def walk_east(w, a, metres, pace, t=0.0, hz=5):
    """Lead the survivor east the way a client does: a target a little ahead every tick."""
    x = 0.0
    while x < metres:
        x += pace / hz
        t += 1.0 / hz
        w.set_position(1, *shift(LAT, LNG, x, 0), 1.0)
        w.step(t)
    return t


def test_heard_distance_follows_pace():
    w, a = make()
    T = w.T
    assert w.heard_m(a) == T["noise_still_m"]
    for speed, key in ((1.0, "noise_quiet_m"), (2.0, "noise_walk_m"), (6.0, "noise_travel_m")):
        a.speed = speed
        assert w.heard_m(a) == T[key]
    a.sprinting = True
    assert w.heard_m(a) == T["noise_sprint_m"]
    assert T["noise_quiet_m"] < T["noise_walk_m"] < T["noise_travel_m"] < T["noise_sprint_m"]


def test_quiet_and_sprint_exclude_each_other_and_quiet_caps_pace():
    w, a = make()
    fast = w.movement_speed(a)
    assert w.act(1, "quiet", op="start")["quiet"] and a.quiet
    assert w.movement_speed(a) == w.T["quiet_speed"] < fast
    assert w.act(1, "sprint", op="start")["ok"] and a.sprinting and not a.quiet
    assert w.act(1, "quiet", op="start")["ok"] and a.quiet and not a.sprinting
    assert w.act(1, "quiet", op="stop")["ok"] and not a.quiet
    assert not w.act(1, "quiet", op="crawl")["ok"]
    assert w.view(1)["you"]["quiet"] is False


def pass_by(mode, lateral, metres, seed=3):
    """Walk east past a line of unaware zombies standing `lateral` metres to the north, in daylight."""
    w, a = make(seed=seed)
    zs = [zed_at(w, f"z{i}", 6 + i * 6, lateral) for i in range(int(metres / 6))]
    if mode in ("quiet", "sprint"):
        w.act(1, mode, op="start")
    walk_east(w, a, metres, pace=w.movement_speed(a))
    return any(z.target == 1 for z in zs)


def test_creeping_past_at_fifteen_metres_is_not_noticed_but_walking_is():
    # Noticing is a chance per second, so this is a rate, not one seed: one seed was 30% likely to fail
    # by design (12 of 40 creeping passes were noticed before the wander change of 2026-11-03, 14 after).
    quiet = sum(pass_by("quiet", 15, 30, seed=s) for s in range(20))
    travel = sum(pass_by("travel", 15, 30, seed=s) for s in range(20))
    assert quiet <= 10 and travel >= 18


def test_a_sprint_is_heard_beyond_sight_and_a_walk_is_not():
    assert not pass_by("travel", 28, 150)
    assert pass_by("sprint", 28, 150)


def test_a_chasing_zombie_is_not_shaken_off_by_creeping_in_plain_sight():
    w, a = make()
    z = zed_at(w, "a", 0, 14)
    z.state, z.target, z.last_seen = "chase", 1, 0.0
    w.act(1, "quiet", op="start")
    a.speed = 1.0
    assert w.creeping(a)
    t = 0.0
    for _ in range(100):                      # 20 s, longer than lose_after_s
        t += 0.2
        a.speed = 1.0
        w.step(t)
        if z.state == "engaged":
            break
    assert z.target == 1 and z.state in ("chase", "engaged")


def house(w):
    b = Building(id="test:house", outline=[list(shift(LAT, LNG, x, y)) for x, y in ((4, -6), (24, -6), (24, 6), (4, 6))])
    w.buildings.items[b.id] = b
    return b


def test_feet_carry_through_a_wall_only_when_loud_and_close():
    # The survivor passes 3 m outside the west wall; a zombie stands 2 m inside it: 5 m apart.
    results = {}
    for mode in ("quiet", "walk", "sprint"):
        w, a = make(seed=5)
        b = house(w)
        a.lat, a.lng = shift(LAT, LNG, 1, -12)
        z = Zed(id="in", lat=0, lng=0)
        z.lat, z.lng = shift(LAT, LNG, 6, 0)
        z.home = (z.lat, z.lng)
        w.zeds["in"] = z
        assert b.contains((z.lat, z.lng)) and not w.visible((a.lat, a.lng), (z.lat, z.lng))
        if mode != "walk":
            w.act(1, mode, op="start")
        t, y = 0.0, -12.0
        pace = w.movement_speed(a)
        while y < 12:
            y += pace / 5
            t += 0.2
            w.set_position(1, *shift(LAT, LNG, 1, y), 1.0)
            w.step(t)
        for _ in range(40):                   # and stand a while at the far end
            t += 0.2
            w.step(t)
        results[mode] = z.target == 1
    assert results == {"quiet": False, "walk": True, "sprint": True}


def test_knock_brings_an_occupant_to_the_door_and_an_empty_house_stays_silent():
    w, a = make(seed=2)
    b = house(w)
    door = next(o for o in b.openings if o["label"] == "Entrance")
    centre = tuple((p + q) / 2 for p, q in zip(door["a"], door["b"]))
    at = b.ll(centre)
    mid = (sum(p[0] for p in b.poly) / len(b.poly), sum(p[1] for p in b.poly) / len(b.poly))
    out = (centre[0] - mid[0], centre[1] - mid[1])
    n = (out[0] ** 2 + out[1] ** 2) ** 0.5
    out = (out[0] / n, out[1] / n)
    a.lat, a.lng = b.ll((centre[0] + out[0] * 1.2, centre[1] + out[1] * 1.2))
    w.set_position(1, a.lat, a.lng, 1.0)
    assert not b.contains((a.lat, a.lng))

    # nobody home
    assert w.act(1, "opening", opening=door["id"], op="knock")["ok"]
    t = 0.0
    for _ in range(30):
        t += 0.2
        w.step(t)
    assert not any(e["e"] == "groan" for e in a.events)

    # one inside, out of sight behind the closed door
    z = Zed(id="in", lat=0, lng=0)
    z.lat, z.lng = b.ll((centre[0] - out[0] * 4.5, centre[1] - out[1] * 4.5))
    assert b.contains((z.lat, z.lng)) and not w.visible((a.lat, a.lng), (z.lat, z.lng))
    z.home = (z.lat, z.lng)
    z.next_groan = 1e9
    w.zeds["in"] = z
    start = dist_m(z.lat, z.lng, *at)
    a.events.clear()
    a.busy_until = 0
    assert w.act(1, "opening", opening=door["id"], op="knock")["ok"]
    assert z.state == "investigate"
    for _ in range(40):
        t += 0.2
        w.step(t)
    groans = [e for e in a.events if e["e"] == "groan"]
    assert groans and not groans[0]["seen"] and "z" not in groans[0]
    assert dist_m(z.lat, z.lng, *at) < start - 1.0
    assert not door["open"]

    # an open door has nothing to knock on
    door["open"] = True
    a.busy_until = 0
    assert not w.act(1, "opening", opening=door["id"], op="knock")["ok"]
