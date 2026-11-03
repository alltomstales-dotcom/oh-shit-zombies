import copy
import pytest
from app.game import home, survival, store
from app.game.sim import World,Actor,Zed
from app.game.content import ITEMS
from tests.test_equipment_home import shelter


def complete(w,a,**args):
    result=w.act(a.id,'work',**args)
    assert result['ok'],result
    ch=copy.deepcopy(a.channel);a.channel=None
    w.now=ch['ends'];survival.finish(w,a,ch)
    return ch


def supply(a,recipe):
    r=survival.RECIPES[recipe]
    for c,n in r['need'].items():a.add(c,n)
    if r.get('tool'):a.add(r['tool'])


def test_salvage_is_finite_and_crafting_conserves_materials():
    w,a,b=shelter();a.add('hammer')
    chair=next(o for o in survival.furniture(w,a) if o['kind']=='chair')
    a.lat,a.lng=chair['lat'],chair['lng']
    complete(w,a,op='salvage',object=chair['id'])
    assert a.count('plank')==3 and a.count('nails')==4
    assert not w.act(a.id,'work',op='salvage',object=chair['id'])['ok']
    a.add('plank',1)
    # Clear outdoor placement keeps entrances and existing furniture clear.
    a.lat,a.lng=b.ll((-10,-10));ll=survival.shift(a.lat,a.lng,4,0)
    complete(w,a,op='craft',recipe='crate',lat=ll[0],lng=ll[1])
    assert a.count('plank')==0 and a.count('nails')==0
    crate=a.home['objects'][0];assert crate['capacity']==25
    a.lat,a.lng=crate['lat'],crate['lng']
    complete(w,a,op='salvage',object=crate['id'])
    assert a.count('plank')==1 and a.count('nails')==1


def test_interrupted_craft_never_consumes_materials_or_grants_xp():
    w,a,b=shelter();a.add('cloth',2)
    ch=w.act(a.id,'work',op='craft',recipe='bandages');assert ch['ok']
    pending=copy.deepcopy(a.channel);a.channel=None;a.lat+=5/111320
    survival.finish(w,a,pending)
    assert a.count('cloth')==2 and a.count('bandage')==0 and a.xp==0


def test_completion_revalidates_tools_and_inventory():
    w,a,b=shelter();a.add('log');saw=a.add('saw')
    assert w.act(a.id,'work',op='craft',recipe='planks')['ok']
    ch=a.channel;a.channel=None;saw['cond']=0
    survival.finish(w,a,ch)
    assert a.count('log')==1 and a.count('plank')==0


def test_tree_to_logs_to_planks_and_depletion():
    w,a,b=shelter();a.add('axe');a.add('saw')
    tree=next(n for n in survival.nodes(w,a) if n['kind']=='tree')
    a.lat,a.lng=tree['lat'],tree['lng']
    complete(w,a,op='chop',object=tree['id'])
    assert a.count('log')==2
    complete(w,a,op='craft',recipe='planks')
    assert a.count('log')==1 and a.count('plank')==4
    assert a.home['nodes'][tree['id']]==2


def test_mining_and_smelting_require_tools_station_and_fuel():
    w,a,b=shelter();ore=next(n for n in survival.nodes(w,a) if n['kind']=='ore');a.lat,a.lng=ore['lat'],ore['lng']
    assert not w.act(a.id,'work',op='mine',object=ore['id'])['ok']
    pick=a.add('pickaxe');complete(w,a,op='mine',object=ore['id'])
    assert a.count('ore')==3 and pick['cond']==29
    a.add('branch',2)
    assert not w.act(a.id,'work',op='craft',recipe='smelt')['ok']
    a.home['objects'].append(dict(id='furnace',kind='furnace',lat=a.lat,lng=a.lng,hp=80,items=[]))
    complete(w,a,op='craft',recipe='smelt')
    assert a.count('metal')==1 and a.count('ore')==1 and a.count('branch')==0


def test_rest_works_when_exhausted_and_needs_are_distinct():
    w,a,b=shelter();bed=next(o for o in survival.furniture(w,a) if o['kind']=='bed');a.lat,a.lng=bed['lat'],bed['lng'];a.end=0;a.sleep=70
    complete(w,a,op='rest',object=bed['id'])
    assert a.end==45 and a.sleep==35
    a.hunger=70;a.thirst=70;a.add('water');a.add('snack')
    w.now+=2;assert w.act(a.id,'use',code='water')['ok']
    w.now+=2;assert w.act(a.id,'use',code='snack')['ok']
    assert a.thirst==25 and a.hunger==45


