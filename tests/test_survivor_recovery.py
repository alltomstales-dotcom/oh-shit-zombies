import copy
import pytest
from sqlalchemy import select
from app.game import corpses,store,memory,floors
from app.game.sim import Actor,World,shift
from app.models import Survivor,WorldCorpse
from tests.test_corpses import setup_hub,request,LAT,LNG


def test_death_moves_exact_carried_stock_not_home_and_is_idempotent():
 w=World();a=store.starter(1,'Tom',100,LAT,LNG);a.life_id=42
 a.add('knife',1,2);a.add('cloth',3);a.home={'items':[{'code':'water','qty':7}]}
 stock=copy.deepcopy(a.items);home=copy.deepcopy(a.home);w.add_actor(a,100)
 w._die(a,{'cause':'bled out'});b=w.corpses[a.death['corpse']]
 assert b['items']==stock and b['until']==100+corpses.RECOVERY_S
 assert not a.items and not a.worn and a.hands is None and a.home==home
 assert a.death['items'] and memory.view(w,a)['recoveries'][0]['id']==b['id']
 w._die(a,{'cause':'turned'});assert len(w.corpses)==1 and b['items']==stock
 b['items'].clear();w._die(a,{});assert not b['items']


def test_only_owner_can_search_take_and_stock_preserves_condition():
 w=World();a=Actor(id=1,lat=LAT,lng=LNG,life_id=1);a.add('knife',1,2);w.add_actor(a,100)
 w._die(a,{'cause':'bled out'});b=next(iter(w.corpses.values()))
 owner=Actor(id=1,lat=LAT,lng=LNG);other=Actor(id=2,lat=LAT,lng=LNG)
 w.add_actor(owner,100);w.add_actor(other,100)
 assert not w.act(2,'search_body',corpse=b['id'])['ok']
 assert w.act(1,'search_body',corpse=b['id'])['ok']
 w._finish_channel(owner,owner.channel);owner.channel=None
 assert w.view(2)['corpses'][0]['items'] is None
 assert not corpses.take(w,other,b,request(b))['ok']
 assert corpses.take(w,owner,b,request(b))['ok'] and owner.items[0]['cond']==2
 assert corpses.take(w,owner,b,request({'id':b['id'],'items':[{'id':1}],'revision':2}))['ok'] # receipt replay
 assert owner.count('knife')==1


@pytest.mark.asyncio
async def test_death_and_pack_survive_fast_respawn_restart_and_do_not_refill(maker):
 h,people,_,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
 a.add('knife',1,2);stock=copy.deepcopy(a.items);h.world._die(a,{'cause':'bled out'})
 cid=a.death['corpse'];sid=c.survivor_id
 # New-life request can arrive before the next tick's corpse flush.
 fresh=await h.new_survivor(p,c);fresh.lat,fresh.lng=LAT,LNG
 await h._flush_corpses()
 assert cid in h.world.corpse_ready and cid not in h.world.corpse_dirty
 async with maker() as s:
  dead=await s.get(Survivor,sid);b=await s.get(WorldCorpse,cid)
  assert not dead.alive and not dead.state['items'] and b.state['items']==stock
  loaded=await corpses.load(s,100)
 h.world.corpses=loaded;h.world.corpse_ready=set(loaded)
 assert (await h.act(c,'search_body',{'corpse':cid}))['ok']
 a=h.world.actors[p.id];h.world._finish_channel(a,a.channel);a.channel=None
 await h._send_state(c,a,100,force=True);b=h.world.corpses[cid];req={**request(b),'item':next(i['id'] for i in b['items'] if i['code']=='knife')}
 assert (await h.act(c,'body_loot',req))['ok']
 remaining=copy.deepcopy(h.world.corpses[cid]['items'])
 async with maker() as s:
  old=store.from_state(await s.get(Survivor,sid),'Tom');old.dead=True;old.death=dead.death
  await store.save(s,old,sid,100)
  assert (await s.get(WorldCorpse,cid)).state['items']==remaining
  assert (await corpses.load(s,100))[cid]['items']==remaining
 assert h.world.actors[p.id].count('knife')==1


@pytest.mark.asyncio
async def test_death_flush_failure_rolls_back_life_and_hides_pack_until_retry(maker,monkeypatch):
 h,people,_,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
 a.add('knife',1,3)
 async with maker() as s:await store.save(s,a,c.survivor_id,100)
 h.world._die(a,{'cause':'bled out'});cid=a.death['corpse'];original=corpses.save_new
 async def fail(*args,**kw):raise RuntimeError('death persistence fixture')
 monkeypatch.setattr(corpses,'save_new',fail);await h._flush_corpses()
 assert cid not in h.world.corpse_ready and cid in h.world.corpse_dirty
 async with maker() as s:
  assert (await s.get(Survivor,c.survivor_id)).alive and await s.get(WorldCorpse,cid) is None
 monkeypatch.setattr(corpses,'save_new',original);await h._flush_corpses()
 async with maker() as s:
  assert not (await s.get(Survivor,c.survivor_id)).alive and await s.get(WorldCorpse,cid)
 assert cid in h.world.corpse_ready


@pytest.mark.asyncio
async def test_offline_turn_and_floor_stock_are_durable_and_expire_from_death(maker):
 h,people,_,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
 a.floor_level=1;a.floor_building='saved-building';a.add('knife',1,4)
 a.dead=True;a.death={'cause':'turned','t':80};a.turns_at=80
 async with maker() as s:
  await store.save(s,a,c.survivor_id,100);b=await s.get(WorldCorpse,a.death['corpse'])
  assert b.until==80+corpses.RECOVERY_S and b.state['floor_level']==1
  assert any(i['code']=='knife' and i['cond']==4 for i in b.state['items'])
  assert not await corpses.load(s,b.until)
