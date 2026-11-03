import copy
import asyncio
import pytest
from sqlalchemy import select
from app.auth import create_anonymous_player
from app.game import bases,store,survival,home
from app.game.hub import Hub
from app.game.sim import Actor,World
from app.models import PlayerHome,Survivor,BaseMembership,BaseSelection,BaseInvite

async def setup(maker):
 h=Hub();h.world.spawner=None;h.clock=lambda:100.;h.director.policy=lambda *a:'quiet'
 players=[]
 for n in range(3):
  async with maker() as s:p=(await create_anonymous_player(s,f'shared-base-device-{n:04}','Base'+str(n)))['player']
  async def send(msg):pass
  c,a,_=await h.join(p,send);a.lat,a.lng=44.9,-93.2;a.placed_at=1
  a.home={'name':p.name,'lat':a.lat,'lng':a.lng,'building':'base','capacity':40.,'revision':1,'items':[],'next_item':1,'receipts':[]}
  survival.defaults(a);a.add('cloth',6)
  async with maker() as s:await store.save(s,a,c.survivor_id,100)
  bases.publish(h.world,a);players.append((p,c,a))
 return h,players

async def invite(h,c,role='builder'):
 r=await h.act(c,'base',{'op':'invite','role':role});assert r['ok'];return r['code']

def transfer(h,c,op,item,qty=1,request='transfer-fixture-001'):
 a=h.world.actors[c.player_id]
 return h.act(c,'transfer',{'op':op,'item':item,'qty':qty,'revision':a.home['revision'],'request':request})

@pytest.mark.asyncio
async def test_join_shared_transfer_condition_replay_and_private_home_preserved(maker):
 h,ps=await setup(maker);p,c,_=ps[0];q,d,member=ps[1]
 personal=copy.deepcopy(member.home);code=await invite(h,c)
 assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 a=h.world.actors[p.id];b=h.world.actors[q.id]
 assert a.home is b.home and bases.owner(b)==p.id and b.base_role=='builder'
 knife=a.add('knife',1,2);assert (await transfer(h,c,'deposit',knife['id']))['ok']
 assert a is not h.world.actors[p.id] # private candidate publication
 a=h.world.actors[p.id];b=h.world.actors[q.id]
 row=next(i for i in b.home['items'] if i['code']=='knife')
 args={'op':'withdraw','item':row['id'],'qty':1,'revision':b.home['revision'],'request':'member-withdraw-001'}
 r=await asyncio.gather(h.act(d,'transfer',args),h.act(d,'transfer',args));assert all(x['ok'] for x in r)
 b=h.world.actors[q.id];assert b.count('knife')==1 and b.item(next(i['id'] for i in b.items if i['code']=='knife'))['cond']==2
 assert not b.home['items'] and b.home is h.world.actors[p.id].home
 async with maker() as s:
  assert (await s.get(PlayerHome,q.id)).state==personal
  assert not (await s.get(PlayerHome,p.id)).state['items']
 assert (await h.act(d,'base',{'op':'personal'}))['ok'];assert h.world.actors[q.id].home==personal
 assert (await h.act(d,'base',{'op':'select','owner':p.id}))['ok']
 assert (await h.act(d,'base',{'op':'leave'}))['ok']
 async with maker() as s:assert await s.get(BaseMembership,(p.id,q.id)) is None

@pytest.mark.asyncio
async def test_names_are_not_invites_role_owner_rules_expiry_rotate_and_revoke(maker):
 h,ps=await setup(maker);p,c,_=ps[0];q,d,_=ps[1];_,e,_=ps[2]
 assert not (await h.act(d,'base',{'op':'join','invite':p.name}))['ok']
 code=await invite(h,c,'storage');assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 b=h.world.actors[q.id]
 assert not (await h.act(d,'home',{'op':'rename','name':'Hijacked'}))['ok']
 assert not (await h.act(d,'base',{'op':'invite'}))['ok']
 assert not survival.start(h.world,b,{'op':'craft','recipe':'bandages'})['ok']
 assert not (await h.act(d,'base',{'op':'revoke','member':p.id}))['ok']
 assert not (await h.act(c,'home',{'name':'Moved'}))['ok']
 rotated=await invite(h,c);assert not (await h.act(e,'base',{'op':'join','invite':code}))['ok']
 h.clock=lambda:86501.;assert not (await h.act(e,'base',{'op':'join','invite':rotated}))['ok'];h.clock=lambda:100.
 b.channel={'kind':'work'};b.pending_work={'op':'craft'}
 assert (await h.act(c,'base',{'op':'revoke','member':q.id}))['ok']
 assert h.world.actors[q.id].home_owner==q.id and not b.channel and not b.pending_work
 assert not (await h.act(d,'base',{'op':'join','invite':rotated}))['ok']
 assert not (await h.act(d,'base',{'op':'select','owner':p.id}))['ok']

