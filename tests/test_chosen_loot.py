import asyncio
import copy

import pytest

from app.auth import create_anonymous_player
from app.game import loot, store
from app.game.hub import Hub
from app.game.sim import Actor, World, shift
from app.models import Survivor

LAT, LNG = 44.9778, -93.265


def setup():
    w = World();a = Actor(id=1,lat=LAT,lng=LNG);w.add_actor(a,100)
    s = {'id':'shelf-test','lat':LAT,'lng':LNG,'kind':'bag','loot':[['water',5],['bat',1]],'condition':{'bat':6}}
    w.stashes[s['id']] = s
    return w,a,s


def args(a, qty=2, rid='transfer-001'):
    s=a.loot_shelves['shelf-test'];row=s['items'][0]
    return {'stash':s['id'],'item':row['id'],'qty':qty,'revision':s['revision'],'request':rid}


def test_search_reveals_without_auto_taking_or_equipping():
    w,a,s=setup();assert w.act(a.id,'search',stash=s['id'])['ok']
    w._finish_channel(a,a.channel);a.channel=None
    assert not a.items and a.hands is None
    assert s['id'] in a.claimed and a.xp==25
    assert a.loot_shelves[s['id']]['items'][1]['cond']==6
    assert not w.act(a.id,'search',stash=s['id'])['ok']
    assert loot.take(w,a,args(a))['ok']
    assert a.count('water')==2 and a.loot_shelves[s['id']]['items'][0]['qty']==3
    assert a.xp==25


def test_partial_contents_and_receipts_round_trip_without_legacy_refill():
    w,a,s=setup();loot.reveal(a,s);request=args(a);loot.take(w,a,request)
    restored=store.from_state(Survivor(player_id=a.id,born=100,state=store.to_state(a)),'T')
    assert restored.loot_shelves==a.loot_shelves
    assert loot.take(w,restored,request)['ok'] and restored.count('water')==2
    restored.claimed.add('legacy');legacy={**s,'id':'legacy'};loot.reveal(restored,legacy)
    assert 'legacy' not in restored.loot_shelves
    assert not loot.take(w,restored,{**request,'stash':'legacy','request':'legacy-001'})['ok']


def test_remaining_shelf_is_still_on_map_after_daily_world_reseed():
    w,a,s=setup();loot.reveal(a,s);loot.take(w,a,args(a));w.stashes.clear()
    marker=next(s for s in w.view(a.id)['stashes'] if s[0]=='shelf-test')
    assert marker[4] and marker[7]
    assert loot.take(w,a,args(a,1,rid='after-reseed-001'))['ok']


def test_receipts_revision_range_quantity_capacity_and_conditions():
    w,a,s=setup();loot.reveal(a,s);original=args(a);assert loot.take(w,a,original)['ok']
    assert not loot.take(w,a,{**original,'qty':1})['ok']
    assert not loot.take(w,a,{**original,'request':'stale-001'})['ok']
    a.lat,a.lng=shift(LAT,LNG,100,0)
    assert not loot.take(w,a,args(a,rid='far-away-001'))['ok']
    a.lat,a.lng=LAT,LNG
    for qty in [0,-1,True,10001,4]:
        assert not loot.take(w,a,args(a,qty,rid='invalid-001'))['ok']
    a.add('plank',1000)
    assert not loot.take(w,a,args(a,rid='heavy-001'))['ok']
    assert a.loot_shelves[s['id']]['items'][0]['qty']==3


async def hub_setup(maker):
    async with maker() as db:
        p=(await create_anonymous_player(db,'chosen-loot-device-12345','LootTest'))['player']
    h=Hub();h.world.spawner=None;h.director.policy=lambda *a:'quiet';h.clock=lambda:100
    sent=[]
    async def send(m):sent.append(m)
    c,a,_=await h.join(p,send);a.lat,a.lng=LAT,LNG
    s={'id':'shelf-test','lat':LAT,'lng':LNG,'kind':'bag','loot':[['water',5]]}
    a.pending_search=copy.deepcopy(s)
    await h._send_state(c,a,100,force=True)
    return h,c,h.world.actors[p.id],sent


@pytest.mark.asyncio
async def test_durable_reveal_and_simultaneous_taps_conserve_stock(maker):
    h,c,a,sent=await hub_setup(maker);request=args(a)
    results=await asyncio.gather(h.act(c,'loot',request),h.act(c,'loot',request))
    assert all(r['ok'] for r in results)
    a=h.world.actors[a.id];assert a.count('water')==4 # two starter + two taken
    assert a.loot_shelves['shelf-test']['items'][0]['qty']==3
    async with maker() as db:
        restored=store.from_state(await db.get(Survivor,c.survivor_id),'T')
    assert restored.loot_shelves==a.loot_shelves and restored.count('water')==a.count('water')
    assert any(e['e']=='found' for m in sent for e in m.get('ev',[]))


@pytest.mark.asyncio
async def test_failed_transfer_never_publishes_mutation(maker,monkeypatch):
    h,c,a,sent=await hub_setup(maker);before=store.to_state(a);sent.clear()
    async def fail(*args,**kw):raise RuntimeError('test failure')
    monkeypatch.setattr(store,'save',fail)
    assert not (await h.act(c,'loot',args(a)))['ok']
    assert store.to_state(h.world.actors[a.id])==before and not sent


@pytest.mark.asyncio
async def test_failed_reveal_retries_without_premature_claim_or_reward(maker,monkeypatch):
    h,c,a,sent=await hub_setup(maker)
    a.claimed.clear();a.loot_shelves.clear();a.xp=0;a.skill_xp={};sent.clear()
    a.pending_search={'id':'retry','lat':LAT,'lng':LNG,'kind':'bag','loot':[['water',5]]}
    save=store.save
    async def fail(*args,**kw):raise RuntimeError('test failure')
    monkeypatch.setattr(store,'save',fail)
    await h._send_state(c,a,100,force=True)
    assert not a.claimed and not a.loot_shelves and a.xp==0 and a.pending_search
    assert not any(e['e']=='found' for m in sent for e in m.get('ev',[]))
    monkeypatch.setattr(store,'save',save)
    await h._send_state(c,a,101,force=True)
    current=h.world.actors[a.id]
    assert current.claimed=={'retry'} and current.xp==25 and current.pending_search is None
