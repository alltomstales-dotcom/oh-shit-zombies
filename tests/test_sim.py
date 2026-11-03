"""The simulation core, on a fake clock."""
import random

from app.game.content import STARTER_KIT
from app.game.sim import Actor, World, Zed, dist_m, shift

LAT, LNG = 44.9778, -93.2650


def make(seed=1, **tune):
    w = World(rng=random.Random(seed), tune=tune)
    a = Actor(id=1, lat=LAT, lng=LNG, born=-10 * 86400)   # an old survivor: no first-day grace
    for code, qty in STARTER_KIT:
        row = a.add(code, qty)
        if code == "bat":
            a.hands = row["id"]
    w.add_actor(a, 0.0)
    w.set_position(1, LAT, LNG, 1.0)
    return w, a


def zed_at(w, zid, east, north, **kw):
    lat, lng = shift(LAT, LNG, east, north)
    z = Zed(id=zid, lat=lat, lng=lng, home=(lat, lng), **kw)
    w.zeds[zid] = z
    return z


def run(w, seconds, t0=None, hz=5):
    t = w.now if t0 is None else t0
    for _ in range(int(seconds * hz)):
        t += 1.0 / hz
        w.step(t)
    return t


def test_zombie_notices_closes_and_grabs():
    w, a = make()
    z = zed_at(w, "a", 0, 15)
    run(w, 40)
    assert z.state == "engaged" and z.target == 1
    assert dist_m(a.lat, a.lng, z.lat, z.lng) < 3.0
    assert any(e["e"] == "groan" and e.get("you") for e in a.events)
    assert any(e["e"] == "grabbed" for e in a.events)


def test_far_zombie_does_not_notice():
    w, a = make()
    z = zed_at(w, "a", 0, 45)
    run(w, 30)
    assert z.target is None


def test_walking_away_outpaces_a_shambler():
    w, a = make()
    z = zed_at(w, "a", 0, 12, speed=0.85)
    t = run(w, 6)
    for i in range(300):                     # walk south at 1.4 m/s for a minute
        t += 0.2
        lat, lng = shift(LAT, LNG, 0, -1.4 * 0.2 * (i + 1))
        w.set_position(1, lat, lng, 1.0)
        w.step(t)
    assert z.state != "engaged"
    assert dist_m(a.lat, a.lng, z.lat, z.lng) > 20


def test_running_does_not_help():
    """The tracked position is capped, so sprinting in real life gains nothing extra."""
    w, a = make()
    t = run(w, 1)
    for i in range(50):                      # report 6 m/s for ten seconds
        t += 0.2
        lat, lng = shift(LAT, LNG, 0, -6.0 * 0.2 * (i + 1))
        w.set_position(1, lat, lng, 1.0, mode='gps')
        w.step(t)
    assert dist_m(LAT, LNG, a.lat, a.lng) < 2.2 * 10 + 1.0


def test_a_grabbed_survivor_cannot_walk_off():
    w, a = make()
    z = zed_at(w, "a", 0, 2)
    z.state, z.target, z.attack_at = "engaged", 1, 1e9
    t = run(w, 0.4)
    for i in range(50):
        t += 0.2
        lat, lng = shift(LAT, LNG, 0, -1.4 * 0.2 * (i + 1))
        w.set_position(1, lat, lng, 1.0)
        w.step(t)
    assert z.state == "engaged"
    assert dist_m(a.lat, a.lng, z.lat, z.lng) < 3.0


def test_unanswered_zombie_bites_on_its_clock():
    w, a = make()
    z = zed_at(w, "a", 0, 2)
    z.state, z.target, z.attack_at = "engaged", 1, 1.0
    run(w, 12)
    hits = [e for e in a.events if e["e"] in ("hit_you", "miss_you")]
    assert 3 <= len(hits) <= 6               # one attempt every 2.2 to 3.2 s
    assert a.hp < 100 and a.wounds


def test_swing_kills_and_costs_endurance():
    w, a = make()
    z = zed_at(w, "a", 0, 2, hp=20, hp_max=20)
    z.state, z.target, z.attack_at = "engaged", 1, 1e9
    t = run(w, 0.4)
    swings = 0
    while "a" in w.zeds and swings < 12:
        r = w.act(1, "swing")
        assert r["ok"], r
        swings += 1
        t = run(w, 0.8, t)
    assert "a" not in w.zeds and a.kills == 1
    assert a.end < 100
    assert "a" in w.dead_until


def test_swing_is_refused_while_recovering():
    w, a = make()
    zed_at(w, "a", 0, 2).state = "engaged"
    w.zeds["a"].target, w.zeds["a"].attack_at = 1, 1e9
    run(w, 0.4)
    assert w.act(1, "swing")["ok"]
    r = w.act(1, "swing")
    assert not r["ok"] and r["why"] == "busy"


