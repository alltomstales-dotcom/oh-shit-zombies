import copy
from types import SimpleNamespace
import asyncio
import pytest
from app.auth import create_anonymous_player
from app.game import backgrounds,store
from app.game.hub import Hub
from app.game.sim import Actor,World,Zed
from app.game.progression import skill_level
from app.models import Survivor


def test_catalog_rank_gear_bounds_and_no_repeat_grants():
 for code,spec in backgrounds.OCCUPATIONS.items():
  a=store.starter(1,'T',100);before=copy.deepcopy(a.items)
  assert backgrounds.choose(a,code,'balanced',100)['ok']
  assert len(spec['skills'])<=2 and all(rank==1 for rank in spec['skills'].values())
  assert all(skill_level(a,s)==1 for s in spec['skills']) and a.xp==0
  after=store.to_state(a);assert backgrounds.choose(a,code,'balanced',101)['replay']
  assert store.to_state(a)==after
  assert not backgrounds.choose(a,code,'nimble',101)['ok']
  assert a.items or before


def test_invalid_used_dead_and_old_save_neutral_guards():
 a=Actor(id=1);assert not backgrounds.choose(a,'bogus','balanced')['ok']
 assert not backgrounds.choose(a,'medic','bogus')['ok'];assert a.background is None
 for key,value in [('lat',44.9),('placed_at',1),('xp',1),('walked_m',1),('kills',1),('dead',True)]:
  a=Actor(id=1);setattr(a,key,value);assert not backgrounds.choose(a,'medic','balanced')['ok']
 old=store.from_state(SimpleNamespace(player_id=1,born=1,state={'lat':44.9,'lng':-93.2}),'Old')
 assert old.background is None and backgrounds.factor(old,'pace')==1 and backgrounds.factor(old,'carry',0)==0


def test_trait_pace_carry_noise_and_fatigue_remain_authoritative():
 w=World();a=Actor(id=1);normal=w.movement_speed(a);capacity=w.carry_capacity(a)
 backgrounds.choose(a,'survivor','nimble');assert w.movement_speed(a)==pytest.approx(normal*1.08)
 assert w.carry_capacity(a)==capacity-1
 a.end=5;assert w.movement_speed(a)<normal
 a.end=100;a.quiet=True;assert w.movement_speed(a)==pytest.approx(w.T['quiet_speed']*1.08)
 b=Actor(id=2);backgrounds.choose(b,'survivor','sturdy');assert w.carry_capacity(b)==capacity+1.5
 b.speed=6;assert w.heard_m(b)==pytest.approx(w.T['noise_travel_m']*1.15)
 b.speed=0;assert w.heard_m(b)==w.T['noise_still_m']


def test_steady_panic_regen_tradeoff_and_json_roundtrip():
 w=World();w.now=100;a=Actor(id=1,end=50);b=Actor(id=2,end=50);backgrounds.choose(b,'medic','steady')
 w._step_actor(a,.5);w._step_actor(b,.5)
 assert b.end-50==pytest.approx((a.end-50)*.9)
 a.panic=b.panic=0
 w.zeds['A']=Zed(id='A',lat=a.lat,lng=a.lng,state='chase',target=1)
 w.zeds['B']=Zed(id='B',lat=b.lat,lng=b.lng,state='chase',target=2)
 w._step_actor(a,.05);w._step_actor(b,.05);assert b.panic==pytest.approx(a.panic*.8)
 restored=store.from_state(SimpleNamespace(player_id=2,born=1,state=store.to_state(b)),'T')
 assert restored.background==b.background and restored.count('disinfectant')==1


async def fresh_hub(maker):
 h=Hub();h.world.spawner=None;h.clock=lambda:100;h.director.policy=lambda *a:'quiet'
 async with maker() as s:p=(await create_anonymous_player(s,'background-device-0001','Role'))['player']
 async def send(msg):pass
 c,a,_=await h.join(p,send);return h,p,c,a


@pytest.mark.asyncio
async def test_durable_choice_concurrent_retry_restart_and_fresh_life(maker):
 h,p,c,a=await fresh_hub(maker);args={'occupation':'medic','trait':'nimble','life_id':a.life_id}
 res=await asyncio.gather(h.act(c,'background',args),h.act(c,'background',args))
 assert all(r['ok'] for r in res) and sum(bool(r.get('replay')) for r in res)==1
 a=h.world.actors[p.id];assert a.count('disinfectant')==1 and skill_level(a,'first_aid')==1
 async with maker() as s:
  loaded=store.from_state(await s.get(Survivor,c.survivor_id),'Role');assert loaded.background==a.background
 cold=Hub();cold.world.spawner=None;cold.clock=lambda:100;cold.director.policy=lambda *a:'quiet'
 async def send(msg):pass
 c2,rejoined,_=await cold.join(p,send)
 assert rejoined.background==a.background and rejoined.count('disinfectant')==1
 assert skill_level(rejoined,'first_aid')==1
 assert (await cold.act(c2,'background',args))['replay']
 assert cold.world.actors[p.id].count('disinfectant')==1
 a.lat,a.lng=44.9,-93.2;assert not (await h.act(c,'background',{**args,'occupation':'scout'}))['ok']
 h.world._die(a,{'cause':'bled out'});fresh=await h.new_survivor(p,c)
 assert fresh.background is None and not fresh.count('disinfectant')
 assert not (await h.act(c,'background',args))['ok'] # previous-life message cannot choose this life
 assert (await h.act(c,'background',{'occupation':'firefighter','trait':'sturdy','life_id':fresh.life_id}))['ok']
 assert h.world.actors[p.id].count('gloves')==1


@pytest.mark.asyncio
async def test_failed_background_save_does_not_publish_partial_gear_or_rank(maker,monkeypatch):
 h,p,c,a=await fresh_hub(maker);before=store.to_state(a);original=store.save
 async def fail(*a,**kw):raise RuntimeError('background save fixture')
 monkeypatch.setattr(store,'save',fail)
 args={'occupation':'medic','trait':'balanced','life_id':a.life_id}
 res=await h.act(c,'background',args);assert not res['ok'] and res['retry']
 assert store.to_state(h.world.actors[p.id])==before
 async with maker() as s:assert (await s.get(Survivor,c.survivor_id)).state==before
 monkeypatch.setattr(store,'save',original);assert (await h.act(c,'background',args))['ok']
 assert h.world.actors[p.id].count('disinfectant')==1