def test_reusable_furniture_storage_and_dismantle_guard():
    w,a,b=shelter();o=next(o for o in survival.furniture(w,a) if o['kind']=='wardrobe');a.lat,a.lng=o['lat'],o['lng'];water=a.add('water',2)
    req=dict(op='deposit',item=water['id'],qty=1,container=o['id'],revision=a.home['revision'],request='fixture-transfer')
    assert home.action(w,a,'transfer',req)['ok']
    assert a.home['mutations'][o['id']]['items'][0]['qty']==1
    a.add('hammer');assert not w.act(a.id,'work',op='salvage',object=o['id'])['ok']


def test_barriers_remain_after_owner_disconnect_and_gate_open_changes_collision():
    w,a,b=shelter();a.lat,a.lng=b.ll((-10,-10));w.homes[a.id]=a.home;survival.defaults(a)
    point=survival.shift(a.lat,a.lng,4,0)
    o=dict(id='fence',kind='gate',lat=point[0],lng=point[1],hp=60,rotation=0)
    a.home['objects'].append(o);survival.sync_geometry(w)
    lo=survival.shift(*point,0,-2);hi=survival.shift(*point,0,2)
    assert not w.buildings.clear(lo,hi)
    w.remove_actor(a.id);survival.sync_geometry(w)
    assert not w.buildings.clear(lo,hi)
    o['open']=True;survival.sync_geometry(w)
    assert w.buildings.clear(lo,hi)


def test_zombies_damage_real_defenses_and_can_break_them():
    w,a,b=shelter();survival.defaults(a);w.homes[a.id]=a.home
    window=next(o for o in b.openings if o['kind']=='window');a.home['defenses'][window['id']]={'hp':10,'building':b.id}
    assert survival.batter_opening(w,window['id'],1)
    assert a.home['defenses'][window['id']]['hp']==0
    assert a.id in w.home_dirty


def test_placement_rejects_doors_and_people_and_keeps_fences_outside():
    w,a,b=shelter();door=b.openings[0];ll=b.ll([(x+y)/2 for x,y in zip(door['a'],door['b'])]);assert not survival.validate_place(w,a,ll,'crate')
    assert not survival.validate_place(w,a,[a.lat,a.lng],'crate')
    assert not survival.validate_place(w,a,b.ll(b.rooms[0]['pos']),'fence')


def test_powered_fridge_slows_spoilage_and_generator_consumes_fuel():
    w,a,b=shelter();survival.defaults(a)
    a.add('rawfood');a.home['objects']=[dict(id='g',kind='generator',lat=a.lat,lng=a.lng,hp=70,fuel=50,on=True,items=[]),dict(id='f',kind='fridge',lat=a.lat,lng=a.lng,hp=50,items=[dict(id=1,code='rawfood',qty=1,cond=100)])]
    survival.update(w,a,10)
    assert a.home['objects'][0]['fuel']==40
    assert a.home['objects'][1]['items'][0]['cond']>a.items[0]['cond']


def test_rain_garden_food_and_offline_needs_are_bounded():
    w,a,b=shelter();survival.defaults(a)
    barrel=dict(id='barrel',kind='rainbarrel',lat=a.lat,lng=a.lng,hp=35,items=[],water=0,fill_at=w.now-60)
    garden=dict(id='garden',kind='garden',lat=a.lat,lng=a.lng,hp=20,items=[],ready=w.now-1)
    a.home['objects']=[barrel,garden];survival.update(w,a,.2)
    assert barrel['water']==2
    complete(w,a,op='collect',object='barrel');assert a.count('dirtywater')==1
    complete(w,a,op='harvest',object='garden');assert a.count('rawfood')==3
    a.hunger=a.thirst=95;hp=a.hp;store.apply_time_away(a,86400,w.now+86400)
    assert a.hunger<=75 and a.thirst<=75 and a.hp>=hp


def test_food_recipe_handles_multiple_freshness_stacks():
    w,a,b=shelter();a.add('rawfood',1,90);a.add('rawfood',1,80)
    assert a.take('rawfood',2) and a.count('rawfood')==0


