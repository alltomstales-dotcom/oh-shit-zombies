"""Themed shelves use ordinary inventory mechanics and preserve old discoveries."""
from types import SimpleNamespace

import pytest

from app.game import loot
from app.game.buildings import Building
from app.game.content import ITEMS, STASH_LOOT
from app.game.sim import Actor, World, shift
from app.game.store import from_state, to_state

ORIGIN = (44.9778, -93.265)
OUTLINE = [list(shift(*ORIGIN, x, y)) for x, y in ((0,0),(20,0),(20,12),(0,12))]
NEW_CODES = ('beans','peaches','soup','tissue','soap','toothbrush','paperback')


def test_twelve_searches_per_room_have_distinct_supplies_and_no_automatic_take():
    observed = {}
    for theme in ('kitchen','bathroom','bedroom','garage'):
        codes = set()
        for n in range(12):
            w = World()
            b = Building(id=f'{theme}:{n}', outline=OUTLINE, type='house')
            b.rooms[0]['name'] = theme.title()
            w.buildings.items[b.id] = b
            a = Actor(id=1, lat=ORIGIN[0], lng=ORIGIN[1])
            w.add_actor(a, 100)
            a.lat, a.lng = b.ll(b.rooms[0]['pos'])
            w._building_loot()
            sid = 'room:' + b.rooms[0]['id']
            assert w.stashes[sid]['kind'] == theme
            assert w.act(a.id, 'search', stash=sid)['ok']
            w.now += 5
            w._finish_channel(a, a.channel)
            assert not a.items
            codes.update(i['code'] for i in a.loot_shelves[sid]['items'])
        assert codes <= {c for c, _, _ in STASH_LOOT[theme]}
        observed[theme] = codes
    assert observed['kitchen'] & {'beans','peaches','soup'}
    assert observed['bathroom'] & {'soap','toothbrush','tissue'}
    assert observed['bedroom'] & {'shirt','pants','schoolbag'}
    assert observed['garage'] & {'hammer','saw','nails'}
    assert not observed['kitchen'] & observed['garage']
    assert len({frozenset(codes) for codes in observed.values()}) == 4


def test_new_items_stack_weigh_and_survive_json_store_roundtrip():
    a = Actor(id=1)
    for code in NEW_CODES:
        first = a.add(code)
        assert a.add(code)['id'] == first['id']
    expected = sum(ITEMS[c]['w'] * 2 for c in NEW_CODES)
    assert a.weight() == pytest.approx(expected)
    restored = from_state(SimpleNamespace(state=to_state(a), player_id=1, born=a.born), 'Test')
    assert restored.items == a.items
    assert restored.weight() == pytest.approx(expected)
    for code in NEW_CODES:
        assert restored.take(code, 1)
    assert restored.weight() == pytest.approx(expected / 2)


@pytest.mark.parametrize('code', ['beans','peaches','soup'])
def test_named_food_uses_existing_hunger_mechanic(code):
    w = World(); a = Actor(id=1, hunger=70)
    w.add_actor(a, 100); a.add(code, 2)
    assert w.act(a.id, 'use', code=code)['ok']
    assert a.hunger == 45 and a.count(code) == 1


def test_room_labels_vary_deterministically_without_moving_geometry():
    names = set()
    for n in range(12):
        b = Building(id=f'house:{n}', outline=OUTLINE, type='house')
        again = Building(id=b.id, outline=OUTLINE, type='house')
        generic = Building(id=b.id, outline=OUTLINE)
        assert b.rooms == again.rooms and b.openings == generic.openings
        assert [r['pos'] for r in b.rooms] == [r['pos'] for r in generic.rooms]
        names.update(r['name'] for r in b.rooms)
    assert names == {'Kitchen','Bathroom','Bedroom'}


def test_destination_priority_and_old_claims_are_preserved():
    b = Building(id='home', outline=OUTLINE, type='house')
    b.rooms[0]['name'] = 'Kitchen'
    for name, expected in [('Fire Station','fire_station'),('Police Station','police_station'),('Pharmacy','medical')]:
        b.name = name
        assert World._supply_kind(b, b.rooms[0]) == expected
    a = Actor(id=1)
    stash = {'id':'old', 'lat':ORIGIN[0], 'lng':ORIGIN[1], 'kind':'chest','loot':[('bat',1)]}
    loot.reveal(a, stash)
    original = to_state(a)
    stash.update(kind='kitchen', loot=[('beans',2)])
    loot.reveal(a, stash)
    assert to_state(a) == original
    legacy = Actor(id=2); legacy.claimed.add('old')
    loot.reveal(legacy, stash)
    assert not legacy.loot_shelves and not legacy.items
