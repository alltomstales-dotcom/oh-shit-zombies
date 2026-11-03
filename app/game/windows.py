"""Curtains conceal sight; window work and crossing retain survival costs."""
import math
from app.game import equipment,survival
from app.game.buildings import point_segment,segment_distance

OPS=('hang','curtain_open','curtain_close','remove','clear','vault')

def clear(w,start,end,o):
 # Ignore just this opening for reach, never its wall or another blocked passage.
 saved={k:o[k] for k in ('open','curtain_closed','barricaded')}
 try:
  o.update(open=True,curtain_closed=False,barricaded=False)
  return w.buildings.clear(start,end)
 finally:o.update(saved)

def gloves(a):return any(spec.get('slot')=='hands' for _,spec in equipment.worn_items(a))

def tool(a):
 weapon=a.weapon()
 return weapon if weapon and (weapon.get('cond') or 0)>0 else next((survival.tool(a,c) for c in ('hammer','crowbar','axe') if survival.tool(a,c)),None)

def inspect(w,a,oid,op):
 from app.game.sim import dist_m
 b,o=w.buildings.opening(oid)
 if not o or o['kind']!='window':return b,o,'choose a window'
 if op not in OPS:return b,o,'unknown window action'
 if a.pending_window:return b,o,'your window work is being saved'
 here=(a.lat,a.lng)
 if point_segment(b.xy(here),o['a'],o['b'])>2.7:return b,o,'approach the window first'
 center=b.ll(tuple((x+y)/2 for x,y in zip(o['a'],o['b'])))
 if not clear(w,here,center,o):return b,o,'a wall blocks this window'
 if any(z.alive and z.target==a.id and z.state=='engaged' for z in w.zeds.values()):return b,o,'escape the zombies first'
 if op in ('hang','remove','curtain_open','curtain_close') and not b.contains(here):return b,o,'handle curtains from inside the building'
 if op=='hang' and (o['curtain'] or a.count('cloth')<2):return b,o,'use 2 cloth on a window without a curtain'
 if op in ('remove','curtain_open','curtain_close') and not o['curtain']:return b,o,'there is no curtain here'
 if op=='curtain_open' and not o['curtain_closed']:return b,o,'curtain already open'
 if op=='curtain_close' and o['curtain_closed']:return b,o,'curtain already closed'
 if op=='remove' and a.weight()+.2>w.carry_capacity(a)*1.25+.001:return b,o,'make room for the 2 cloth first'
 if op=='clear' and (not o['broken'] or o['glass_cleared']):return b,o,'no loose glass to clear'
 if op=='clear' and not tool(a):return b,o,'hold a usable weapon or carry a hammer, crowbar or axe'
 if op=='vault':
  if a.floor_level:return b,o,'use the stairs; upper windows are not exits'
  if o.get('barricaded') or not (o['open'] or o['broken']):return b,o,'open the window and remove its boards first'
  if o['curtain_closed']:return b,o,'open or remove the curtain first'
  if a.end<6:return b,o,'recover stamina before climbing'
  if destination(w,a,b,o) is None:return b,o,'the other side is blocked'
 return b,o,None

def destination(w,a,b,o):
 center=tuple((x+y)/2 for x,y in zip(o['a'],o['b']));dx=o['b'][0]-o['a'][0];dy=o['b'][1]-o['a'][1];n=math.hypot(dx,dy)
 if not n:return None
 nx,ny=-dy/n,dx/n;p=b.xy((a.lat,a.lng));side=1 if (p[0]-center[0])*nx+(p[1]-center[1])*ny>=0 else -1
 target=b.ll((center[0]-nx*side*1.2,center[1]-ny*side*1.2))
 return target if clear(w,b.ll(center),target,o) else None

def start(w,a,opening='',op='hang',**_):
 b,o,why=inspect(w,a,opening,op)
 if why:return {'ok':False,'why':why}
 duration=1.2 if op=='vault' else 1.5 if op=='clear' else 2 if op=='hang' else .8
 a.sprinting=False;a.raw=(a.lat,a.lng,1);a.speed=0
 a.channel={'kind':'window_work','opening':opening,'op':op,'ends':w.now+duration,'total':duration,'start':[a.lat,a.lng]}
 center=b.ll(tuple((x+y)/2 for x,y in zip(o['a'],o['b'])))
 w.noise(*center,5 if op in ('clear','vault') else 2,a)
 return {'ok':True,'channel':duration}

def cut(w,a,o):
 if o['broken'] and not o['glass_cleared'] and not gloves(a) and w.rng.random()<.55:
  a.wounds.append({'id':a._next_wound_id,'kind':'scratch','part':'left hand','bleeding':True,'bandaged':False,'clean':False,'t':w.now})
  a._next_wound_id+=1;a.hp=max(.1,a.hp-3);a.dirty=True
  w._ev(a,'work',message='Broken glass cut your hand. Bandage it; clear the glass before crossing again.')

def finish(w,a,ch):
 from app.game.sim import dist_m
 # Pending is an internal commit marker, not another action in progress.
 a.pending_window=None
 b,o,why=inspect(w,a,ch['opening'],ch['op'])
 if not why and dist_m(a.lat,a.lng,*ch['start'])>1:why='you moved away from the window'
 if why:w._ev(a,'interrupted',what='window_work');return False
 op=ch['op']
 if op=='hang':a.take('cloth',2);o.update(curtain=True,curtain_closed=True);message='Curtain hung. Sight blocked; zombies can still hear and break in.'
 elif op=='remove':a.add('cloth',2);o.update(curtain=False,curtain_closed=False);message='Curtain removed; 2 cloth returned.'
 elif op in ('curtain_open','curtain_close'):o['curtain_closed']=op=='curtain_close';message='Curtain '+('closed. Sight blocked; sound still carries.' if o['curtain_closed'] else 'opened.')
 elif op=='clear':
  tool(a)['cond']=max(0,tool(a)['cond']-1);o['glass_cleared']=True;a.end=max(0,a.end-2);message='Loose glass cleared. This window is safe to climb.'
 else:
  target=destination(w,a,b,o);cut(w,a,o);a.end=max(0,a.end-4);a.lat,a.lng=target;a.raw=(*target,1);a.speed=0
  w._ev(a,'vaulted',lat=a.lat,lng=a.lng);message='Climbed through the window.'
 a.dirty=True;w.buildings.dirty.add(o['id']);w.buildings.revision+=1
 w._ev(a,'work',message=message);return True

def crossing(w,a,start,end):
 """Ordinary tap/stick walking through a window pays the same glass/stamina cost."""
 if start==end or w.now<a.window_until:return
 for b in w.buildings.near(start,8):
  p,q=b.xy(start),b.xy(end)
  for o in b.openings:
   if o['kind']!='window' or not (o['open'] or o['broken']):continue
   x,y=o['a'];dx=o['b'][0]-x;dy=o['b'][1]-y
   before=(p[0]-x)*dy-(p[1]-y)*dx;after=(q[0]-x)*dy-(q[1]-y)*dx
   if before*after<=0 and abs(before-after)>1e-5 and segment_distance(p,q,o['a'],o['b'])<.001:
    cut(w,a,o);a.end=max(0,a.end-4);a.window_until=w.now+.9;a.busy_until=max(a.busy_until,a.window_until);a.dirty=True
    w._ev(a,'work',message='Climbing through window'+(' — loose glass: wear gloves or clear it.' if o['broken'] and not o['glass_cleared'] else '.'));return