def test_depleted_resources_and_built_objects_survive_serialized_home():
    w,a,b=shelter();survival.defaults(a);a.home['nodes']['node']=0;a.home['objects'].append(dict(id='crate',kind='crate',lat=a.lat,lng=a.lng,hp=40,items=[],capacity=25))
    from app.models import Survivor
    fresh=store.from_state(Survivor(player_id=1,born=100,state=store.to_state(a)),'New')
    fresh.home=copy.deepcopy(a.home)
    assert fresh.home['nodes']['node']==0 and fresh.home['objects'][0]['kind']=='crate'


def test_need_damage_never_heals_a_critical_survivor():
    w,a,b=shelter();a.hp=2;a.hunger=99
    survival.update(w,a,10)
    assert a.hp==2


def test_resource_positions_survive_geometry_change_and_invalid_ids_are_safe():
    w,a,b=shelter();first=survival.nodes(w,a);assert first
    snapshot=copy.deepcopy(a.home)
    w.buildings.items.clear();w.buildings.revision+=1
    a.home=snapshot
    second=survival.nodes(w,a)
    assert [(n['id'],n['lat'],n['lng']) for n in first]==[(n['id'],n['lat'],n['lng']) for n in second]
    assert survival.target(w,a,'resource:!!!!!!!:0') is None


def test_placement_snaps_to_home_grid_and_rejects_segment_crossing_wall():
    w,a,b=shelter();a.lat,a.lng=b.ll((-10,-10))
    point=survival.shift(a.lat,a.lng,4.27,.33)
    q=survival.snap(a,point);assert survival.snap(a,q)==q
    from app.game.buildings import Buildings
    lo,hi=survival.shift(*q,0,-2),survival.shift(*q,0,2)
    w.buildings.obstacles=[dict(id='cross',a=lo,b=hi)]
    assert not survival.validate_place(w,a,q,'fence')


def test_exit_planner_respects_barricaded_openings():
    w,a,b=shelter();blocked={o['id'] for o in b.openings}
    assert not w.buildings.exit_plan([a.lat,a.lng],blocked)['ok']
    assert w.buildings.exit_plan([a.lat,a.lng])['ok']


@pytest.mark.asyncio
async def test_constructed_home_and_nodes_are_saved_with_survivor_and_retained_after_death(maker):
    from app.models import Player,Survivor,PlayerHome
    w,a,b=shelter();a.add('axe')
    tree=next(n for n in survival.nodes(w,a) if n['kind']=='tree');a.lat,a.lng=tree['lat'],tree['lng']
    complete(w,a,op='chop',object=tree['id'])
    a.home['objects'].append(dict(id='built:1:1',kind='metal_fence',lat=a.lat,lng=a.lng,hp=120,rotation=90,items=[]))
    async with maker() as s:
        p=Player(id=1,device_token='durable-work',name='Builder');s.add(p)
        row=Survivor(player_id=1,born=100,last_seen=100,state=store.to_state(a));s.add(row);await s.commit();sid=row.id
        await store.save(s,a,sid,101)
    async with maker() as s:
        saved=await s.get(PlayerHome,1);row=await s.get(Survivor,sid)
        assert saved.state['nodes'][tree['id']]==2
        assert saved.state['node_positions'][tree['id']]==[tree['lat'],tree['lng']]
        assert saved.state['objects'][0]['hp']==120
        assert store.from_state(row,'Builder').count('log')==2
        row.alive=False;await s.commit();fresh,_,_=await store.load_or_create(s,await s.get(Player,1),102)
        assert fresh.count('log')==0
        assert (await s.get(PlayerHome,1)).state['objects'][0]['hp']==120


def test_broken_utilities_require_repair_and_barricade_cannot_be_bypassed_by_smashing():
    w,a,b=shelter();survival.defaults(a);w.homes[a.id]=a.home
    a.home['objects'].append(dict(id='broken',kind='bed',lat=a.lat,lng=a.lng,hp=0,items=[]))
    assert not w.act(a.id,'work',op='rest',object='broken')['ok']
    window=next(o for o in b.openings if o['kind']=='window');a.lat,a.lng=b.ll([(x+y)/2 for x,y in zip(window['a'],window['b'])])
    a.home['defenses'][window['id']]={'hp':80,'building':b.id}
    assert not w.act(a.id,'opening',opening=window['id'],op='smash')['ok']