def test_shove_then_finish_is_cheaper_than_swinging():
    w, a = make(shove_knockdown=1.0)
    z = zed_at(w, "a", 0, 2, hp=22, hp_max=22)
    z.state, z.target, z.attack_at = "engaged", 1, 1e9
    t = run(w, 0.4)
    assert w.act(1, "shove")["hit"][0]["down"]
    assert z.state == "down"
    t = run(w, 0.6, t)
    r = w.act(1, "swing")
    assert r["hit"] and r["finish"] and r.get("kill")
    assert a.end >= 100 - 5 - 9 - 0.01


def test_back_away_breaks_every_grip():
    w, a = make()
    for i, (e, n) in enumerate([(0, 2), (1.5, 1), (-1.5, 1)]):
        z = zed_at(w, f"z{i}", e, n)
        z.state, z.target, z.attack_at = "engaged", 1, 1e9
    t = run(w, 0.4)
    assert w.act(1, "back")["ok"]
    run(w, 1.0, t)
    assert all(z.state == "stagger" for z in w.zeds.values())
    assert all(dist_m(a.lat, a.lng, z.lat, z.lng) > 5 for z in w.zeds.values())
    assert not w.act(1, "back")["ok"]        # cooldown, and nothing has hold now


def test_bandage_takes_time_and_a_hit_interrupts_it():
    w, a = make()
    a.wounds.append({"id": 1, "kind": "laceration", "part": "torso", "bleeding": True,
                     "bandaged": False, "clean": False, "t": 0.0})
    t = run(w, 0.4)
    assert w.act(1, "bandage")["ok"]
    t = run(w, 2.0, t)
    assert a.wounds[0]["bleeding"]           # not done yet
    t = run(w, 2.0, t)
    assert not a.wounds[0]["bleeding"] and a.count("bandage") == 1
    # second wound, interrupted by a bite
    a.wounds.append({"id": 2, "kind": "scratch", "part": "neck", "bleeding": True,
                     "bandaged": False, "clean": False, "t": t})
    assert w.act(1, "bandage")["ok"]
    z = zed_at(w, "a", 0, 2)
    z.state, z.target, z.attack_at = "engaged", 1, t + 0.5
    w.T["attack_miss"] = 0.0
    run(w, 1.5, t)
    assert a.channel is None and a.count("bandage") == 1
    assert any(e["e"] == "interrupted" for e in a.events)


def test_bleeding_drains_health_and_health_does_not_come_back():
    w, a = make()
    a.wounds.append({"id": 1, "kind": "laceration", "part": "torso", "bleeding": True,
                     "bandaged": False, "clean": False, "t": 0.0})
    run(w, 20)
    assert 94 < a.hp < 96
    a.wounds[0]["bleeding"] = False
    hp = a.hp
    run(w, 60)
    assert a.hp == hp


def test_a_bite_always_infects_and_infection_kills_on_its_clock():
    w, a = make(wound_weights={"scratch": 0, "laceration": 0, "bite": 1}, attack_miss=0.0)
    z = zed_at(w, "a", 0, 2)
    z.state, z.target, z.attack_at = "engaged", 1, 0.5
    t = run(w, 1.0)
    assert a.infected_at is not None and 24 * 3600 <= a.turns_at - a.infected_at <= 48 * 3600
    del w.zeds["a"]
    a.wounds[0]["bleeding"] = False
    w.step(a.turns_at + 1)
    assert a.dead and a.death["cause"] == "turned"


def test_being_mobbed_is_fast():
    """Five on you with nothing done about it: dead inside half a minute."""
    w, a = make(seed=3)
    for i in range(5):
        z = zed_at(w, f"z{i}", i - 2, 2)
        z.state, z.target, z.attack_at = "engaged", 1, 1.0 + i * 0.3
    t = 0.0
    while not a.dead and t < 120:
        t += 0.2
        w.step(t)
    assert a.dead and t < 40
    assert a.death["cause"] in ("killed", "bled out")
    assert any(e["e"] == "died" for e in a.events)


def test_panic_rises_with_numbers_and_settles():
    w, a = make()
    for i in range(3):
        z = zed_at(w, f"z{i}", i, 2)
        z.state, z.target, z.attack_at = "engaged", 1, 1e9
    t = run(w, 3)
    assert a.panic > 60
    w.zeds.clear()
    run(w, 30, t)
    assert a.panic < 5


