import copy
import asyncio
import pytest
from app.auth import create_anonymous_player
from app.game import vehicles,store
from app.game.hub import Hub
from app.game.sim import Actor,World
from app.models import WorldVehicle,Survivor

def setup_world():
 w=World();w.now=100.;a=Actor(id=1,life_id=1,lat=44.9,lng=-93.2,placed_at=1)
 cars=vehicles.seeds(w,a);assert len(cars)==2
 v=cars[0];a.lat,a.lng=v['lat'],v['lng'];w.actors[a.id]=a;w.vehicles={x['id']:x for x in cars}
 return w,a,v

def test_repeatable_outdoor_spawns_and_bounded_car_van_stock():
 w,a,v=setup_world();first=vehicles.seeds(w,a);assert first==vehicles.seeds(w,a)
 assert {v['kind'] for v in first}=={'car','van'}
 assert max(v['capacity'] for v in first)==100 and all(v['fuel']<=v['tank'] for v in first)
 assert all(w.buildings.containing([v['lat'],v['lng']]) is None for v in first)
 a.floor_level=1;assert not vehicles.seeds(w,a)

def test_seat_claim_permission_controls_cargo_and_condition():
 w,a,v=setup_world();a.add('knife',1,2)
 assert vehicles.action(w,a,v,{'op':'enter_driver'},100)['ok']
 stranger=Actor(id=2,life_id=2,lat=a.lat,lng=a.lng)
 assert not vehicles.action(w,stranger,v,{'op':'enter_driver'},100)['ok']
 assert not vehicles.action(w,stranger,v,{'op':'withdraw','item':1,'qty':1,'revision':v['revision'],'request':'stranger-cargo-001'},100)['ok']
 assert not vehicles.control(w,stranger,v,{'east':1,'throttle':1},100)['ok']
 assert not vehicles.control(w,a,v,{'east':float('nan')},100)['ok']
 knife=next(x for x in a.items if x['code']=='knife')
 args={'op':'deposit','item':knife['id'],'qty':1,'revision':v['revision'],'request':'driver-cargo-001'}
 assert vehicles.action(w,a,v,args,100)['ok'];assert vehicles.action(w,a,v,args,100)['ok']
 assert sum(x['qty'] for x in v['items'] if x['code']=='knife')==1 and next(x for x in v['items'] if x['code']=='knife')['cond']==2

def test_server_driving_stops_stale_input_ignores_avatar_pos_and_consumes_fuel():
 w,a,v=setup_world();assert vehicles.action(w,a,v,{'op':'enter_driver'},100)['ok']
 assert vehicles.action(w,a,v,{'op':'engine'},100)['ok'];v['heading']=0
 fuel=v['fuel'];before=[v['lat'],v['lng']]
 for i in range(20):
  now=100+(i+1)*.2;vehicles.control(w,a,v,{'east':1,'throttle':1},now);w.step(now)
 assert v['fuel']<fuel and v['speed']>0 and [a.lat,a.lng]==[v['lat'],v['lng']]
 assert a.walked_m==0 and a.xp==0 # riding does not train walking
 moved=[v['lat'],v['lng']];w.set_position(a.id,a.lat+.01,a.lng+.01,1)
 assert a.raw is None and [v['lat'],v['lng']]==moved
 for i in range(12):w.step(104+(i+1)*.2)
 assert v['speed']==pytest.approx(0)
 assert vehicles.action(w,a,v,{'op':'exit'},107)['ok'] and a.vehicle_id is None
 assert before!=moved

def test_vehicle_collision_stops_before_buildings_and_hurts_condition():
 w,a,v=setup_world();vehicles.action(w,a,v,{'op':'enter_driver'},100);vehicles.action(w,a,v,{'op':'engine'},100)
 v['speed']=8.;v['heading']=0.;before=[v['lat'],v['lng']];hull=v['hull']
 w.buildings.clear=lambda *args,**kw:False
 vehicles.control(w,a,v,{'east':1,'throttle':1},100);vehicles.step(w,.2,100.2)
 assert [v['lat'],v['lng']]==before and v['speed']==0 and v['hull']<hull
 a.dead=True;vehicles.step(w,.2,100.4);assert not v['engine'] and not any(v['seats']) and a.vehicle_id is None

