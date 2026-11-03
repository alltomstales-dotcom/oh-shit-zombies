import asyncio
import copy

import pytest

from app.auth import create_anonymous_player
from app.game import corpses, store
from app.game.buildings import Building
from app.game.content import ITEMS
from app.game.hub import Hub
from app.game.sim import Actor, World, Zed, shift
from app.models import Survivor, WorldCorpse

LAT,LNG=44.9778,-93.265


def kill(w,a,zid='victim',variant=4,temp=False):
    z=Zed(id=zid,lat=a.lat,lng=a.lng,variant=variant,temp=temp)
    w.zeds[z.id]=z;w._kill(z,a)
    return next(b for b in w.corpses.values() if b['id'] in w.corpse_dirty)


def request(body,rid='body-take-001',qty=1):
    return {'corpse':body['id'],'item':body['items'][0]['id'],'qty':qty,
            'revision':body['revision'],'request':rid}


def test_kill_creates_shared_static_body_and_daily_expiry():
    w=World();a=Actor(id=1,lat=LAT,lng=LNG);b=Actor(id=2,lat=LAT,lng=LNG)
    w.add_actor(a,100);w.add_actor(b,100);body=kill(w,a)
    assert w.view(1)['corpses']==w.view(2)['corpses']
    assert w.view(1)['corpses'][0]['items'] is None # unsearched supplies stay hidden
    assert not w.view(1)['z'] and not w.view(1)['stashes']
    w.step(145) # previous client bodies vanished at40seconds
    assert w.view(2)['corpses'][0]['id']==body['id']
    w.step(body['until'])
    assert not w.corpses and not w.view(1)['corpses']


def test_noisy_search_requires_range_line_of_sight_and_can_be_interrupted():
    w=World();a=Actor(id=1,lat=LAT,lng=LNG);w.add_actor(a,100);body=kill(w,a)
    z=Zed(id='listener',lat=LAT,lng=LNG,home=(LAT,LNG));w.zeds[z.id]=z
    assert w.act(a.id,'search_body',corpse=body['id'])['ok']
    assert z.state=='investigate'
    channel=a.channel;a.lat,a.lng=shift(LAT,LNG,5,0)
    w._finish_channel(a,channel);a.channel=None
    assert not body['searched'] and a.events[-1]['e']=='interrupted'
    a.lat,a.lng=LAT,LNG;z.state='engaged';z.target=a.id
    assert not w.act(a.id,'search_body',corpse=body['id'])['ok']
    z.state='idle';z.target=None
    outline=[list(shift(LAT,LNG,x,y)) for x,y in ((1,-4),(5,-4),(5,4),(1,4))]
    building=Building(id='wall',outline=outline);w.buildings.items[building.id]=building
    body['lat'],body['lng']=shift(LAT,LNG,2,0)
    assert not corpses.reachable(w,a,body)


def test_search_is_shared_no_auto_take_and_does_not_repeat_xp():
    w=World();a=Actor(id=1,lat=LAT,lng=LNG);w.add_actor(a,100);body=kill(w,a)
    body['items']=[{'id':1,'code':'shirt','qty':1,'cond':3}]
    assert w.act(a.id,'search_body',corpse=body['id'])['ok']
    w._finish_channel(a,a.channel);a.channel=None
    assert body['searched'] and not a.items and a.xp==25 # kill20 + search5
    corpses.reveal(a,body);assert a.xp==25
    assert corpses.take(w,a,body,request(body))['ok']
    assert a.items[0]['cond']==3 and not body['items']


def test_snapshot_bound_distance_and_visibility():
    w=World();a=Actor(id=1,lat=LAT,lng=LNG);w.add_actor(a,100)
    for n in range(60):
        z=Zed(id='victim'+str(n),lat=LAT,lng=LNG,variant=n%12)
        body=corpses.create(w,z);body['lat'],body['lng']=shift(LAT,LNG,n,0);w.corpses[body['id']]=body
    visible=w.view(1)['corpses'];assert len(visible)==corpses.VIEW_LIMIT
    assert all(b['items'] is None for b in visible)
    w.visible=lambda *args:False
    assert not w.view(1)['corpses']