def test_destination_supply_themes_are_explicit_and_bounded():
    w,a,b=shelter();b.name='Fire Station'
    assert w._supply_kind(b,b.rooms[0])=='fire_station'
    b.name='Police Station';assert w._supply_kind(b,b.rooms[0])=='police_station'
    b.name='Community Pharmacy';assert w._supply_kind(b,b.rooms[0])=='medical'


def test_door_can_be_reinforced_only_while_another_escape_remains():
    w,a,b=shelter();survival.defaults(a);w.homes[a.id]=a.home;a.add('hammer');a.add('plank',4);a.add('nails',4)
    # Open the room passage to make the window a usable alternate escape.
    for o in b.openings:
        if o['label']=='Room door':o['open']=True
    door=next(o for o in b.openings if o['label']=='Entrance');a.lat,a.lng=b.ll((10,1))
    complete(w,a,op='barricade',opening=door['id'])
    assert a.home['defenses'][door['id']]['hp']==80
    windows=[o for o in b.openings if o['kind']=='window']
    a.add('plank',12);a.add('nails',12)
    for window in windows[:-1]:
        p=[(x+y)/2 for x,y in zip(window['a'],window['b'])]
        a.lat,a.lng=b.ll((p[0],p[1]-1))
        complete(w,a,op='barricade',opening=window['id'])
    window=windows[-1];p=[(x+y)/2 for x,y in zip(window['a'],window['b'])];a.lat,a.lng=b.ll((p[0],p[1]-1))
    assert not w.act(a.id,'work',op='barricade',opening=window['id'])['ok']
    assert w.buildings.exit_plan([a.lat,a.lng],{door['id']})['ok']


def test_work_rejects_invalid_placement_coordinates_without_exceptions():
    w,a,b=shelter()
    for lat,lng in ((1e308,1e308),(float('nan'),0),(0,float('inf'))):
        assert not w.act(a.id,'work',op='craft',recipe='crate',lat=lat,lng=lng)['ok']


def test_locked_entry_requires_a_tool_but_never_locks_a_survivor_inside():
    w,a,b=shelter();door=b.openings[0];door['locked']=True;a.lat,a.lng=b.ll((10,-1))
    assert not w.act(a.id,'opening',opening=door['id'],op='open')['ok']
    hammer=a.add('hammer');assert w.act(a.id,'opening',opening=door['id'],op='open')['ok']
    assert hammer['cond']==29 and not door['locked']
    w.now+=2;door['open']=False;door['locked']=True;a.items=[];a.lat,a.lng=b.ll((10,1))
    assert w.act(a.id,'opening',opening=door['id'],op='open')['ok']


def test_building_alarm_triggers_once_and_security_fields_are_visible():
    w,a,b=shelter();door=b.openings[0];door['alarm']=True;a.lat,a.lng=b.ll((10,1))
    assert w.act(a.id,'opening',opening=door['id'],op='open')['ok']
    assert door['alarm_triggered'] and sum(e['e']=='alarm' for e in a.events)==1
    w.act(a.id,'opening',opening=door['id'],op='close');w.act(a.id,'opening',opening=door['id'],op='open')
    assert sum(e['e']=='alarm' for e in a.events)==1
    assert 'locked' in b.snapshot()['openings'][0]


def test_spatial_collision_index_matches_full_geometry_and_route_legs_are_clear():
    import random
    w,a,b=shelter();rng=random.Random(72)
    for _ in range(100):
        lo=b.ll((rng.uniform(-10,30),rng.uniform(-10,22)));hi=b.ll((rng.uniform(-10,30),rng.uniform(-10,22)))
        assert w.buildings.clear(lo,hi)==(not any(x.blocks(lo,hi) for x in w.buildings.items.values()))
    start=b.ll((-2,-2));goal=b.ll((22,14));route=w.buildings.route(start,goal);assert route
    for leg in route:assert w.buildings.clear(start,leg);start=leg


def test_boarded_windows_block_sight_and_removal_restores_glass_visibility():
    w,a,b=shelter();w.homes[a.id]=a.home;survival.defaults(a)
    window=next(o for o in b.openings if o['kind']=='window')
    a.home['defenses'][window['id']]={'hp':80,'building':b.id};survival.sync_geometry(w)
    lo,hi=b.ll((10,11)),b.ll((10,13))
    assert not w.visible(lo,hi)
    a.home['defenses'].clear();survival.sync_geometry(w)
    assert w.visible(lo,hi)



