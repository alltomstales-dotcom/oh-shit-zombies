import copy
import random
import pytest
from app.game import windows,floors,store
from app.models import BuildingOpening,Survivor
from tests.test_building_world import setup
from tests.test_corpses import setup_hub


def near_window(w,a,b):
 o=next(o for o in b.openings if o['kind']=='window');c=tuple((x+y)/2 for x,y in zip(o['a'],o['b']))
 for dx,dy in ((0,-1),(0,1),(-1,0),(1,0)):
  p=b.ll((c[0]+dx,c[1]+dy))
  if b.contains(p) and w.buildings.clear(p,p):a.lat,a.lng=p;break
 return o


def complete(w,a,o,op):
 assert w.act(a.id,'window',opening=o['id'],op=op)['ok']
 ch=a.channel;a.channel=None;w._finish_channel(a,ch)


def test_curtain_conserves_cloth_and_blocks_sight_not_sound_or_movement():
 w,a,b=setup();o=near_window(w,a,b);a.add('cloth',2)
 c=tuple((x+y)/2 for x,y in zip(o['a'],o['b']));outside=b.ll((c[0],c[1]+2))
 before=w.visible((a.lat,a.lng),outside)
 assert before
 complete(w,a,o,'hang');assert o['curtain_closed'] and a.count('cloth')==0
 assert not w.visible((a.lat,a.lng),outside)
 o['open']=True;assert w.buildings.clear((a.lat,a.lng),outside)
 complete(w,a,o,'curtain_open');assert w.visible((a.lat,a.lng),outside)
 complete(w,a,o,'curtain_close');assert not w.visible((a.lat,a.lng),outside)
 complete(w,a,o,'remove');assert a.count('cloth')==2 and not o['curtain']
 assert not w.act(a.id,'window',opening=o['id'],op='remove')['ok']


def test_window_work_interrupts_without_spending_and_cannot_reach_through_wall():
 w,a,b=setup();o=near_window(w,a,b);a.add('cloth',2)
 assert w.act(a.id,'window',opening=o['id'],op='hang')['ok'];ch=a.channel;a.channel=None
 a.lat+=.001;w._finish_channel(a,ch);assert a.count('cloth')==2 and not o['curtain']
 a.lat,a.lng=b.ll((o['a'][0]-3,o['a'][1]))
 assert not w.act(a.id,'window',opening=o['id'],op='hang')['ok']


def test_clear_requires_usable_tool_preserves_gloves_and_removes_crossing_injury():
 w,a,b=setup();o=near_window(w,a,b);o.update(open=True,broken=True)
 assert not w.act(a.id,'window',opening=o['id'],op='clear')['ok']
 row=a.add('bat',1,3);a.hands=row['id'];complete(w,a,o,'clear')
 assert o['glass_cleared'] and row['cond']==2
 w.rng=random.Random(1);windows.cut(w,a,o);assert not a.wounds
 o['glass_cleared']=False;glove=a.add('gloves');a.worn['hands']=glove['id'];windows.cut(w,a,o);assert not a.wounds
 a.worn.clear();windows.cut(w,a,o);assert a.wounds[0]['kind']=='scratch' and a.infected_at is None


def test_vault_has_stamina_time_range_obstruction_and_floor_guards():
 w,a,b=setup();o=near_window(w,a,b);o.update(open=True,glass_cleared=True)
 a.end=5;assert not w.act(a.id,'window',opening=o['id'],op='vault')['ok']
 a.end=100;old=(a.lat,a.lng);assert w.act(a.id,'window',opening=o['id'],op='vault')['ok']
 assert (a.lat,a.lng)==old and w.movement_speed(a)==0
 ch=a.channel;a.channel=None;w._finish_channel(a,ch)
 assert not b.contains((a.lat,a.lng)) and a.end==96 and any(e['e']=='vaulted' for e in a.events)
 a.floor_level=1;a.floor_building=b.id
 assert not windows.start(w,a,opening=o['id'],op='vault')['ok']