def test_loot_is_sparse_look_tied_and_damaged():
    w=World();w.now=100;found={};weight=0;count=0
    for variant in range(16):
        codes=set()
        for n in range(100):
            z=Zed(id=f'look:{variant}:{n}',lat=LAT,lng=LNG,variant=variant)
            b=corpses.create(w,z);assert b==corpses.create(w,z)
            for i in b['items']:
                codes.add(i['code']);count+=i['qty'];weight+=ITEMS[i['code']]['w']*i['qty']
                if 'cond' in ITEMS[i['code']]:assert 2<=i['cond']<=5
        found[variant]=codes
    assert 'knife' in found[4] and 'helmet' in found[2] and 'bandage' in found[1] and 'fire_jacket' in found[14]
    assert all(codes<={'cloth'} for v,codes in found.items() if v not in (1,2,4,7,14))   # the postman's twin is not a nurse
    assert count<1600*.27 and weight/1600<.1
    # Bodies must not be more profitable than two ordinary room rolls.
    from app.game.content import STASH_LOOT
    for table in (STASH_LOOT[t] for t in ('kitchen','bathroom','bedroom','garage')):
        expected_qty=2*sum(wt*(lo+hi)/2 for _,wt,(lo,hi) in table)/sum(wt for _,wt,_ in table)
        assert count/1200<expected_qty/5


def test_director_body_ids_do_not_collide_across_restarts():
    w=World();w.now=100;z=Zed(id='t:1',lat=LAT,lng=LNG,temp=True)
    assert corpses.create(w,z)['id']!=corpses.create(w,z)['id']


def test_transfer_quantity_range_carry_and_engaged_checks():
    w=World();a=Actor(id=1,lat=LAT,lng=LNG);w.add_actor(a,100);body=kill(w,a)
    body['items']=[{'id':1,'code':'knife','qty':1,'cond':2}]
    assert not corpses.take(w,a,body,request(body))['ok']
    corpses.reveal(a,body)
    for qty in (0,-1,True,2,10001):assert not corpses.take(w,a,body,request(body,qty=qty))['ok']
    a.lat,a.lng=shift(LAT,LNG,5,0);assert not corpses.take(w,a,body,request(body))['ok']
    a.lat,a.lng=LAT,LNG;a.add('log',100)
    assert not corpses.take(w,a,body,request(body))['ok']
    a.items.clear();a.channel={'kind':'search'}
    assert not corpses.take(w,a,body,request(body))['ok']
    a.channel=None;w.zeds['grabber']=Zed(id='grabber',lat=LAT,lng=LNG,state='engaged',target=a.id)
    assert not corpses.take(w,a,body,request(body))['ok']
    w.zeds.clear();req=request(body);assert corpses.take(w,a,body,req)['ok']
    assert a.items[0]['cond']==2 and not body['items']
    assert corpses.take(w,a,None,req)['ok'] and a.count('knife')==1


async def setup_hub(maker):
    h=Hub();h.world.spawner=None;h.clock=lambda:100;h.director.policy=lambda *args:'quiet'
    people=[];messages={}
    for n in range(2):
        async with maker() as s:p=(await create_anonymous_player(s,f'body-device-000{n}',f'Body{n}'))['player']
        messages[p.id]=[]
        async def send(msg,pid=p.id):messages[pid].append(msg)
        conn,a,_=await h.join(p,send);a.lat,a.lng=LAT,LNG;people.append((p,conn))
    a=h.world.actors[people[0][0].id];body=kill(h.world,a)
    body['items']=[{'id':1,'code':'cloth','qty':2,'cond':None}]
    assert not h.world.view(a.id)['corpses'] # durable bodies are not published early
    await h._flush_corpses()
    return h,people,body,messages


@pytest.mark.asyncio
async def test_two_players_share_search_and_conserve_simultaneous_transfers_and_restart(maker):
    h,people,body,msgs=await setup_hub(maker);p,c=people[0];q,d=people[1]
    assert (await h.act(c,'search_body',{'corpse':body['id']}))['ok']
    a=h.world.actors[p.id];h.world._finish_channel(a,a.channel);a.channel=None
    await h._send_state(c,a,100,force=True);body=h.world.corpses[body['id']]
    assert h.world.view(p.id)['corpses']==h.world.view(q.id)['corpses']
    req=request(body,qty=1)
    results=await asyncio.gather(h.act(c,'body_loot',req),h.act(d,'body_loot',{**req,'request':'other-player-001'}))
    assert sum(r['ok'] for r in results)==1
    assert (await h.act(c,'body_loot',req))['ok'] # receipt replay, not another take
    h.world.actors[p.id].hunger=65;h.world.actors[p.id].dirty=True
    assert (await h.act(c,'body_loot',req))['ok']
    assert h.world.actors[p.id].dirty # replay must not discard unrelated unsaved needs
    assert h.world.actors[p.id].count('cloth')+h.world.actors[q.id].count('cloth')==1
    rest=h.world.corpses[body['id']];assert rest['items'][0]['qty']==1
    assert (await h.act(d,'body_loot',request(rest,rid='other-player-002')))['ok']
    assert not h.world.corpses[body['id']]['items']
    async with maker() as s:
        loaded=await corpses.load(s,100)
        saved=store.from_state(await s.get(Survivor,c.survivor_id),'T')
    assert loaded==h.world.corpses and saved.count('cloth')==1
    # Rejoin restores the receipt and shared stock; old personal loot does not own the body.
    h.world.remove_actor(p.id);h.conns.pop(p.id)
    async def send(msg):pass
    reconnect,a,_=await h.join(p,send)
    assert (await h.act(reconnect,'body_loot',req))['ok'] and h.world.actors[p.id].count('cloth')==1
    assert not a.loot_shelves and body['id'] not in a.claimed


