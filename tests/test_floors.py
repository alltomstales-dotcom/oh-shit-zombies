import copy
from app.game.sim import World,Actor,Zed
from app.game import floors,store
from tests.test_buildings import house


def setup():
    w=World();b=house();w.buildings.items[b.id]=b
    lat,lng=floors.landing(b);a=Actor(id=1,lat=lat,lng=lng);w.add_actor(a,100)
    return w,a,b


def test_stairs_change_level_without_gps_and_isolate_ground_zombies():
    w,a,b=setup();ground=Zed(id='ground',lat=a.lat,lng=a.lng,state='chase',target=a.id)
    w.zeds[ground.id]=ground
    assert w.act(a.id,'stairs',op='up')['ok'];assert a.floor_level==1
    layer=w.for_actor(a);assert layer is not w
    assert not w.view(a.id)['z'] or all(row[0]!='ground' for row in w.view(a.id)['z'])
    assert w.view(a.id)['you']['floor']==1
    assert all(':f1:' in r['id'] for r in layer.buildings.items[b.id].rooms)
    w.step(101);assert a.hp==100
    assert not layer.buildings.clear((a.lat,a.lng),[a.lat+.01,a.lng])
    assert w.act(a.id,'stairs',op='down')['ok'];assert a.floor_level==0
    assert w.for_actor(a) is w


def test_stairs_require_proximity_and_escape_from_melee():
    w,a,b=setup();a.lat+=.0001
    assert not w.act(a.id,'stairs',op='up')['ok']
    a.lat,a.lng=floors.landing(b)
    w.zeds['held']=Zed(id='held',lat=a.lat,lng=a.lng,state='engaged',target=a.id)
    assert not w.act(a.id,'stairs',op='up')['ok']
    assert a.floor_level==0


def test_upper_openings_do_not_modify_ground_and_actor_level_is_saved():
    w,a,b=setup();before=copy.deepcopy(b.snapshot())
    assert w.act(a.id,'stairs',op='up')['ok']
    upper=w.for_actor(a).buildings.items[b.id]
    upper.openings[0]['open']=True
    assert b.snapshot()==before
    assert {o['id'] for o in b.openings}.isdisjoint(o['id'] for o in upper.openings)
    saved=store.to_state(a)
    assert saved['floor_level']==1 and saved['floor_building']==b.id and saved['floor_epoch']==1
    assert floors.state(w.for_actor(a))['openings'][upper.openings[0]['id']]['open']


def test_upper_exit_opens_inner_door_and_descends_without_window_escape():
    w,a,b=setup();assert w.act(a.id,'stairs',op='up')['ok']
    upper=w.for_actor(a);ub=upper.buildings.items[b.id]
    a.lat,a.lng=ub.ll(ub.rooms[-1]['pos'])
    opened=[]
    for _ in range(5):
        result=floors.exit_plan(upper.buildings,(a.lat,a.lng))
        assert result['ok'],result
        for point in result['route']:
            assert upper.buildings.clear((a.lat,a.lng),point)
            a.lat,a.lng=point
        if result.get('stairs'):break
        _,o=upper.buildings.opening(result['opening']);opened.append(o['label']);o['open']=True
    assert result.get('stairs') and 'Room door' in opened
    assert w.act(a.id,'stairs',op='down')['ok']
    assert a.floor_level==0


def test_upper_movement_rejects_transit_jump_and_closed_window_escape():
    w,a,b=setup();assert w.act(a.id,'stairs',op='up')['ok']
    before=(a.lat,a.lng);raw=a.raw
    w.set_position(a.id,a.lat+.01,a.lng,1)
    assert a.raw==raw
    w.step(101)
    assert (a.lat,a.lng)==before


def test_upper_loot_and_household_containers_are_distinct_and_floor_filtered():
    from app.game import home,survival,loot
    w,a,b=setup();a.add('water',2)
    assert home.action(w,a,'home',{'name':'House'})['ok']
    ground=survival.furniture(w,a)
    w._building_loot();ground_stashes=set(w.stashes)
    assert w.act(a.id,'stairs',op='up')['ok'];up=w.for_actor(a)
    upper=survival.furniture(up,a)
    assert {o['id'] for o in ground}.isdisjoint(o['id'] for o in upper)
    assert not home.reachable(up,a)
    up._building_loot();assert ground_stashes.isdisjoint(up.stashes)
    assert all(s.get('floor_level')==1 for s in up.stashes.values())
    assert all(s.get('floor_level')==1 for s in loot.containers(up,a))
    assert w.act(a.id,'stairs',op='down')['ok']
    assert home.reachable(w,a)