def test_shared_passenger_seat_switch_storage_permission_fuel_and_full_cargo():
 w,a,v=setup_world();assert vehicles.action(w,a,v,{'op':'enter_driver'},100)['ok']
 assert vehicles.action(w,a,v,{'op':'enter_driver'},100)['replay']
 b=Actor(id=2,life_id=2,lat=a.lat,lng=a.lng,home_owner=a.id,base_role='builder');w.actors[b.id]=b
 assert vehicles.action(w,b,v,{'op':'enter_passenger'},100)['ok']
 assert not vehicles.action(w,b,v,{'op':'enter_driver'},100)['ok']
 assert not vehicles.action(w,a,v,{'op':'enter_passenger'},100)['ok'] # no empty passenger seat
 assert vehicles.action(w,a,v,{'op':'exit'},100)['ok']
 assert vehicles.action(w,b,v,{'op':'enter_driver'},100)['ok'] and not v['seats'][1]
 assert vehicles.action(w,b,v,{'op':'exit'},100)['ok']
 b.base_role='storage';b.lat,b.lng=v['lat'],v['lng'];b.add('fuel',1)
 assert not vehicles.action(w,b,v,{'op':'enter_driver'},100)['ok']
 before=v['fuel'];assert vehicles.action(w,b,v,{'op':'fuel'},100)['ok'];assert v['fuel']==before+10 and not b.count('fuel')
 a.lat,a.lng=v['lat'],v['lng'];a.add('log',100)
 row=next(x for x in a.items if x['code']=='log');args={'op':'deposit','item':row['id'],'qty':100,'revision':v['revision'],'request':'full-cargo-fixture-001'}
 assert not vehicles.action(w,a,v,args,100)['ok'] and a.count('log')==100

async def setup_hub(maker):
 h=Hub();h.world.spawner=None;h.clock=lambda:100.;h.director.policy=lambda *a:'quiet'
 async with maker() as s:p=(await create_anonymous_player(s,'vehicle-test-device-001','Driver'))['player']
 async def send(msg):pass
 c,a,_=await h.join(p,send);a.lat,a.lng=44.9,-93.2;a.placed_at=1
 await h._seed_vehicles(a);v=next(iter(h.world.vehicles.values()));a.lat,a.lng=v['lat'],v['lng']
 async with maker() as s:await store.save(s,a,c.survivor_id,100)
 return h,p,c,a,v

@pytest.mark.asyncio
async def test_atomic_seat_retry_cargo_failure_and_cold_release_no_refill(maker,monkeypatch):
 h,p,c,a,v=await setup_hub(maker);vid=v['id']
 assert (await h.act(c,'vehicle',{'op':'enter_driver','vehicle':vid}))['ok']
 a=h.world.actors[p.id];v=h.world.vehicles[vid]
 item=a.add('knife',1,2);before=copy.deepcopy(v);original=store.save
 async def fail(*args,**kw):raise RuntimeError('vehicle stock save fixture')
 monkeypatch.setattr(store,'save',fail)
 args={'op':'deposit','vehicle':vid,'item':item['id'],'qty':1,'revision':v['revision'],'request':'durable-vehicle-001'}
 assert not (await h.act(c,'vehicle',args))['ok']
 assert h.world.vehicles[vid]==before and h.world.actors[p.id].count('knife')==1
 monkeypatch.setattr(store,'save',original)
 results=await asyncio.gather(h.act(c,'vehicle',args),h.act(c,'vehicle',args));assert all(r['ok'] for r in results)
 async with maker() as s:
  restored=await vehicles.load(s)
  car=restored[vid];assert not any(car['seats']) and not car['engine']
  assert sum(x['qty'] for x in car['items'] if x['code']=='knife')==1
  assert next(x for x in car['items'] if x['code']=='knife')['cond']==2
  state=(await s.get(Survivor,c.survivor_id)).state
  assert not any(x['code']=='knife' for x in state['items'])
  assert sum(x['qty'] for x in car['items'] if x['code']=='fuel')==1

@pytest.mark.asyncio
async def test_vehicle_version_conflict_rolls_back_actor_stock(maker):
 h,p,c,a,v=await setup_hub(maker);stale=copy.deepcopy(v)
 assert (await h.act(c,'vehicle',{'op':'enter_driver','vehicle':v['id']}))['ok']
 async with maker() as s:
  with pytest.raises(RuntimeError,match='vehicle changed'):await vehicles.save(s,stale)
  await s.rollback()
 async with maker() as s:assert (await s.get(WorldVehicle,v['id'])).state['seats'][0]['player']==p.id

@pytest.mark.asyncio
async def test_gps_launch_parks_vehicle_without_teleporting_it(maker):
 h,p,c,a,v=await setup_hub(maker);vid=v['id'];before=[v['lat'],v['lng']]
 assert (await h.act(c,'vehicle',{'op':'enter_driver','vehicle':vid}))['ok']
 args={'ticket':c.placement_ticket,'source':'manual','reason':'launch','lat':44.91,'lng':-93.2,'accuracy':1,'timestamp':100000,'request':'gps-car-launch-001'}
 assert (await h.act(c,'place',args))['ok']
 assert h.world.actors[p.id].vehicle_id is None and h.world.actors[p.id].lat==44.91
 assert [h.world.vehicles[vid]['lat'],h.world.vehicles[vid]['lng']]==before
 async with maker() as s:assert not any((await s.get(WorldVehicle,vid)).state['seats'])


