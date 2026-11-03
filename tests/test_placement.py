import copy
import pytest
from app.auth import create_anonymous_player
from app.game import placement, store
from app.game.director import Director
from app.game.hub import Hub
from app.game.sim import Actor, World, Zed, shift
from app.geo import cell_of
from app.models import Survivor, PlayerHome
from tests.test_building_world import setup

NOW = 1_000_000


def fix(**overrides):
    return dict(lat=44.9778, lng=-93.265, accuracy=12, timestamp=NOW*1000,
                source='gps', reason='launch', **overrides)


@pytest.mark.parametrize('changes', [dict(accuracy=150), dict(timestamp=(NOW-20)*1000),
    dict(timestamp=(NOW+10)*1000), dict(lat=float('nan')), dict(lng=181), dict(accuracy=-1)])
def test_bad_gps_does_not_place_or_change_actor(changes):
    w=World();a=Actor(id=1,lat=45,lng=-93);before=copy.deepcopy(a)
    assert not placement.apply(w,a,{**fix(),**changes},NOW)['ok']
    assert a==before


def test_launch_retains_life_and_gear_but_moves_to_current_fix():
    w=World();a=store.starter(1,'Tom',NOW-1000,45,-93)
    a.hp=71;a.xp=99;a.home={'name':'Home','lat':45,'lng':-93,'items':[]}
    before=store.to_state(a);h=copy.deepcopy(a.home)
    result=placement.apply(w,a,fix(),NOW)
    assert result['ok'] and (a.lat,a.lng)==(44.9778,-93.265)
    assert a.items==before['items'] and a.worn==before['worn'] and a.home==h
    assert a.hp==71 and a.xp==99 and a.born==NOW-1000 and a.placed_at==0


def test_fresh_life_starts_arrival_calm_when_placed_not_when_waiting():
    w=World();w.now=NOW;a=store.starter(1,'New',NOW-1000)
    assert placement.apply(w,a,fix(),NOW)['ok']
    assert a.placed_at==NOW and w.arriving(a)
    assert a.transit_until==NOW+20


def test_hunted_life_cannot_escape_with_launch_but_fresh_life_can_place():
    w=World();a=Actor(id=1,lat=45,lng=-93)
    w.zeds['z']=Zed(id='z',lat=45,lng=-93,target=1,state='chase')
    assert placement.apply(w,a,fix(),NOW)['hunted']
    assert (a.lat,a.lng)==(45,-93)
    w.zeds['z'].state='idle'
    assert placement.apply(w,a,fix(),NOW)['ok']


def test_travel_is_measured_from_gps_anchor_not_virtual_position():
    w=World();a=Actor(id=1);assert placement.apply(w,a,fix(),NOW)['ok']
    a.lat,a.lng=shift(*a.gps_anchor,2000,0)
    assert not placement.apply(w,a,{**fix(),'reason':'travel'},NOW)['ok']
    lat,lng=shift(*a.gps_anchor,1000,0)
    assert placement.apply(w,a,{**fix(),'lat':lat,'lng':lng,'reason':'travel'},NOW)['ok']


@pytest.mark.asyncio
async def test_atomic_placement_retries_stale_ticket_and_new_life(maker):
    async with maker() as s:player=(await create_anonymous_player(s,'placement-device-123456','Tom'))['player']
    h=Hub();h.world.spawner=None;h.clock=lambda:NOW
    async def send(m):pass
    c,a,_=await h.join(player,send)
    args={**fix(),'ticket':c.placement_ticket,'request':'placement-001'}
    r=await h.act(c,'place',args);assert r['ok']
    assert await h.act(c,'place',args)==r
    assert not (await h.act(c,'place',{**args,'request':'placement-002'}))['ok']
    assert not (await h.act(c,'place',{**args,'ticket':'stale'}))['ok']
    async with maker() as s:
        row=await s.get(Survivor,c.survivor_id)
        assert row.state['gps_anchor']==[44.9778,-93.265] and row.state['placement_epoch']==1
    h.world._die(h.world.actors[a.id],{'cause':'test'})
    fresh=await h.new_survivor(player,c)
    assert (fresh.lat,fresh.lng)==(0,0)
    assert not (await h.act(c,'place',args))['ok']
    assert (await h.act(c,'place',{**args,'ticket':c.placement_ticket,'request':'placement-003'}))['ok']


@pytest.mark.asyncio
async def test_database_failure_never_publishes_placement(maker,monkeypatch):
    async with maker() as s:player=(await create_anonymous_player(s,'placement-rollback-123456','Tom'))['player']
    h=Hub();h.clock=lambda:NOW
    async def send(m):pass
    c,a,_=await h.join(player,send)
    async def fail(*args,**kwargs):raise RuntimeError('storage failure')
    monkeypatch.setattr(store,'save',fail)
    result=await h.act(c,'place',{**fix(),'ticket':c.placement_ticket,'request':'placement-001'})
    assert not result['ok'] and (h.world.actors[a.id].lat,h.world.actors[a.id].lng)==(0,0)
    assert not c.launch_placed