@pytest.mark.asyncio
async def test_owner_absent_restart_and_member_death_new_life_still_shared(maker):
 h,ps=await setup(maker);p,c,_=ps[0];q,d,_=ps[1]
 code=await invite(h,c);assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 cold=Hub();cold.world.spawner=None;cold.clock=lambda:100.;cold.director.policy=lambda *a:'quiet'
 async def send(msg):pass
 conn,b,_=await cold.join(q,send)
 assert bases.owner(b)==p.id and b.home['_shared'] and p.id not in cold.world.actors
 item=next(i for i in b.items if i['code']=='cloth')
 assert (await transfer(cold,conn,'deposit',item['id']))['ok']
 b=cold.world.actors[q.id];cold.world._die(b,{'cause':'bled out'})
 fresh=await cold.new_survivor(q,conn)
 assert fresh.home_owner==p.id and fresh.home['items'][0]['code']=='cloth' and fresh.base_role=='builder'
 assert fresh.lat==fresh.lng==0

@pytest.mark.asyncio
async def test_shared_transfer_save_failure_is_atomic_and_retry_conserved(maker,monkeypatch):
 h,ps=await setup(maker);p,c,_=ps[0];_,d,_=ps[1]
 code=await invite(h,c);assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 a=h.world.actors[p.id];item=next(i for i in a.items if i['code']=='cloth');before=store.to_state(a);stock=copy.deepcopy(a.home)
 original=store.save
 async def fail(*a,**kw):raise RuntimeError('storage failure fixture')
 monkeypatch.setattr(store,'save',fail)
 assert not (await transfer(h,c,'deposit',item['id']))['ok']
 assert store.to_state(h.world.actors[p.id])==before and h.world.actors[p.id].home==stock
 monkeypatch.setattr(store,'save',original);assert (await transfer(h,c,'deposit',item['id']))['ok']
 async with maker() as s:assert sum(i['qty'] for i in (await s.get(PlayerHome,p.id)).state['items'] if i['code']=='cloth')==1

@pytest.mark.asyncio
async def test_stale_shared_save_cannot_overwrite_other_stock_or_survivor(maker):
 h,ps=await setup(maker);p,c,_=ps[0]
 await invite(h,c);a=h.world.actors[p.id];stale=copy.deepcopy(a)
 item=next(i for i in a.items if i['code']=='cloth');assert (await transfer(h,c,'deposit',item['id']))['ok']
 stale.home['name']='Stale writer';stale.hp=12
 async with maker() as s:
  with pytest.raises(RuntimeError,match='shared base changed'):await store.save(s,stale,c.survivor_id,100)
  await s.rollback()
 async with maker() as s:
  assert (await s.get(Survivor,c.survivor_id)).state['hp']!=12
  assert (await s.get(PlayerHome,p.id)).state['name']==p.name
  assert (await s.get(PlayerHome,p.id)).state['items'][0]['qty']==1

@pytest.mark.asyncio
async def test_shared_work_save_failure_keeps_materials_until_success(maker,monkeypatch):
 h,ps=await setup(maker);p,c,_=ps[0];await invite(h,c)
 a=h.world.actors[p.id];before=a.count('cloth');a.pending_work={'kind':'work','op':'craft','args':{'op':'craft','recipe':'bandages'},'start':[a.lat,a.lng]}
 original=store.save
 async def fail(*a,**kw):raise RuntimeError('shared work failure fixture')
 monkeypatch.setattr(store,'save',fail)
 kept=await h._commit_work(c,a,100);assert kept is a and kept.count('cloth')==before and kept.pending_work
 monkeypatch.setattr(store,'save',original);done=await h._commit_work(c,a,100)
 assert not done.pending_work and done.count('cloth')==before-2
 async with maker() as s:assert (await s.get(Survivor,c.survivor_id)).state['items']==done.items

@pytest.mark.asyncio
async def test_two_members_compete_for_last_item_and_receipts_belong_to_actor(maker):
 h,ps=await setup(maker);p,c,_=ps[0];q,d,_=ps[1];r,e,_=ps[2]
 code=await invite(h,c)
 for conn in (d,e):assert (await h.act(conn,'base',{'op':'join','invite':code}))['ok']
 a=h.world.actors[p.id];knife=a.add('knife',1,3);assert (await transfer(h,c,'deposit',knife['id']))['ok']
 a=h.world.actors[p.id];row=a.home['items'][0]
 args={'op':'withdraw','item':row['id'],'qty':1,'revision':a.home['revision'],'request':'compete-last-item-001'}
 results=await asyncio.gather(h.act(d,'transfer',args),h.act(e,'transfer',args))
 assert sum(result['ok'] for result in results)==1
 assert sum(h.world.actors[player.id].count('knife') for player in (q,r))==1
 assert not h.world.actors[p.id].home['items']

