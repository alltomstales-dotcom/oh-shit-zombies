import random
from app.game.sim import Actor,World,Zed,shift
from app.game.buildings import Building


def setup():
    w=World(rng=random.Random(1))
    origin=(44.9778,-93.265)
    b=Building(id='test:house',outline=[list(shift(*origin,x,y)) for x,y in ((0,0),(20,0),(20,12),(0,12))])
    w.buildings.items[b.id]=b
    a=Actor(id=1,lat=origin[0],lng=origin[1]);w.add_actor(a,100)
    return w,a,b


def test_world_actor_cannot_walk_through_wall_or_train_against_it():
    w,a,b=setup();a.lat,a.lng=b.ll((1,-.5))
    w.set_position(1,*b.ll((1,3)),1)
    w.step(100.5)
    assert not b.contains((a.lat,a.lng))
    assert a.training_m==0 and a.end==100


def test_interior_search_checks_wall_and_short_reach_at_start_and_finish():
    w,a,b=setup();a.lat,a.lng=b.ll((10,-1))
    pos=b.ll((10,1))
    w.stashes['box']={'id':'box','lat':pos[0],'lng':pos[1],'kind':'chest','building':b.id,'loot':[('bandage',1)]}
    assert not w.act(1,'search',stash='box')['ok']
    door=b.openings[0]
    assert w.act(1,'opening',opening=door['id'],op='open')['ok']
    assert w.act(1,'search',stash='box')['ok']
    ch=a.channel
    a.lat,a.lng=b.ll((10,-8))
    w._finish_channel(a,ch)
    assert 'box' not in a.claimed and a.xp==0


def test_invalid_smash_cannot_open_door_and_occupied_passage_cannot_close():
    w,a,b=setup();door=b.openings[0];center=tuple((p+q)/2 for p,q in zip(door['a'],door['b']))
    a.lat,a.lng=b.ll(center)
    assert not w.act(1,'opening',opening=door['id'],op='smash')['ok']
    assert not door['open']
    assert w.act(1,'opening',opening=door['id'],op='open')['ok']
    assert not w.act(1,'opening',opening=door['id'],op='close')['ok']
    assert door['open']


def test_opening_reach_matches_exit_planner_at_passage_edge():
    w,a,b=setup();door=b.openings[0]
    edge=door['a'];a.lat,a.lng=b.ll((edge[0],edge[1]-2.5))
    assert w.act(1,'opening',opening=door['id'],op='open')['ok']
    a.lat,a.lng=b.ll((edge[0],edge[1]-2.8))
    assert not w.act(1,'opening',opening=door['id'],op='close')['ok']


def test_combat_and_visibility_cannot_reach_through_wall():
    w,a,b=setup();a.lat,a.lng=b.ll((1,1))
    lat,lng=b.ll((1,-1));z=Zed(id='z',lat=lat,lng=lng,home=(lat,lng),state='engaged',target=1)
    w.zeds[z.id]=z
    assert w._reachable(a,4)==[]
    w._attack(z,a,1)
    assert a.hp==100 and z.state=='chase'
    assert w.view(1)['z']==[]


def test_room_loot_is_stable_and_claims_block_repeat_rewards():
    w,a,b=setup();a.lat,a.lng=b.ll(b.rooms[0]['pos']);w._building_loot()
    sid='room:'+b.rooms[0]['id'];stash=w.stashes[sid]
    assert stash['building']==b.id and stash['room']==b.rooms[0]['name']
    assert w.act(1,'search',stash=sid)['ok']
    w._finish_channel(a,a.channel)
    xp=a.xp;loot=list(stash['loot']);w._building_loot()
    assert w.stashes[sid]['loot']==loot
    assert not w.act(1,'search',stash=sid)['ok'] and a.xp==xp


def test_zombie_batters_closed_entrance_and_cannot_cross_until_broken():
    w,a,b=setup();lat,lng=b.ll((10,-.8));z=Zed(id='z',lat=lat,lng=lng,home=(lat,lng))
    door=b.openings[0]
    goal=b.ll((12,3))
    for _ in range(100):
        w._walk(z,*goal,.2,10)
        if not door['broken']:assert not b.contains((z.lat,z.lng))
    assert door['broken'] and door['open']


def test_new_geometry_clears_a_wall_overlap_without_training_xp():
    w,a,b=setup();a.lat,a.lng=b.ll((1,0));a.raw=(a.lat,a.lng,1)
    w.buildings.revision+=1
    w.step(100.1)
    assert w.buildings.clear((a.lat,a.lng),(a.lat,a.lng))
    assert a.xp==0 and a.training_m==0


