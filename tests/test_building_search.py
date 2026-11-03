"""Two persistent search attempts reveal useful hidden room containers."""
from app.game.sim import Actor,shift
from app.game.store import to_state,from_state
from app.models import Survivor
from tests.test_building_world import setup


def test_building_search_has_two_chances_and_cannot_farm_xp():
    w,a,b=setup();a.lat,a.lng=b.ll(b.rooms[0]['pos'])
    for i in range(2):
        assert w.act(a.id,'search_building')['ok']
        w._finish_channel(a,a.channel);a.channel=None
        assert a.building_searches[b.id]['attempts']==i+1
    xp=a.xp
    assert not w.act(a.id,'search_building')['ok']
    assert a.xp==xp and w.view(a.id)['you']['building_search_left']==0


def test_interrupted_or_departed_search_does_not_use_chance():
    w,a,b=setup();a.lat,a.lng=b.ll(b.rooms[0]['pos'])
    assert w.act(a.id,'search_building')['ok']
    ch=a.channel
    a.lat,a.lng=b.ll((-10,-10))
    w._finish_channel(a,ch)
    assert b.id not in a.building_searches
    assert not w.act(a.id,'search_building')['ok']


def test_search_state_and_discovered_caches_restore_and_are_private():
    w,a,b=setup();a.lat,a.lng=b.ll(b.rooms[0]['pos'])
    # Try deterministic independent lives until one actual RNG discovery succeeds.
    for born in range(20):
        a.born=born;a.building_searches={}
        assert w.act(a.id,'search_building')['ok']
        w._finish_channel(a,a.channel);a.channel=None
        if a.building_searches[b.id]['caches']:break
    cache=a.building_searches[b.id]['caches'][0]
    row=Survivor(player_id=a.id,born=a.born,state=to_state(a))
    restored=from_state(row,a.name)
    w.stashes.clear();w.actors[a.id]=restored;w._building_loot()
    assert restored.building_searches==a.building_searches
    assert cache['id'] in w.stashes
    restored.lat,restored.lng=cache['lat'],cache['lng']
    assert w.act(a.id,'search',stash=cache['id'])['ok']
    w._finish_channel(restored,restored.channel)
    assert cache['id'] in restored.claimed
    other=Actor(id=2,lat=cache['lat'],lng=cache['lng']);w.add_actor(other,w.now)
    assert cache['id'] not in [s[0] for s in w.view(other.id)['stashes']]
    assert not w.act(other.id,'search',stash=cache['id'])['ok']