@pytest.mark.asyncio
async def test_real_transaction_rollback_does_not_publish_invite_or_version(maker,monkeypatch):
 from sqlalchemy.ext.asyncio import AsyncSession
 h,ps=await setup(maker);p,c,_=ps[0];before=copy.deepcopy(h.world.actors[p.id].home)
 original=AsyncSession.commit
 async def fail(s):
  await s.flush()
  raise RuntimeError('commit failure after SQL flush')
 monkeypatch.setattr(AsyncSession,'commit',fail)
 assert not (await h.act(c,'base',{'op':'invite','role':'builder'}))['ok']
 assert h.world.actors[p.id].home==before
 monkeypatch.setattr(AsyncSession,'commit',original)
 async with maker() as s:
  assert not (await s.execute(select(BaseInvite))).scalars().all()
  assert (await s.get(PlayerHome,p.id)).state==before
 assert (await h.act(c,'base',{'op':'invite','role':'builder'}))['ok']

@pytest.mark.asyncio
async def test_revoked_stale_actor_cannot_save_into_former_shared_base(maker):
 h,ps=await setup(maker);p,c,_=ps[0];q,d,_=ps[1]
 code=await invite(h,c);assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 stale=copy.deepcopy(h.world.actors[q.id]);stock=copy.deepcopy(stale.home)
 assert (await h.act(c,'base',{'op':'revoke','member':q.id}))['ok']
 stale.home['items'].append({'id':1,'code':'cloth','qty':900,'cond':None});stale.hp=2
 async with maker() as s:
  with pytest.raises(PermissionError):await store.save(s,stale,d.survivor_id,100)
  await s.rollback()
 async with maker() as s:
  assert (await s.get(PlayerHome,p.id)).state['items']==stock['items']
  assert (await s.get(Survivor,d.survivor_id)).state['hp']!=2

@pytest.mark.asyncio
async def test_switch_flushes_recent_personal_investment_and_offline_base_damage(maker):
 h,ps=await setup(maker);p,c,_=ps[0];q,d,_=ps[1]
 code=await invite(h,c);b=h.world.actors[q.id]
 b.home['name']='Fresh personal name';b.home['revision']+=1
 assert (await h.act(d,'base',{'op':'join','invite':code}))['ok']
 async with maker() as s:assert (await s.get(PlayerHome,q.id)).state['name']=='Fresh personal name'
 a=h.world.actors[p.id];a.home['defenses']['door']={'hp':12,'building':'base'}
 async with maker() as s:await store.save(s,a,c.survivor_id,100)
 h.world.actors.clear();h.conns.clear();h.world.homes[p.id]['defenses']['door']['hp']=5;h.world.home_dirty.add(p.id)
 await h.save_all()
 async with maker() as s:assert (await s.get(PlayerHome,p.id)).state['defenses']['door']['hp']==5

def test_two_members_share_once_per_instant_utilities_and_food_even_different_layers():
 w=World();w.now=100
 h={'items':[{'code':'rawfood','qty':1,'cond':100}],'objects':[{'id':'gen','kind':'generator','on':True,'fuel':100,'hp':70,'lat':1,'lng':1}],'lat':1,'lng':1}
 a=Actor(id=1,lat=1,lng=1,home=h);b=Actor(id=2,lat=1,lng=1,home=h,home_owner=1,base_role='builder')
 upper=World();upper._level_root=w;upper.now=100
 survival.update(w,a,1);fuel=h['objects'][0]['fuel'];food=h['items'][0]['cond']
 survival.update(upper,b,1);assert h['objects'][0]['fuel']==fuel==99 and h['items'][0]['cond']==food
 assert a.hunger==b.hunger

def test_teammates_are_visible_only_in_same_active_base_floor_range_and_sight():
 w=World();a=Actor(id=1,name='Owner',lat=44.9,lng=-93.2);b=Actor(id=2,name='Friend',lat=a.lat,lng=a.lng,home_owner=1)
 stranger=Actor(id=3,lat=a.lat,lng=a.lng);w.actors={x.id:x for x in (a,b,stranger)}
 assert [r['id'] for r in w.view(a.id)['allies']]==[b.id]
 b.floor_level=1;assert not w.view(a.id)['allies'];b.floor_level=0
 b.lat+=.01;assert not w.view(a.id)['allies'];b.lat=a.lat
 w.visible=lambda *args:False;assert not w.view(a.id)['allies']