def test_other_room_loot_is_hidden_until_room_door_opens():
    w,a,b=setup();a.lat,a.lng=b.ll(b.rooms[1]['pos']);w._building_loot()
    sid='room:'+b.rooms[0]['id']
    assert not next(s for s in w.view(1)['stashes'] if s[0]==sid)[8]
    door=next(o for o in b.openings if o['label']=='Room door');door['open']=True
    assert next(s for s in w.view(1)['stashes'] if s[0]==sid)[8]


def test_small_shed_gets_usable_single_room():
    w,a,b=setup();origin=(a.lat,a.lng)
    shed=Building(id='shed',outline=[list(shift(*origin,x,y)) for x,y in ((0,0),(3,0),(3,5),(0,5))])
    assert len(shed.rooms)==1 and shed.room_at(shed.ll(shed.rooms[0]['pos']))=='Interior'
    assert any(o['label']=='Entrance' for o in shed.openings)


def test_doors_and_windows_close_successfully_when_passage_is_clear():
    w,a,b=setup();a.lat,a.lng=b.ll((10,-2));door=b.openings[0]
    assert w.act(1,'opening',opening=door['id'],op='open')['ok']
    assert w.act(1,'opening',opening=door['id'],op='close')['ok']
    assert not door['open'] and door['id'] in w.buildings.dirty
    window=next(o for o in b.openings if o['kind']=='window');a.lat,a.lng=b.ll((10,10))
    assert w.act(1,'opening',opening=window['id'],op='open')['ok']
    assert w.act(1,'opening',opening=window['id'],op='close')['ok']
    assert not window['open'] and window['id'] in w.buildings.dirty


def test_initial_fix_with_preloaded_geometry_clears_wall_overlap():
    w,a,b=setup();w._geometry_seen=w.buildings.revision
    fresh=Actor(id=2);w.add_actor(fresh,100)
    w.set_position(2,*b.ll((1,0)),1)
    assert w.buildings.clear((fresh.lat,fresh.lng),(fresh.lat,fresh.lng))
    assert fresh.xp==0


def test_saved_survivor_joining_loaded_map_clears_wall_overlap():
    w,a,b=setup();w._geometry_seen=w.buildings.revision
    lat,lng=b.ll((1,0));saved=Actor(id=2,lat=lat,lng=lng)
    w.add_actor(saved,100)
    assert w.buildings.clear((saved.lat,saved.lng),(saved.lat,saved.lng))
    assert saved.xp==0


def test_virtual_steps_are_precise_while_gps_deadband_is_preserved():
    w,a,b=setup();a.lat,a.lng=b.ll((10,-5));start=(a.lat,a.lng)
    goal=shift(*start,.3,0)
    w.set_position(1,*goal,1,mode='gps');w.step(100.2)
    assert (a.lat,a.lng)==start
    w.set_position(1,*goal,1,mode='desk');w.step(100.4)
    assert abs(a.lat-goal[0])<1e-8 and abs(a.lng-goal[1])<1e-8
    assert .29<a.training_m<.31


def _sealed_block():
    """Nine attached squares. The middle one touches no open ground, so no door of its own can lead out."""
    import math
    lat,lng=44.9778,-93.265;mx=111320*math.cos(math.radians(lat))
    ll=lambda x,y:[lat+y/111320,lng+x/mx]
    return [{'id':'q:%d%d'%(i,j),'type':'house','outline':[ll(i*10,j*10),ll(i*10+10,j*10),ll(i*10+10,j*10+10),ll(i*10,j*10+10)]}
            for i in range(3) for j in range(3)]


def test_someone_sealed_inside_climbs_out_instead_of_being_stuck():
    w=World();w.buildings.add(_sealed_block());b=w.buildings.items['q:11']
    start=b.ll(b.rooms[0]['pos'])
    assert not w.buildings.exit_plan(start)['ok']
    a=Actor(id=1,lat=start[0],lng=start[1]);w.add_actor(a,0);a.raw=(start[0],start[1],5)
    assert w.climb_out(a)
    assert w.buildings.containing((a.lat,a.lng)) is None and w.buildings.clear((a.lat,a.lng),(a.lat,a.lng))
    out=(a.lat,a.lng)
    # the phone still reports the old spot for a moment: the survivor must not be pulled back in
    w.set_position(1,start[0],start[1],5)
    for i in range(30):w.step(i*.2)
    assert w.buildings.containing((a.lat,a.lng)) is None
    # with an ordinary way out nobody is lifted over the roof
    edge=w.buildings.items['q:01'];c=Actor(id=2);c.lat,c.lng=edge.ll(edge.rooms[0]['pos']);w.add_actor(c,0)
    assert w.buildings.exit_plan((c.lat,c.lng))['ok'] and not w.climb_out(c)
    assert w.buildings.containing((c.lat,c.lng)) is edge
