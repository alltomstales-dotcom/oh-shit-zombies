"""The building search grid must give the answers a walk over every loaded building gives.

It is rebuilt only when buildings arrive, leave or are laid out again, and a sight line or a step
looks only at the cells it passes through. These tests hold both shortcuts to the plain rule.
"""
import math
import random

from app.game import survival
from app.game.buildings import Building, Buildings
from app.game.sim import Actor, World, shift
from tools.geometry_load import town


def _town(n=144, index=0):
    g = Buildings(); centre, records = town(index, n); g.add(records); return g, centre


def test_thin_line_search_agrees_with_every_building_for_steps_and_long_looks():
    g, c = _town(); rng = random.Random(5); blocked = 0
    for i in range(1500):
        reach = rng.choice((1.5, 8, 40, 120, 260))
        a = shift(*c, rng.uniform(-170, 170), rng.uniform(-170, 170))
        ang = rng.uniform(0, math.tau) if i % 5 else rng.choice((0, math.pi / 2, math.pi, 1e-9))     # level and upright lines too
        b = shift(*a, math.cos(ang) * reach, math.sin(ang) * reach)
        radius = rng.choice((0, .28, 1.0)); vision = bool(i % 2)
        plain = not any(x.blocks(a, b, radius, vision) for x in g.items.values())
        assert g.clear(a, b, radius, vision) == plain, (a, b, radius, vision)
        blocked += not plain
        first = next((x for x in g.items.values() if x.blocks(a, b)), None)
        assert g.first_blocking(a, b) is first
    assert 200 < blocked < 1400                    # the sample really has both answers in it


def test_near_matches_the_old_walk_and_keeps_loading_order():
    g, c = _town(); rng = random.Random(9)
    def plain(p, radius):
        out = []
        for b in g.items.values():
            x, y = b.xy(p); x0, y0, x1, y1 = b.bounds
            if math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1)) <= radius: out.append(b)
        return out
    for _ in range(60):
        p = shift(*c, rng.uniform(-200, 200), rng.uniform(-200, 200)); radius = rng.choice((5, 40, 180))
        assert [b.id for b in g.near(p, radius)] == [b.id for b in plain(p, radius)]


def test_opening_a_door_does_not_rebuild_the_grid_but_a_new_building_does():
    g, c = _town(36); g.containing(c); grid = g._spatial
    door = next(o for b in g.items.values() for o in b.openings if o['kind'] == 'door')
    door['open'] = True; g.revision += 1
    g.containing(c); assert g._spatial is grid
    assert g.opening(door['id'])[1] is door
    far = shift(*c, 900, 0); extra = Building(id='extra', outline=[list(shift(*far, x, y)) for x, y in ((0, 0), (9, 0), (9, 9), (0, 9))])
    g.items[extra.id] = extra                       # put in by hand, as older tests and tools do
    assert g.containing(shift(*far, 4, 4)) is extra and g._spatial is not grid
    assert g.opening(extra.openings[0]['id'])[0] is extra
    assert g.remove(['extra', 'never-there']) == ['extra'] and g.containing(shift(*far, 4, 4)) is None
    assert g.opening(extra.openings[0]['id']) == (None, None)


def test_a_door_moved_to_another_wall_is_still_found_by_id():
    g, c = _town(36); b = next(iter(g.items.values())); entrance = next(o for o in b.openings if o['label'] == 'Entrance')
    assert g.opening(entrance['id'])[1] is entrance
    b.relayout((b.entrance_edge + 1) % len(b.poly), b.window_edge)
    moved = next(o for o in b.openings if o['label'] == 'Entrance')
    assert moved is not entrance and g.opening(entrance['id'])[1] is moved


def test_boards_follow_buildings_that_arrive_later_and_come_down_when_broken():
    w = World(); c, records = town(0, 16); w.buildings.add(records[:8])
    late = Buildings(); late.add(records[8:]); b = next(iter(late.items.values())); window = next(o for o in b.openings if o['kind'] == 'window')
    a = Actor(id=1); a.lat, a.lng = c; w.add_actor(a, 0); survival.defaults(a)
    a.home = a.home or {}; a.home.setdefault('defenses', {})[window['id']] = {'hp': 80, 'building': b.id}; w.homes[a.id] = a.home
    survival.sync_geometry(w); rev = w.buildings.revision
    survival.sync_geometry(w); assert w.buildings.revision == rev          # nothing to do: no revision churn
    w.buildings.items.update(late.items)                                   # the region with the home loads
    survival.sync_geometry(w); assert window['barricaded'] and w.buildings.revision > rev
    a.home['defenses'][window['id']]['hp'] = 0
    survival.sync_geometry(w); assert not window['barricaded']


def test_walls_are_described_again_only_when_they_change_or_others_come_into_range():
    w = World(); c, records = town(0, 64); w.buildings.add(records)
    a = Actor(id=1); a.lat, a.lng = shift(*c, -5, -7); w.add_actor(a, 0)
    first = w.view(1); assert first['buildings'] and first['building_key'][0] == w.buildings.revision
    assert 'buildings' not in w.view(1, first['building_key'])
    door = next(o for b in w.buildings.items.values() for o in b.openings if o['kind'] == 'door')
    door['open'] = True; w.buildings.revision += 1
    again = w.view(1, first['building_key']); assert again['buildings'] and again['building_key'] != first['building_key']
    far = shift(*c, 2000, 0); extra = Building(id='extra', outline=[list(shift(*far, x, y)) for x, y in ((0, 0), (9, 0), (9, 9), (0, 9))])
    w.buildings.items[extra.id] = extra
    assert 'buildings' not in w.view(1, again['building_key'])           # too far to matter to this survivor
    a.lat, a.lng = shift(*far, -4, -4)
    assert [b['id'] for b in w.view(1, again['building_key'])['buildings']] == ['extra']


def test_a_shelf_is_judged_in_view_only_in_the_building_the_survivor_stands_in():
    w = World(); c, records = town(0, 16); w.buildings.add(records)
    b = next(x for x in w.buildings.items.values() if len(x.rooms) > 1)
    a = Actor(id=1); a.lat, a.lng = b.ll(b.rooms[1]['pos']); w.add_actor(a, 0); w._building_loot()
    rows = {s[0]: s for s in w.view(1)['stashes']}
    here = [s for s in rows.values() if s[5] == b.id]; elsewhere = [s for s in rows.values() if s[5] and s[5] != b.id]
    assert here and elsewhere and all(isinstance(s[8], bool) for s in here) and any(s[8] for s in here)
    assert all(s[8] is False for s in elsewhere)