import pytest
@pytest.mark.asyncio
async def test_upper_actor_and_openings_survive_cold_hub_without_loaded_map(maker):
    from app.game.hub import Hub
    from app.auth import create_anonymous_player
    from app.models import BuildingLevel
    async def send(_):pass
    h=Hub();h.clock=lambda:1000
    async with maker() as s:player=(await create_anonymous_player(s,'floor-test-device-123','FloorTest'))['player']
    conn,_,_=await h.join(player,send);b=house();h.world.buildings.items[b.id]=b
    a=h.world.actors[player.id];a.lat,a.lng=floors.landing(b);a.raw=(*floors.landing(b),1)
    assert (await h.act(conn,'stairs',{'op':'up'}))['ok']
    upper=h.world.for_actor(player.id);o=upper.buildings.items[b.id].openings[0];o['open']=True
    upper.zeds.clear();resident=Zed(id=b.id+':resident',lat=a.lat,lng=a.lng,hp=23,home=(a.lat,a.lng));upper.zeds[resident.id]=resident
    await h.save_all(force=True)
    async with maker() as s:
        level=await s.get(BuildingLevel,b.id+':f1');assert level.state['openings'][o['id']]['open']
    cold=Hub();cold.clock=lambda:1001
    conn2,_,_=await cold.join(player,send)
    saved=cold.world.actors[player.id];assert saved.floor_level==1
    coldlevel=cold.world.for_actor(saved)
    assert coldlevel is not cold.world and coldlevel.buildings.items[b.id].openings[0]['open']
    assert coldlevel.zeds[resident.id].hp==23
    assert (coldlevel.zeds[resident.id].lat,coldlevel.zeds[resident.id].lng)==(resident.lat,resident.lng)
    assert cold.world.view(player.id)['you']['floor']==1
    assert (await cold.act(conn2,'stairs',{'op':'down'}))['ok']
    assert cold.world.actors[player.id].floor_level==0


def test_third_floor_and_upper_body_isolation():
    from app.game import corpses
    from app.game.buildings import Building
    w,a,b=setup()
    b=Building(id='office:large',type='office',outline=[b.ll(p) for p in ((0,0),(40,0),(40,30),(0,30))]);w.buildings.items={b.id:b}
    a.lat,a.lng=floors.landing(b)
    assert floors.count(b)==3
    assert w.act(a.id,'stairs',op='up')['ok']
    assert w.act(a.id,'stairs',op='up')['ok'];assert a.floor_level==2
    assert not w.act(a.id,'stairs',op='up')['ok']
    up=w.for_actor(a);z=Zed(id='upper-corpse',lat=a.lat,lng=a.lng);up.zeds[z.id]=z;up._kill(z,a)
    body=next(iter(up.corpses.values()));assert body['floor_level']==2 and body['floor_building']==b.id
    assert corpses.reachable(up,a,body)
    assert w.act(a.id,'stairs',op='down')['ok']
    assert not corpses.reachable(w.for_actor(a),a,body)
    assert w.act(a.id,'stairs',op='down')['ok']
    assert not w.act(a.id,'stairs',op='down')['ok']


def test_missing_upper_blueprint_is_safe_until_map_loads():
    w,a,b=setup();a.floor_level=1;a.floor_building='missing'
    assert w.for_actor(a) is not w
    w.zeds['ground']=Zed(id='ground',lat=a.lat,lng=a.lng,state='engaged',target=a.id)
    w.step(101);assert a.hp==100
    assert not w.view(a.id)['z']


def test_stairs_wait_for_initial_map_and_clear_a_refreshed_ground_wall():
    w,a,b=setup();a.location_loading_until=w.now+10
    assert not w.act(a.id,'stairs',op='up')['ok']
    a.location_loading_until=0
    assert w.act(a.id,'stairs',op='up')['ok']
    # The real ground map can refresh while the player is on the saved upper floor.
    point=(a.lat,a.lng)
    from app.game.sim import shift
    w.buildings.obstacles=[{'id':'new-wall','a':shift(*point,-2,0),'b':shift(*point,2,0)}]
    assert w.act(a.id,'stairs',op='down')['ok']
    assert w.buildings.clear((a.lat,a.lng),(a.lat,a.lng))
    assert a.raw[:2]==(a.lat,a.lng)


def test_upper_window_can_be_smashed_without_ground_damage_or_walking_out():
    w,a,b=setup();assert w.act(a.id,'stairs',op='up')['ok']
    up=w.for_actor(a);ub=up.buildings.items[b.id];o=ub.openings[0]
    mid=tuple((p+q)/2 for p,q in zip(o['a'],o['b']))
    from app.game.sim import shift
    for dy in (-1,1):
        p=shift(*ub.ll(mid),0,dy)
        if ub.contains(p):a.lat,a.lng=p;break
    result=w.act(a.id,'opening',opening=o['id'],op='smash')
    assert result['ok'],result
    assert o['broken'] and o['kind']=='window' and not b.openings[0]['broken']
    assert not up.buildings.clear((a.lat,a.lng),shift(a.lat,a.lng,100,0))


def test_upper_inhabitants_keep_position_health_and_cleared_floors_stay_clear():
    w,a,b=setup();assert w.act(a.id,'stairs',op='up')['ok'];up=w.for_actor(a)
    up.zeds.clear();z=Zed(id='resident',lat=a.lat,lng=a.lng,hp=17,home=(a.lat,a.lng));up.zeds[z.id]=z
    key=up._level_key;w.level_states[key]=floors.state(up);w.levels.clear()
    restored=w.for_actor(a);assert restored.zeds[z.id].hp==17
    assert (restored.zeds[z.id].lat,restored.zeds[z.id].lng)==(z.lat,z.lng)
    restored._kill(restored.zeds[z.id],a)
    w.level_states[key]=floors.state(restored);w.levels.clear();w.dead_until.clear()
    assert not w.for_actor(a).zeds,'a saved cleared upstairs room cannot reseed on restart/expiry'


def test_a_sealed_home_never_gets_a_new_upper_inhabitant():
    from app.game import home
    w,a,b=setup();assert home.action(w,a,'home',{'name':'Sealed'})['ok']
    w.homes[a.id]=a.home
    assert w.act(a.id,'stairs',op='up')['ok']
    assert not w.for_actor(a).zeds