def test_zombies_damage_shell_and_ramming_has_cost_without_melee_training():
 from app.game.sim import Zed,shift
 w,a,v=setup_world();vehicles.action(w,a,v,{'op':'enter_driver'},100)
 hp=a.hp;hull=v['hull']
 assert vehicles.intercept(w,a,10) and v['hull']==hull-10 and a.hp==hp-.5
 v['hull']=10;assert not vehicles.intercept(w,a,10)
 v['hull']=80;vehicles.action(w,a,v,{'op':'engine'},100);v['heading']=0;v['speed']=8
 z=Zed(id='ram-zombie',lat=v['lat'],lng=v['lng'],hp=1);w.zeds[z.id]=z
 vehicles.control(w,a,v,{'east':1,'throttle':1},100);vehicles.step(w,.2,100.2)
 assert not z.alive and v['hull']<80 and a.kills==1 and a.xp==0
 assert w.corpses # bodies remain searchable

@pytest.mark.asyncio
async def test_periodic_conflict_refreshes_cargo_and_allows_next_action(maker):
 h,p,c,a,v=await setup_hub(maker);vid=v['id']
 async with maker() as s:
  row=await s.get(WorldVehicle,vid);new=vehicles.restore(row);new['items'][1]['qty']=7
  new['revision']+=1;await vehicles.save(s,new);await s.commit()
 h.world.vehicle_dirty.add(vid);h.world.vehicle_controls[vid]={'at':100,'throttle':1}
 await h._save_vehicles()
 assert h.world.vehicles[vid]['items'][1]['qty']==7
 assert vid not in h.world.vehicle_dirty and vid not in h.world.vehicle_controls
 assert (await h.act(c,'vehicle',{'op':'enter_driver','vehicle':vid}))['ok']


def test_remembered_vehicle_mark_does_not_track_out_of_sight():
 from app.game import memory
 w,a,v=setup_world();w.now=100;memory.observe(w,a)
 seen=memory.view(w,a)['vehicles'];assert any(x['id']==v['id'] for x in seen)
 old=next(x for x in seen if x['id']==v['id'])
 v['lat']+=.01;w.now=200;memory.observe(w,a)
 remembered=next(x for x in memory.view(w,a)['vehicles'] if x['id']==v['id'])
 assert remembered['lat']==old['lat'] and remembered['age_s']==100

@pytest.mark.asyncio
async def test_two_players_compete_for_seat_and_last_cargo_with_base_revoke(maker):
 from tests.test_bases import setup,invite
 h,ps=await setup(maker);p,c,a=ps[0];q,d,b=ps[1]
 code=await invite(h,c);assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 a=h.world.actors[p.id];await h._seed_vehicles(a);vid=next(iter(h.world.vehicles));v=h.world.vehicles[vid]
 for x in h.world.actors.values():x.lat,x.lng=v['lat'],v['lng']
 results=await asyncio.gather(h.act(c,'vehicle',{'op':'enter_driver','vehicle':vid}),h.act(d,'vehicle',{'op':'enter_driver','vehicle':vid}))
 assert sum(r['ok'] for r in results)==1
 assert (await h.act(d,'vehicle',{'op':'enter_passenger','vehicle':vid}))['ok']
 v=h.world.vehicles[vid];args={'op':'withdraw','vehicle':vid,'item':1,'qty':1,'revision':v['revision']}
 results=await asyncio.gather(h.act(c,'vehicle',{**args,'request':'last-fuel-owner-001'}),h.act(d,'vehicle',{**args,'request':'last-fuel-member-001'}))
 assert sum(r['ok'] for r in results)==1
 assert sum(h.world.actors[x.id].count('fuel') for x in (p,q))==1
 assert not any(x['code']=='fuel' for x in h.world.vehicles[vid]['items'])
 assert (await h.act(c,'base',{'op':'revoke','member':q.id}))['ok']
 vehicles.step(h.world,.2,100.2);assert h.world.actors[q.id].vehicle_id is None
 assert not (await h.act(d,'vehicle',{'op':'enter_driver','vehicle':vid}))['ok']
 await h._save_vehicles()
 async with maker() as s:assert not (await s.get(WorldVehicle,vid)).state['seats'][1]


def test_driver_disconnect_brakes_and_invalid_life_releases_seat():
 w,a,v=setup_world();vehicles.action(w,a,v,{'op':'enter_driver'},100);vehicles.action(w,a,v,{'op':'engine'},100)
 v['speed']=8;a.connected=False;w.vehicle_dirty.clear()
 vehicles.step(w,.2,100.2);assert not v['engine'] and v['speed']==0 and v['id'] in w.vehicle_dirty
 a.life_id+=1;vehicles.step(w,.2,100.4);assert not any(v['seats']) and a.vehicle_id is None