def test_endurance_returns_only_once_free():
    w, a = make()
    a.end = 40
    z = zed_at(w, "a", 0, 2)
    z.state, z.target, z.attack_at = "engaged", 1, 1e9
    t = run(w, 5)
    assert a.end == 40
    w.zeds.clear()
    run(w, 10, t)
    assert a.end > 55


def test_view_hides_what_is_out_of_sight():
    w, a = make()
    zed_at(w, "near", 0, 30)
    zed_at(w, "far", 0, 80)
    w.step(0.2)
    ids = [r[0] for r in w.view(1)["z"]]
    assert ids == ["near"]


def test_movement_capacity_tracks_endurance_and_injury():
    w, a = make()
    fresh = w.movement_speed(a)
    assert fresh == 6.0
    a.end = 0
    exhausted = w.movement_speed(a)
    assert 1.0 < exhausted < fresh
    a.wounds.append({"part": "left shin", "bleeding": False, "kind": "scratch"})
    injured = w.movement_speed(a)
    assert injured < exhausted
    a.hp = 20
    assert w.movement_speed(a) < injured
    assert w.view(a.id)["you"]["walk_speed"] == round(w.movement_speed(a), 3)


def test_exploration_speed_triples_but_combat_and_wounds_keep_penalties():
    w,a=make()
    assert w.movement_speed(a)==6
    z=zed_at(w,'combat',2,0,state='engaged',target=a.id)
    assert w.movement_speed(a)==2
    a.end=0
    hurt_combat=w.movement_speed(a)
    z.state='dead'
    assert abs(w.movement_speed(a)-hurt_combat*3)<1e-9



def test_sprint_multiplies_pace_and_spends_stamina_only_when_moving():
    w,a=make()
    assert w.act(a.id,'sprint',op='start')['ok']
    assert w.movement_speed(a)==24
    w.step(.2)
    assert a.end==100
    w.set_position(a.id,*shift(a.lat,a.lng,20,0),1,mode='desk')
    w.step(.4)
    assert a.walked_m>4 and a.end<98
    a.end=.1
    w.step(.6)
    assert a.end==0 and not a.sprinting
    assert not w.act(a.id,'sprint',op='start')['ok']
    assert w.act(a.id,'sprint',op='stop')['ok']
    assert a.xp==0


def test_walking_spends_endurance_and_stopping_recovers_it():
    w, a = make()
    w.set_position(a.id, *shift(LAT, LNG, 0, 20), 1.0)
    run(w, 3)
    assert a.walked_m > 4 and a.end < 100
    w.set_position(a.id, a.lat, a.lng, 1.0)
    run(w, 5)
    assert a.end == 100


def test_injured_gps_walker_stays_with_normal_walk_without_transit():
    w, a = make()
    a.end, a.hp = 0, 25
    a.wounds = [{"part": p, "kind": "scratch", "bleeding": False} for p in ("left shin", "right thigh")]
    assert w.movement_speed(a) / 3 < 1.4
    for i in range(900):  # three minutes of ordinary walking with an 8m GPS fix
        lat, lng = shift(LAT, LNG, 0, 1.4 * .2 * (i + 1))
        w.set_position(a.id, lat, lng, 8.0, mode="gps")
        w.step((i + 1) * .2)
        assert dist_m(a.lat, a.lng, lat, lng) < 5
        assert a.transit_until <= w.now


def test_gps_speed_is_still_capped():
    w, a = make()
    for i in range(50):
        lat, lng = shift(LAT, LNG, 0, 6 * .2 * (i + 1))
        w.set_position(a.id, lat, lng, 1.0, mode="gps")
        w.step((i + 1) * .2)
    assert dist_m(LAT, LNG, a.lat, a.lng) < 21


def test_switching_from_gps_restores_injury_movement_limit():
    w, a = make()
    a.end = 0
    w.set_position(a.id, *shift(LAT, LNG, 0, 20), 1, mode="gps")
    w.step(.2)
    before = (a.lat, a.lng)
    w.set_position(a.id, *shift(LAT, LNG, 0, 20), 1, mode="desk")
    w.step(.4)
    assert a.position_mode == "desk"
    assert .7 < dist_m(*before, a.lat, a.lng) < .75  # exhausted exploration pace, 3x combat


def test_scream_pulls_visible_radius_zombies_and_has_cooldown():
    w, a = make()
    near = zed_at(w, "near", 0, 54)
    far = zed_at(w, "far", 0, 57)
    assert w.act(a.id, "scream") == {"ok": True, "radius": 55.0}
    assert near.state == "investigate" and near.goal == (a.lat, a.lng)
    assert far.state == "idle"
    assert a.events[-1]["e"] == "scream" and not a.events[-1]["involuntary"]
    assert not w.act(a.id, "scream")["ok"]
    w.now = 10
    assert w.act(a.id, "scream")["ok"]