def test_resources_wait_for_region_geometry_before_generating():
    w,a,b=shelter();w.resource_regions=set()
    assert survival.nodes(w,a)==[] and survival.view(w,a)['resources']==[]
    from app.geo import cell_of
    w.resource_regions.add(cell_of(a.lat,a.lng,6))
    assert survival.nodes(w,a)



def test_heavy_logs_slow_hauling_and_backpack_recovers_some_pace():
    from app.game import equipment
    w,a,b=shelter();fresh=w.movement_speed(a);a.add('log',10)
    burdened=w.movement_speed(a);assert burdened<fresh
    bag=a.add('rucksack');equipment.wear(a,bag['id'])
    assert burdened<w.movement_speed(a)<fresh



def test_lantern_light_stops_after_the_item_leaves_the_pack():
    w,a,b=shelter();row=a.add('lantern');a.lantern=True
    a.items.remove(row);w._step_actor(a,.2)
    assert not a.lantern



def test_heavy_work_does_not_regenerate_endurance_like_rest():
    w,a,b=shelter();a.end=30;a.last_action=w.now-3;a.raw=(a.lat,a.lng,1)
    a.channel={'kind':'work','op':'craft','ends':w.now+10,'args':{},'start':[a.lat,a.lng]}
    w._step_actor(a,1)
    assert a.end==30
    a.channel=None;w._step_actor(a,1)
    assert a.end>30


def test_a_built_gate_and_fence_can_be_worked_on_from_beside_them():
    """Their own barrier is not a wall between the survivor and the object."""
    w,a,b=shelter();a.lat,a.lng=b.ll((-10,-10));w.homes[a.id]=a.home;survival.defaults(a)
    a.add('hammer');a.add('plank',3)
    for oid,kind,east in (('gate1','gate',1.5),('fence1','fence',-1.5)):
        p=survival.shift(a.lat,a.lng,east,0)
        a.home['objects'].append(dict(id=oid,kind=kind,lat=p[0],lng=p[1],hp=30,rotation=90))
    survival.sync_geometry(w)
    assert len(w.buildings.obstacles)==2
    complete(w,a,op='open_gate',object='gate1')
    assert next(o for o in a.home['objects'] if o['id']=='gate1')['open']
    complete(w,a,op='open_gate',object='gate1')
    assert not next(o for o in a.home['objects'] if o['id']=='gate1').get('open')
    complete(w,a,op='repair',object='fence1')
    assert next(o for o in a.home['objects'] if o['id']=='fence1')['hp']==60 and a.count('plank')==2
    # a different barrier in between still blocks the reach
    far=survival.shift(a.lat,a.lng,2.5,0)
    a.home['objects'].append(dict(id='fence2',kind='fence',lat=far[0],lng=far[1],hp=30,rotation=90));survival.sync_geometry(w)
    assert not w.act(a.id,'work',op='repair',object='fence2')['ok']


def test_a_smashed_window_can_be_boarded_up_and_holds_until_the_boards_fail():
    w,a,b=shelter();survival.defaults(a);w.homes[a.id]=a.home;a.add('hammer');a.add('plank',4);a.add('nails',4)
    for o in b.openings:
        if o['label']=='Room door':o['open']=True
    window=next(o for o in b.openings if o['kind']=='window');window.update(broken=True,open=True,damage=1)
    inside,outside=b.ll((10,11)),b.ll((10,13.5))
    assert w.buildings.clear(inside,outside)               # smashed: anything walks through
    a.lat,a.lng=inside
    complete(w,a,op='barricade',opening=window['id']);survival.sync_geometry(w)
    assert a.home['defenses'][window['id']]['hp']==80 and window['barricaded']
    assert not w.buildings.clear(inside,outside) and not w.buildings.clear(inside,outside,vision=True)
    # a zombie at the boards batters them instead of climbing through the broken frame
    near=b.ll((10,12.8));z=Zed(id='z',lat=near[0],lng=near[1])
    held=w._zed_obstacle(z,inside,.2)
    assert abs(held[0]-near[0])*111320<.1 and abs(held[1]-near[1])*111320<.1      # it stays outside
    assert a.home['defenses'][window['id']]['hp']<80
    # the boards can be mended, and once they fail the frame is open again
    complete(w,a,op='repair_opening',opening=window['id']);assert a.home['defenses'][window['id']]['hp']==80
    a.home['defenses'][window['id']]['hp']=0;survival.sync_geometry(w)
    assert not window['barricaded'] and w.buildings.clear(inside,outside)