def sealed():
    w,a,b=setup();w.homes[1]={'building':b.id,'defenses':{}}
    return w,a,b


def test_director_cannot_spawn_in_sealed_home_or_inside_observer_sight():
    w,a,b=sealed();center=b.ll(b.rooms[0]['pos']);a.lat,a.lng=shift(*center,0,-70)
    z=Director(w)._spawn(a,0,70,'shambler',False)
    assert z is not None and not b.contains((z.lat,z.lng))
    from app.game.sim import dist_m
    assert dist_m(a.lat,a.lng,z.lat,z.lng)>=w.sight_m(a)


def test_boarded_broken_home_is_protected_but_open_window_is_not():
    w,a,b=sealed();p=b.ll(b.rooms[0]['pos']);o=next(o for o in b.openings if o['kind']=='window')
    o['open']=o['broken']=True
    assert not w.protected_home(p)
    w.homes[1]['defenses'][o['id']]={'hp':80}
    assert w.protected_home(p)
    point=w.spawn_point(*p);assert point and not b.contains(point)


def test_late_geometry_corrects_only_unmapped_spawns_not_existing_occupants():
    w,a,b=sealed();p=b.ll(b.rooms[0]['pos'])
    for zid,unmapped in [('new',True),('existing',False)]:
        w.zeds[zid]=Zed(id=zid,lat=p[0],lng=p[1],spawn_unmapped=unmapped)
    w.protect_unmapped_spawns(cell_of(*p,6))
    assert not b.contains((w.zeds['new'].lat,w.zeds['new'].lng))
    assert b.contains((w.zeds['existing'].lat,w.zeds['existing'].lng))


@pytest.mark.asyncio
async def test_saved_home_still_protects_spawns_after_restart(maker):
    w,a,b=sealed()
    async with maker() as s:
        player=(await create_anonymous_player(s,'protected-home-device-123456','Tom'))['player']
        s.add(PlayerHome(player_id=player.id,state={'building':b.id,'defenses':{}}));await s.commit()
    restored=World();restored.buildings.items[b.id]=b
    async with maker() as s:restored.homes[player.id]=(await s.get(PlayerHome,player.id)).state
    p=b.ll(b.rooms[0]['pos']);assert restored.protected_home(p)
    assert not b.contains(restored.spawn_point(*p))


def test_new_cell_spawns_cannot_appear_inside_sealed_home():
    w,a,b=sealed();p=b.ll(b.rooms[0]['pos'])
    class FixedSpawner:
        def bucket(self,now):return 1
        def cells_near(self,*args):return ['test']
        def zeds(self,*args):return [dict(id='seed',lat=p[0],lng=p[1],kind='shambler',hp=20,speed=1,variant=0)]
        def stashes(self,*args):return []
    w.spawner=FixedSpawner();w._load_cells()
    z=w.zeds['seed'];assert not b.contains((z.lat,z.lng))


def test_map_loading_protection_finishes_when_ready_and_is_bounded():
    w=World();w.now=NOW;w.resource_regions=set();a=store.starter(1,'New',NOW-100)
    placement.apply(w,a,fix(),NOW);w.add_actor(a,NOW)
    w.resource_regions.add(cell_of(a.lat,a.lng,6));w.step(NOW+1)
    assert a.location_loading_until==0 and a.transit_until<=w.now and a.placed_at==NOW+1
    a2=store.starter(2,'New2',NOW);placement.apply(w,a2,fix(),NOW)
    w2=World();w2.resource_regions=set();w2.add_actor(a2,NOW);w2.step(NOW+21)
    assert a2.location_loading_until==0 and a2.transit_until<=w2.now


def test_manual_start_is_explicit_and_cannot_bypass_pursuit():
    w=World();a=Actor(id=1,lat=45,lng=-93)
    w.zeds['z']=Zed(id='z',lat=45,lng=-93,target=1,state='engaged')
    args={**fix(),'source':'manual'}
    assert placement.apply(w,a,args,NOW)['hunted']
    w.zeds.clear();assert placement.apply(w,a,args,NOW)['ok']
    assert a.gps_anchor is None


def test_four_minutes_of_packs_director_and_a_woken_herd_put_nothing_inside_shut_homes(monkeypatch):
    """The whole machine at once, in a town where every house is a shut home (tools/sealed_home_soak.py)."""
    from tools import sealed_home_soak as soak
    r=soak.run(seed=1,seconds=240,owner='away')
    assert r['made']['street pack']>10 and r['made']['director']>0 and r['made']['herd']>=60
    assert r['inside_while_shut']=={}
    # and the watch is not blind: without the rule the same run finds them
    monkeypatch.setattr(World,'protected_home',lambda self,p:False)
    assert soak.run(seed=1,seconds=30,owner='away')['inside_while_shut']