@pytest.mark.asyncio
async def test_failed_creation_stays_hidden_and_retries(maker,monkeypatch):
    h,people,body,msgs=await setup_hub(maker)
    next_body=kill(h.world,h.world.actors[people[0][0].id],'second')
    original=corpses.save_new
    async def fail(*args):raise RuntimeError('fixture save failure')
    monkeypatch.setattr(corpses,'save_new',fail);await h._flush_corpses()
    assert next_body['id'] in h.world.corpse_dirty
    assert next_body['id'] not in {b['id'] for b in h.world.view(people[0][0].id)['corpses']}
    monkeypatch.setattr(corpses,'save_new',original);await h._flush_corpses()
    assert next_body['id'] in h.world.corpse_ready and not h.world.corpse_dirty


@pytest.mark.asyncio
async def test_failed_search_and_transfer_rollback_both_documents(maker,monkeypatch):
    h,people,body,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
    await h.act(c,'search_body',{'corpse':body['id']});h.world._finish_channel(a,a.channel);a.channel=None
    before=store.to_state(a);original=store.save
    async def fail(*args,**kw):raise RuntimeError('fixture actor save failure')
    monkeypatch.setattr(store,'save',fail);await h._send_state(c,a,100,force=True)
    assert not h.world.corpses[body['id']]['searched'] and store.to_state(a)==before
    async with maker() as s:assert not (await s.get(WorldCorpse,body['id'])).state['searched']
    monkeypatch.setattr(store,'save',original);await h._send_state(c,a,100,force=True)
    a=h.world.actors[p.id];body=copy.deepcopy(h.world.corpses[body['id']]);before=store.to_state(a)
    monkeypatch.setattr(store,'save',fail)
    assert not (await h.act(c,'body_loot',request(body)))['ok']
    assert h.world.corpses[body['id']]==body and store.to_state(h.world.actors[p.id])==before
    async with maker() as s:assert (await s.get(WorldCorpse,body['id'])).state==body


@pytest.mark.asyncio
async def test_database_revision_check_rejects_stale_writer_and_expired_rows(maker):
    h,people,body,msgs=await setup_hub(maker)
    candidate=copy.deepcopy(body);candidate['searched']=True;candidate['revision']+=1
    async with maker() as s:
        assert await corpses.update_stock(s,candidate,1);await s.commit()
    async with maker() as s:
        assert not await corpses.update_stock(s,candidate,1);await s.rollback()
        assert not await corpses.load(s,body['until'])


@pytest.mark.asyncio
async def test_static_body_snapshot_only_sent_when_changed(maker):
    h,people,body,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
    await h._send_state(c,a,100,force=True)
    assert msgs[p.id][-1]['corpses']
    await h._send_state(c,a,100,force=True)
    assert 'corpses' not in msgs[p.id][-1]
    a.lat,a.lng=shift(LAT,LNG,60,0)
    await h._send_state(c,a,100,force=True)
    assert msgs[p.id][-1]['corpses']==[]


@pytest.mark.asyncio
async def test_new_life_resends_bodies_after_client_clears_them(maker):
    h,people,body,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
    await h._send_state(c,a,100,force=True);assert c.corpse_key
    a.dead=True
    fresh=await h.new_survivor(p,c)
    assert c.corpse_key is None
    fresh.lat,fresh.lng=LAT,LNG
    await h._send_state(c,fresh,100,force=True)
    assert msgs[p.id][-1]['corpses'][0]['id']==body['id']
