import pytest
from app.game import broadcasts,survival
from app.game.sim import Actor,World,Zed
from app.geo import cell_of
from app.game.hub import Hub
from app.models import WorldEvent


def test_reports_are_regional_restart_stable_and_listening_is_quiet():
 w=World();w.now=1000000;a=Actor(id=1,lat=44.9778,lng=-93.265,placed_at=1)
 item=a.add('radio',1);before=list(a.items);hp=a.hp;end=a.end
 r=broadcasts.action(w,a,item=item['id']);assert r['ok'] and r['broadcast']['lines']
 other=World();other.now=w.now;b=Actor(id=2,lat=a.lat,lng=a.lng,placed_at=1);b.add('radio',1)
 assert r['broadcast']==broadcasts.report(other,b)['broadcast']
 assert a.items==before and a.hp==hp and a.end==end
 assert not broadcasts.action(w,a,item=999)['ok']
 assert not broadcasts.action(w,a,object='unknown-radio')['ok']


def test_event_schedule_bounded_and_shared():
 region=cell_of(44.9778,-93.265,6)
 events=[broadcasts.event(region,n) for n in range(20)]
 assert any(events) and any(e is None for e in events)
 for n,e in enumerate(events):
  assert e==broadcasts.event(region,n)
  if e:assert n*broadcasts.BLOCK<=e['at']<(n+1)*broadcasts.BLOCK and e['radius']<=140

@pytest.mark.asyncio
async def test_event_commits_once_before_noise_and_restart_does_not_repeat(maker):
 h=Hub();w=h.world;a=Actor(id=1,lat=44.9778,lng=-93.265,placed_at=1);w.actors[a.id]=a
 region=cell_of(a.lat,a.lng,6);e=next(broadcasts.event(region,n) for n in range(20) if broadcasts.event(region,n))
 w.now=e['at']+1
 calls=[];w.noise=lambda *args,**kw:calls.append(args)
 await h._broadcast_events();await h._broadcast_events();assert len(calls)==1
 async with maker() as s:
  assert await s.get(WorldEvent,e['id'])
  w.broadcast_fired=await broadcasts.load(s)
 await h._broadcast_events();assert len(calls)==1
 w.broadcast_fired.clear();await h._broadcast_events();assert len(calls)==1 # durable receipt, even without memory

@pytest.mark.asyncio
async def test_failed_event_save_does_not_emit_noise(maker,monkeypatch):
 from app.game import hub
 h=Hub();w=h.world;a=Actor(id=1,lat=44.9778,lng=-93.265,placed_at=1);w.actors[a.id]=a
 region=cell_of(a.lat,a.lng,6);e=next(broadcasts.event(region,n) for n in range(20) if broadcasts.event(region,n));w.now=e['at']+1
 def fail():raise RuntimeError('event transaction fixture')
 monkeypatch.setattr(hub,'get_sessionmaker',fail)
 calls=[];w.noise=lambda *args,**kw:calls.append(args)
 await h._broadcast_events();assert not calls and e['id'] not in w.broadcast_fired


def test_fixture_radio_requires_reach_and_intact_fixture():
 from tests.test_equipment_home import shelter
 w,a,b=shelter();radios=[o for o in survival.objects(w,a) if o['kind']=='radio']
 # The shelter fixture is generic residential map data, not a radio injected into the world.
 if not radios:
  b.type='house';radios=[o for o in survival.objects(w,a) if o['kind']=='radio']
 assert radios
 radio=radios[0];a.lat,a.lng=radio['lat'],radio['lng']
 assert broadcasts.action(w,a,object=radio['id'])['ok']
 a.lat+=.001;assert not broadcasts.action(w,a,object=radio['id'])['ok']
 a.lat,a.lng=radio['lat'],radio['lng'];survival.defaults(a);a.home['mutations'][radio['id']]={**radio,'hp':0}
 assert not broadcasts.action(w,a,object=radio['id'])['ok']