def test_normal_walking_through_smashed_glass_cannot_bypass_costs():
 w,a,b=setup();o=near_window(w,a,b);o.update(open=True,broken=True);w.rng=random.Random(1)
 start=(a.lat,a.lng);end=windows.destination(w,a,b,o);assert end
 windows.crossing(w,a,start,end)
 assert a.end==96 and a.wounds and w.movement_speed(a)==0
 w.now=a.window_until+.1;assert w.movement_speed(a)>0


@pytest.mark.asyncio
async def test_window_cloth_and_geometry_save_atomically_and_restore(maker,monkeypatch):
 h,people,_,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
 w,_,b=setup();h.world.buildings.items[b.id]=b;o=near_window(h.world,a,b);a.add('cloth',2)
 await h.act(c,'window',{'opening':o['id'],'op':'hang'});ch=a.channel;a.channel=None;h.world._finish_channel(a,ch)
 assert a.pending_window and not o['curtain']
 original=store.save
 async def fail(*args,**kw):raise RuntimeError('window persistence fixture')
 monkeypatch.setattr(store,'save',fail);await h._send_state(c,a,100,force=True)
 assert a.pending_window and not o['curtain'] and a.count('cloth')==2
 async with maker() as s:assert await s.get(BuildingOpening,o['id']) is None
 monkeypatch.setattr(store,'save',original);await h._send_state(c,a,100,force=True)
 a=h.world.actors[p.id];assert o['curtain'] and a.count('cloth')==0 and not a.pending_window
 async with maker() as s:
  saved=await s.get(BuildingOpening,o['id']);dead=await s.get(Survivor,c.survivor_id)
  assert saved.state['curtain_closed'] and not store.from_state(dead,'T').count('cloth')
 # Opening refresh/relayout retains the state; upper floors default independently.
 b.relayout(*b.default_edges());assert next(x for x in b.openings if x['id']==o['id'])['curtain_closed']


def test_upper_curtains_are_independent_and_survive_floor_blueprint_restore():
 w,a,b=setup();ground=near_window(w,a,b);ground.update(curtain=True,curtain_closed=True)
 a.floor_level=1;a.floor_building=b.id;upper=w.for_actor(a);ub=upper.buildings.items[b.id];o=near_window(upper,a,ub)
 assert not o['curtain'];a.add('cloth',2);complete(upper,a,o,'hang');saved=floors.state(upper)
 w.levels.clear();w.level_states[(b.id,1)]=saved;restored=w.for_actor(a)
 assert next(x for x in restored.buildings.items[b.id].openings if x['id']==o['id'])['curtain_closed']
 assert ground['curtain_closed']


def test_cancel_returns_to_movement_without_consuming_cloth():
 w,a,b=setup();o=near_window(w,a,b);a.add('cloth',2)
 assert w.act(a.id,'window',opening=o['id'],op='hang')['ok'];assert w.act(a.id,'cancel')['ok']
 assert not a.channel and a.count('cloth')==2 and not o['curtain']


@pytest.mark.asyncio
async def test_window_geometry_is_not_published_before_material_commit(maker,monkeypatch):
 import asyncio
 h,people,_,msgs=await setup_hub(maker);p,c=people[0];a=h.world.actors[p.id]
 w,_,b=setup();h.world.buildings.items[b.id]=b;o=near_window(h.world,a,b);a.add('cloth',2)
 await h.act(c,'window',{'opening':o['id'],'op':'hang'});ch=a.channel;a.channel=None;h.world._finish_channel(a,ch)
 waiting=asyncio.Event();release=asyncio.Event();original=store.save
 async def paused(*args,**kwargs):
  waiting.set();await release.wait();await original(*args,**kwargs)
 monkeypatch.setattr(store,'save',paused)
 task=asyncio.create_task(h._send_state(c,a,100,force=True));await waiting.wait()
 assert not o['curtain_closed'] and a.count('cloth')==2
 release.set();await task
 assert o['curtain_closed'] and h.world.actors[p.id].count('cloth')==0