def test_scream_radius_tracks_night_view_and_cannot_pull_dead_or_engaged():
    w, a = make()
    w.light_fn = lambda *args: 0
    near = zed_at(w, "near", 0, 21)
    far = zed_at(w, "far", 0, 24)
    down = zed_at(w, "down", 0, 5, state="down")
    held = zed_at(w, "held", 0, 2, state="engaged", target=a.id)
    assert w.act(a.id, "scream")["radius"] == 22
    assert near.state == "investigate" and far.state == "idle"
    assert down.state == "down" and held.state == "engaged"
    a.dead = True
    assert not w.act(a.id, "scream")["ok"]


def test_panic_scream_is_random_and_obeys_cooldown():
    w, a = make(panic_scream_per_s=1000, panic_down=0)
    a.panic = 100
    near = zed_at(w, "near", 0, 50)
    w._step_actor(a, .2)
    events = [e for e in a.events if e["e"] == "scream"]
    assert len(events) == 1 and events[0]["involuntary"]
    assert near.state == "investigate"
    for i in range(1, 100):
        w.now = i * .2
        w._step_actor(a, .2)
    assert len([e for e in a.events if e["e"] == "scream"]) == 1
    w.now = 21
    w._step_actor(a, .2)
    assert len([e for e in a.events if e["e"] == "scream"]) == 2


def test_calm_or_disconnected_survivor_does_not_scream_automatically():
    w, a = make(panic_scream_per_s=1000)
    w._step_actor(a, 1)
    assert not any(e["e"] == "scream" for e in a.events)
    a.panic, a.connected = 100, False
    w._step_actor(a, 1)
    assert not any(e["e"] == "scream" for e in a.events)


def test_a_player_in_another_city_never_costs_a_wall_test():
    """Noise, melee and views must filter by distance before testing walls.

    The wall test walks a map grid between its two points. Between two cities that is
    billions of steps, which once froze the live server for every player.
    """
    w, a = make()
    far = Actor(id=2, lat=41.9484, lng=-87.74, born=-10 * 86400)     # Chicago, 570 km away
    w.add_actor(far, 0.0)
    w.set_position(2, far.lat, far.lng, 1.0)
    w.zeds["chi"] = Zed(id="chi", lat=41.9514, lng=-87.74, home=(41.9514, -87.74))   # idle, out of its sight
    w.zeds["chi2"] = Zed(id="chi2", lat=41.94841, lng=-87.74, home=(41.94841, -87.74))  # one beside player 2
    near = zed_at(w, "mpls", 0, 6)
    spans = []
    real = w.buildings.clear

    def spy(p, q, *args, **kw):
        spans.append(dist_m(p[0], p[1], q[0], q[1]))
        return real(p, q, *args, **kw)

    w.buildings.clear = spy
    t = run(w, 2)
    w.noise(a.lat, a.lng, 55, a)
    w.act(1, "scream")
    w.act(1, "swing")
    w.act(1, "shove")
    w.act(2, "swing")
    run(w, 3, t)
    w.view(1), w.view(2), w.body(a), w.body(far)
    assert spans and max(spans) < 400
    assert near.state != "idle"                       # the nearby one still heard it
    assert w.zeds["chi"].state == "idle"              # and the far one was not drawn across the map


def test_a_survivor_who_has_just_appeared_is_not_noticed_at_once():
    w, a = make()
    a.born = 1000.0                                   # a brand-new life
    z = zed_at(w, "a", 0, 4)
    t = run(w, 30, t0=1000.0)
    assert z.target is None and a.hp == 100           # half a minute to look around
    t = run(w, 40, t)
    assert z.target == 1                              # then the street behaves as usual


def test_walking_off_ends_the_arrival_calm():
    w, a = make()
    a.born = 1000.0
    a.walked_m = 20.0
    z = zed_at(w, "a", 0, 4)
    run(w, 25, t0=1000.0)
    assert z.target == 1


def test_view_combat_target_matches_server_finish_choice():
    w=World();a=Actor(id=99,lat=44.9778,lng=-93.265);w.add_actor(a,100)
    for id,metres,hp in [('near',1,60),('weak',4,5)]:
        lat,lng=shift(a.lat,a.lng,metres,0)
        z=Zed(id=id,lat=lat,lng=lng,state='down',hp=hp);w.zeds[id]=z
    assert w.view(a.id)['you']['combat']['swing']=='weak'
    w.zeds.clear()
    assert w.view(a.id)['you']['combat']['swing'] is None
