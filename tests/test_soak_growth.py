"""What the soak of 2 November let pile up: zombie bodies and dropped weapons. Both now go away,
and a frame's wall tests no longer grow with how many lie about."""
from app.game import corpses
from app.game.sim import Actor, World, Zed, dist_m, shift, DROP_KEEP_S, DROP_VIEW_LIMIT

LAT, LNG = 41.8807, -87.6278


class Spawner:
    def expires(self, now):
        return now + 86400.0


def test_zombie_bodies_rot_after_thirty_minutes_but_survivor_packs_keep():
    w = World(); w.spawner = None; a = Actor(id=1, lat=LAT, lng=LNG); w.add_actor(a, 1000.0); w.now = 1000.0
    z = Zed(id='z1', lat=LAT, lng=LNG); w.zeds[z.id] = z; w._kill(z, a)
    body = next(b for b in w.corpses.values() if b['kind'] == 'shambler')
    assert body['until'] == 1000.0 + corpses.ZOMBIE_BODY_S
    w.step(1000.0 + corpses.ZOMBIE_BODY_S + 1)
    assert body['id'] not in w.corpses
    pack = corpses.survivor(Actor(id=2, lat=LAT, lng=LNG, life_id=1), 1000.0)
    assert pack['until'] == 1000.0 + corpses.RECOVERY_S


def test_dropped_weapons_go_after_their_time():
    w = World(); a = Actor(id=1, lat=LAT, lng=LNG); w.add_actor(a, 100.0); w.now = 100.0
    row = a.add('bat', 1, 10); a.hands = row['id']
    w._drop_hands(a)
    assert len(w.drops) == 1
    w.step(100.0 + DROP_KEEP_S - 10)
    assert len(w.drops) == 1
    w.step(100.0 + DROP_KEEP_S + 10)
    assert not w.drops


def test_frame_shows_nearest_bodies_and_drops_and_stops_wall_testing_at_the_limit():
    w = World(); a = Actor(id=1, lat=LAT, lng=LNG); w.add_actor(a, 100.0); w.now = 100.0
    for i in range(200):
        lat, lng = shift(LAT, LNG, (i % 20) - 10, (i // 20) - 5)
        w.corpses[f'b{i}'] = {'id': f'b{i}', 'lat': lat, 'lng': lng, 'kind': 'shambler', 'variant': 0,
                              'until': 1e9, 'items': [], 'searched': False, 'revision': 1}
        w.drops[f'd{i}'] = {'id': f'd{i}', 'lat': lat, 'lng': lng, 'code': 'bat', 'qty': 1, 'cond': 5, 't': 100.0}
    calls = []
    real = w.visible
    w.visible = lambda p, q: calls.append(1) or real(p, q)
    shown = corpses.visible(w, a)
    assert len(shown) == corpses.VIEW_LIMIT and len(calls) == corpses.VIEW_LIMIT
    far = max(dist_m(LAT, LNG, b['lat'], b['lng']) for b in shown)
    hidden = [b for b in w.corpses.values() if b['id'] not in {s['id'] for s in shown}]
    assert all(dist_m(LAT, LNG, b['lat'], b['lng']) >= far - 1e-9 for b in hidden)
    calls.clear()
    assert len(w._visible_drops(a, w.sight_m(a))) == DROP_VIEW_LIMIT and len(calls) == DROP_VIEW_LIMIT


def test_an_idle_zombie_shuffles_as_far_in_chunks_as_it_did_every_tick():
    w = World(); w.now = 0.0
    a = Actor(id=1, lat=LAT + 40 / 111320, lng=LNG); w.add_actor(a, 0.0)   # someone 40 m off: awake, unnoticed
    z = Zed(id='w1', lat=LAT, lng=LNG, home=(LAT, LNG)); w.zeds[z.id] = z
    z.goal = shift(LAT, LNG, 10.0, 0.0)
    walks = []
    real = w._walk
    w._walk = lambda *args: walks.append(1) or real(*args)
    t = 0.0
    for _ in range(30):                                  # six seconds
        t += 0.2; z.sleep_until = 0.0; w._step_zeds(0.2); w.now = t
    moved = dist_m(LAT, LNG, z.lat, z.lng)
    assert abs(moved - 0.22 * 6) < 0.25                   # wander_speed x 6 s, give or take a chunk
    assert len(walks) <= 11                               # about one step in three


def test_a_wanderer_gives_up_a_goal_it_cannot_reach():
    from app.game.buildings import Building
    w = World(); w.now = 0.0
    b = Building(id='test:block', outline=[list(shift(LAT, LNG, x, y)) for x, y in ((2, -30), (40, -30), (40, 30), (2, 30))])
    w.buildings.items[b.id] = b
    z = Zed(id='w2', lat=LAT, lng=LNG, home=(LAT, LNG), state='investigate'); w.zeds[z.id] = z
    z.goal = shift(LAT, LNG, 20.0, 0.0)                    # inside a solid block with no way in
    for _ in range(60):
        if z.goal is None:
            break
        w._wander(z, 0.2)
    assert z.goal is None and z.state == 'idle'
