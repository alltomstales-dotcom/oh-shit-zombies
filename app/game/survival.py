"""Persistent work, resources and shelter life. No I/O or client-side rewards."""
import copy
import math
import random
from app.game.content import ITEMS, TUNE
from app.game.progression import award, skill_level
from app.geo import cell_of, _decode_bbox
from app.rng import seeded

RECIPES = {
 "repair_kit":dict(name="Make a vehicle repair kit",need={"scrap":2,"cloth":1},tool="hammer",bench="workbench",out={"repair_kit":1},seconds=6,skill="metalworking",knowledge="vehicle_kits",learn_from="Roadside Repair Magazine"),
 "reinforced_vest":dict(name="Make a reinforced vest",need={"leather":1,"plate":2,"cloth":2},tool="hammer",bench="workbench",out={"reinforced_vest":1},seconds=8,skill="metalworking",knowledge="protective_gear",learn_from="Protective Clothing Magazine"),
 "kindling":dict(name="Split a log for fuel",need={"log":1},tool="axe",out={"branch":8},seconds=4,skill="carpentry"),
 "planks":dict(name="Saw a log",need={"log":1},tool="saw",out={"plank":4},seconds=5,skill="carpentry"),
 "bandages":dict(name="Tear cloth bandages",need={"cloth":2},out={"bandage":2},seconds=3,skill="first_aid"),
 "stone_axe":dict(name="Make a stone hand axe",need={"stone":2,"branch":2},out={"axe":1},seconds=6,skill="carpentry"),
 "crate":dict(name="Build a storage crate",need={"plank":4,"nails":4},tool="hammer",object="crate",seconds=6,skill="carpentry"),
 "workbench":dict(name="Build a workbench",need={"plank":6,"nails":6},tool="hammer",object="workbench",seconds=8,skill="carpentry"),
 "bed":dict(name="Build a bed",need={"plank":4,"cloth":3},tool="hammer",object="bed",seconds=8,skill="carpentry"),
 "fence":dict(name="Build a fence",need={"plank":3,"nails":2},tool="hammer",object="fence",seconds=6,skill="carpentry"),
 "gate":dict(name="Build a gate",need={"plank":4,"nails":4},tool="hammer",object="gate",seconds=7,skill="carpentry"),
 "rainbarrel":dict(name="Build a rain barrel",need={"plank":4,"scrap":2},tool="hammer",object="rainbarrel",seconds=8,skill="carpentry"),
 "campfire":dict(name="Build a cooking fire",need={"stone":4,"branch":3},object="campfire",seconds=5,skill="cooking"),
 "pickaxe":dict(name="Make a pickaxe",need={"scrap":3,"plank":2},tool="hammer",bench="workbench",out={"pickaxe":1},seconds=8,skill="metalworking"),
 "furnace":dict(name="Build a furnace",need={"stone":8,"scrap":4},tool="hammer",object="furnace",seconds=10,skill="metalworking"),
 "smelt":dict(name="Smelt iron ore",need={"ore":2,"branch":2},bench="furnace",out={"metal":1},seconds=8,skill="metalworking"),
 "metal_plate":dict(name="Forge reinforcement plates",need={"metal":2},tool="hammer",bench="workbench",out={"plate":2},seconds=6,skill="metalworking"),
 "stone_wall":dict(name="Build a stone barrier",need={"stone":6},tool="hammer",object="stone_wall",seconds=9,skill="carpentry"),
 "metal_fence":dict(name="Build a metal fence",need={"metal":3,"plank":2},tool="hammer",object="metal_fence",seconds=9,skill="metalworking"),
 "lantern":dict(name="Repair a lantern",need={"scrap":2,"cloth":1},bench="workbench",out={"lantern":1},seconds=5,skill="metalworking"),
 "generator":dict(name="Rebuild a generator",need={"scrap":6,"metal":2},tool="hammer",bench="workbench",object="generator",seconds=12,skill="metalworking"),
 "fridge":dict(name="Build a cold-storage cabinet",need={"scrap":4,"metal":1},tool="hammer",object="fridge",seconds=9,skill="metalworking"),
 "cook":dict(name="Cook a filling meal",need={"rawfood":1,"branch":1},bench="campfire",out={"meal":1},seconds=5,skill="cooking"),
 "filter":dict(name="Filter and boil water",need={"dirtywater":1,"cloth":1,"branch":1},bench="campfire",out={"water":1},seconds=5,skill="cooking"),
 "garden":dict(name="Plant a garden bed",need={"seeds":1,"branch":2},object="garden",seconds=5,skill="foraging"),
 "rod":dict(name="Make a fishing rod",need={"branch":2,"cloth":2},out={"rod":1},seconds=5,skill="carpentry"),
 "plot":dict(name="Dig a vegetable plot (a day to grow)",need={"seeds":3,"branch":2},object="plot",seconds=8,skill="foraging"),
}
# How long a bed takes and what one harvest gives. The quick garden is unchanged; the plot is the
# slow one. A bed already in the ground keeps the `ready` time it was given when planted.
GROW = {"garden":(300.0,{"rawfood":3,"seeds":1}),"plot":(TUNE["plot_grow_s"],{"rawfood":10,"seeds":3})}
# Jobs a station does by itself on the real clock, also while the game is closed. The materials go in
# with a few seconds of work; the job records what it will give, so later rule changes never alter
# something already on the fire. Collected once, by a second short piece of work.
SLOW = {
 "smoke":dict(name="Smoke rations (an hour)",need={"rawfood":3,"branch":4},bench="campfire",out={"smoked":3},seconds=TUNE["smoke_s"],setup=5,skill="cooking",rule=1),
}
OBJECTS = {
 "television":dict(name="Training television",symbol="▣",hp=25),
 "radio":dict(name="Household radio",symbol="▣",hp=15),
 "bed":dict(name="Bed",symbol="▰",hp=25),"wardrobe":dict(name="Wardrobe",symbol="▥",hp=35,capacity=25),
 "counter":dict(name="Kitchen counter",symbol="▤",hp=30,capacity=20),"chair":dict(name="Chair",symbol="▧",hp=15),
 "crate":dict(name="Storage crate",symbol="▣",hp=40,capacity=25),"workbench":dict(name="Workbench",symbol="⚒",hp=50),
 "fence":dict(name="Wood fence",symbol="╳",hp=60,solid=True),"gate":dict(name="Gate",symbol="⇄",hp=60,solid=True),
 "stone_wall":dict(name="Stone barrier",symbol="▦",hp=130,solid=True),"metal_fence":dict(name="Metal fence",symbol="╬",hp=180,solid=True),
 "campfire":dict(name="Cooking fire",symbol="♨",hp=20),"rainbarrel":dict(name="Rain barrel",symbol="◉",hp=35),
 "furnace":dict(name="Furnace",symbol="♨",hp=80),"generator":dict(name="Generator",symbol="⚡",hp=70),
 "fridge":dict(name="Cold-storage cabinet",symbol="▥",hp=50,capacity=35),"garden":dict(name="Garden bed",symbol="❀",hp=20),
 "plot":dict(name="Vegetable plot",symbol="❀",hp=20),
}


def wait_text(seconds):
 seconds=max(0,seconds)
 if seconds<90:return 'a minute'
 if seconds<5400:return f'{round(seconds/60)} minutes'
 return f'{round(seconds/3600)} hours'
def shift(lat,lng,dx,dy):return [lat+dy/111320,lng+dx/(111320*math.cos(math.radians(lat)))]
def dist(a,b):return math.hypot((a[0]-b[0])*111320,(a[1]-b[1])*111320*math.cos(math.radians(a[0])))
def pos(a):return [a.lat,a.lng]
def defaults(a):
 if a.home is not None:
  for k,v in {"objects":[],"mutations":{},"nodes":{},"defenses":{},"next_object":1,"work_receipts":[],"node_positions":{}}.items():a.home.setdefault(k,copy.deepcopy(v))


def furniture(w,a):
 defaults(a)
 changes=(a.home or {}).get('mutations',{})
 result=[]
 inside=w.buildings.containing(pos(a))
 candidates=[inside] if inside else []
 if a.home and dist(pos(a),[a.home['lat'],a.home['lng']])<35:
  home_building=w.buildings.items.get(a.home['building'])
  if home_building and home_building not in candidates:candidates.append(home_building)
 for b in candidates:
  for i,r in enumerate(b.rooms):
   origin=b.ll(r['pos'])
   residential=b.type in ('house','residential','apartments','cabin','detached')
   names=('Rest sofa','Household cupboard','Kitchen counter','Living-room chair') if residential and i==0 else ('Bed','Wardrobe','Storage counter','Bedroom chair') if residential else ('Rest cot','Supply cabinet','Stockroom shelves','Stool') if i else ('Rest cot','Supply cabinet','Service counter','Waiting chair')
   if b.type in ('hospital','clinic'):names=('Treatment bed','Medical cupboard','Treatment counter','Waiting chair')
   kinds=('bed','crate','workbench','chair') if b.type in ('industrial','warehouse','garage','workshop') else ('bed','wardrobe','counter','chair')
   if 'workbench' in kinds:names=('Rest cot','Parts crate','Workshop bench','Workshop stool')
   if i==0:
    kinds=(*kinds[:3],'radio','television');names=(*names[:3],'Household radio' if residential else 'Emergency radio','Training television')
   for j,kind in enumerate(kinds):
    oid=f'fixture:{b.id}:'+ (f'f{a.floor_level}:' if a.floor_level else '')+f'{i}:{j}'
    if oid in changes:
     o=changes[oid]
     if o is not None:result.append(o)
     continue
    xy=next((q for dx,dy in (((2,2),(-2,2),(2,-2),(-2,-2),(0,0))[j],((3,3),(-3,3),(3,-3),(-3,-3),(0,3))[j],((4,4),(-4,4),(4,-4),(-4,-4),(0,-3))[j])
             if b.contains(q:=shift(*origin,dx,dy)) and w.buildings.clear(origin,q) and all(dist(q,[o['lat'],o['lng']])>=1.5 for o in result)),None)
    if xy:
     result.append(dict(id=oid,kind=kind,lat=xy[0],lng=xy[1],building=b.id,floor_level=a.floor_level,name=names[j],hp=OBJECTS[kind]['hp'],items=[],next_item=1,capacity=OBJECTS[kind].get('capacity',0),generated=True))
 return result


def objects(w,a):
 return furniture(w,a)+[o for o in (a.home or {}).get('objects',[]) if o.get('floor_level',0)==a.floor_level]


def nodes(w,a,cell=None):
 if a.floor_level:return []
 result=[]
 cell=cell or cell_of(a.lat,a.lng,7)
 if len(cell)!=7 or any(c not in '0123456789bcdefghjkmnpqrstuvwxyz' for c in cell):return []
 if hasattr(w,'resource_regions') and cell[:6] not in w.resource_regions:return []
 la0,la1,ln0,ln1=_decode_bbox(cell)
 center=[(la0+la1)/2,(ln0+ln1)/2]
 if dist(pos(a),center)>350:return []
 defaults(a)
 saved=(a.home or {}).get('node_positions',{})
 rng=seeded('resources:'+cell)
 for i,kind in enumerate(('tree','tree','rubble','rock','ore','forage','pond')):
  oid=f'resource:{cell}:{i}'
  point=None
  for _ in range(30):
   q=[rng.uniform(la0+2/111320,la1-2/111320),rng.uniform(ln0+2/111320,ln1-2/111320)]
   if w.buildings.containing(q) is None and w.buildings.clear(q,q):point=q;break
  if oid in saved:
   old=saved[oid]
   if w.buildings.containing(old) is None and w.buildings.clear(old,old):point=old
   elif oid in (a.home or {}).get('nodes',{}):continue
   elif point:saved[oid]=point;a.dirty=True
  elif point and a.home is not None:
   saved[oid]=point;a.dirty=True
  if point:
   remaining=(a.home or {}).get('nodes',{}).get(oid,3 if kind in ('tree','rock','ore') else 2)
   result.append(dict(id=oid,kind=kind,lat=point[0],lng=point[1],remaining=remaining,generated=True,name={'tree':'Generated tree','rubble':'Salvage rubble','rock':'Stone outcrop','ore':'Iron deposit','forage':'Foraging patch','pond':'Generated fishing spot'}[kind]))
 return result


def target(w,a,oid):
 ns=nodes(w,a,oid.split(':')[1]) if oid and oid.startswith('resource:') and len(oid.split(':'))==3 and len(oid.split(':')[1])==7 else nodes(w,a)
 return next((o for o in objects(w,a)+ns if o['id']==oid),None)
def in_range(w,a,o,r=2.7):return dist(pos(a),[o['lat'],o['lng']])<=r and w.buildings.clear(pos(a),[o['lat'],o['lng']],ignore=o.get('id'))
def tool(a,code):return next((i for i in a.items if i['code']==code and (i.get('cond') or 0)>0),None)
def station(w,a,kind):return next((o for o in objects(w,a) if o['kind']==kind and o.get('hp',1)>0 and in_range(w,a,o)),None)


def snap(a,ll):
 origin=[a.home['lat'],a.home['lng']] if a.home else pos(a)
 mx=111320*math.cos(math.radians(origin[0]))
 return [origin[0]+math.floor((ll[0]-origin[0])*111320+.5)/111320,origin[1]+math.floor((ll[1]-origin[1])*mx+.5)/mx]


def validate_place(w,a,ll,kind,rotation=0):
 if len(ll)!=2 or not all(math.isfinite(x) for x in ll) or dist(pos(a),ll)>8:return False
 if not w.buildings.clear(ll,ll):return False
 if any(dist(ll,[o['lat'],o['lng']])<1.2 for o in objects(w,a)):return False
 if any(dist(ll,[x.lat,x.lng])<1 for x in list(w.actors.values())+list(w.zeds.values()) if not getattr(x,'dead',False)):return False
 for b in w.nearby_buildings(a,30):
  p=b.xy(ll)
  from app.game.buildings import point_segment
  if any(point_segment(p,o['a'],o['b'])<3 for o in b.openings):return False
 # Solid construction remains outside: indoor furniture has no movement collision,
 # leaving the existing room navigation/automatic exit reliable.
 if OBJECTS.get(kind,{}).get('solid'):
  angle=math.radians(rotation%180);dx,dy=math.cos(angle)*1.3,math.sin(angle)*1.3
  lo,hi=shift(*ll,-dx,-dy),shift(*ll,dx,dy)
  if any(w.buildings.containing(p) for p in (lo,ll,hi)) or not w.buildings.clear(lo,hi):return False
  from app.game.buildings import point_segment
  def xy(p):return ((p[1]-ll[1])*111320*math.cos(math.radians(ll[0])),(p[0]-ll[0])*111320)
  if any(point_segment(xy([x.lat,x.lng]),xy(lo),xy(hi))<1 for x in list(w.actors.values())+list(w.zeds.values()) if not getattr(x,'dead',False)):return False
 return w.buildings.clear(pos(a),ll)


def start(w,a,args):
 from app.game import bases
 if not bases.can_build(a):return {'ok':False,'why':'this base grants storage access; ask the owner for Builder access to work here'}
 if not a.home:return {'ok':False,'why':'choose a home before investing in work'}
 defaults(a)
 if any(z.alive and z.target==a.id and z.state=='engaged' for z in w.zeds.values()):return {'ok':False,'why':'escape the zombies first'}
 args=copy.deepcopy(args)
 if 'lat' in args or 'lng' in args:
  if not all(isinstance(args.get(k),(int,float)) and math.isfinite(args[k]) for k in ('lat','lng')) or not -90<=args['lat']<=90 or not -180<=args['lng']<=180:return {'ok':False,'why':'choose a valid nearby map position'}
  args['lat'],args['lng']=snap(a,[args['lat'],args['lng']])
 op=args.get('op','');oid=args.get('object');o=target(w,a,oid) if oid else None
 if a.end<8 and op!='rest':return {'ok':False,'why':'rest before working'}
 recipe=args.get('recipe');spec=RECIPES.get(recipe) if recipe else None
 if op=='craft':
  if spec is None:return {'ok':False,'why':'unknown recipe'}
  if spec.get('knowledge') and spec['knowledge'] not in a.knowledge:return {'ok':False,'why':'learn this recipe from '+spec['learn_from']}
  missing=[ITEMS[c]['name'] for c,n in spec['need'].items() if a.count(c)<n]
  if missing:return {'ok':False,'why':'need '+', '.join(missing)}
  if spec.get('tool') and not tool(a,spec['tool']):return {'ok':False,'why':'need a usable '+ITEMS[spec['tool']]['name']}
  if spec.get('bench') and not station(w,a,spec['bench']):return {'ok':False,'why':'work beside a '+OBJECTS[spec['bench']]['name']}
  if spec.get('object'):
   ll=[args.get('lat',float('nan')),args.get('lng',float('nan'))]
   if not validate_place(w,a,ll,spec['object'],args.get('rotation',0)):return {'ok':False,'why':'choose a clear nearby place away from exits and people'}
  seconds=spec['seconds']*(1-.05*skill_level(a,spec['skill']))
 elif op=='repair_gear':
  row=a.item(args.get('item'))
  if not row or row.get('cond') is None or row['cond']>=ITEMS[row['code']].get('cond',10):return {'ok':False,'why':'choose damaged equipment'}
  code='cloth' if ITEMS[row['code']]['kind'] in ('clothing','bag') else 'scrap'
  if a.count(code)<2:return {'ok':False,'why':'need two '+ITEMS[code]['name']}
  seconds=4
 elif op in ('slow','take'):
  if not o or not in_range(w,a,o):return {'ok':False,'why':'walk closer to the selected object'}
  if o.get('generated') or o.get('hp',1)<=0:return {'ok':False,'why':'this needs a working station you built'}
  job=o.get('job')
  if op=='slow':
   spec=SLOW.get(recipe)
   if spec is None or spec['bench']!=o['kind']:return {'ok':False,'why':'that job does not fit this object'}
   if job:return {'ok':False,'why':'something is already on here; collect it first'}
   missing=[ITEMS[c]['name'] for c,n in spec['need'].items() if a.count(c)<n]
   if missing:return {'ok':False,'why':'need '+', '.join(missing)}
   seconds=spec['setup']
  else:
   spec=None
   if not job:return {'ok':False,'why':'nothing is waiting here'}
   if w.now<job['ready']:return {'ok':False,'why':'not ready: about '+wait_text(job['ready']-w.now)+' to go'}
   seconds=3
 elif op in ('chop','mine','forage','salvage','rest','collect','harvest','fish','move','repair','fuel','toggle','open_gate'):
  if not o or not in_range(w,a,o):return {'ok':False,'why':'walk closer to the selected object'}
  kind=o['kind']
  if o.get('hp',1)<=0 and op not in ('repair','salvage'):return {'ok':False,'why':'repair this broken object first'}
  valid={'chop':['tree'],'mine':['rock','ore'],'forage':['forage','rubble'],'salvage':list(OBJECTS),'rest':['bed'],'collect':['rainbarrel'],'harvest':list(GROW),'fish':['pond'],'fuel':['generator'],'toggle':['generator'],'open_gate':['gate']}
  if op in valid and kind not in valid[op]:return {'ok':False,'why':'that action does not fit this object'}
  needtool={'chop':'axe','mine':'pickaxe','salvage':'hammer','fish':'rod'}.get(op)
  if needtool and not tool(a,needtool):return {'ok':False,'why':'need a usable '+ITEMS[needtool]['name']}
  if 'remaining' in o and o['remaining']<=0:return {'ok':False,'why':'this spot is depleted; explore another area'}
  if op=='salvage' and o.get('items'):return {'ok':False,'why':'empty the container before dismantling it'}
  if op=='salvage' and o.get('job'):return {'ok':False,'why':'collect what is on it before dismantling it'}
  if op=='move' and (o.get('items') or OBJECTS.get(kind,{}).get('solid')):return {'ok':False,'why':'empty furniture first; dismantle defenses instead'}
  if op=='move' and not validate_place(w,a,[args.get('lat',float('nan')),args.get('lng',float('nan'))],kind):return {'ok':False,'why':'choose a clear place away from doors'}
  if op=='repair' and a.count('plank')<1 and a.count('plate')<1:return {'ok':False,'why':'need a plank or reinforcement plate'}
  if op=='fuel' and a.count('fuel')<1:return {'ok':False,'why':'need generator fuel'}
  if op=='collect' and o.get('water',0)<1:return {'ok':False,'why':'the barrel is still collecting water'}
  if op=='harvest' and w.now<o.get('ready',w.now+300):return {'ok':False,'why':'the crop is still growing: about '+wait_text(o.get('ready',w.now+300)-w.now)+' to go'}
  seconds={'chop':7,'mine':7,'forage':4,'salvage':5,'rest':10,'collect':3,'harvest':3,'fish':8,'move':4,'repair':4,'fuel':3,'toggle':1,'open_gate':1}[op]
 elif op in ('barricade','repair_opening','remove_barricade'):
  b,opening=w.buildings.opening(args.get('opening',''))
  if not opening:return {'ok':False,'why':'select a nearby door or window'}
  p=b.ll([(x+y)/2 for x,y in zip(opening['a'],opening['b'])])
  if dist(pos(a),p)>2.7:return {'ok':False,'why':'approach the opening first'}
  from app.game.buildings import point_segment
  if op!='remove_barricade' and any(point_segment(b.xy(pos(x)),opening['a'],opening['b'])<.55 for x in w.actors.values() if not x.dead):return {'ok':False,'why':'step clear of the passage before barricading it'}
  if op!='remove_barricade' and (not tool(a,'hammer') or a.count('plank')<2 or a.count('nails')<2):return {'ok':False,'why':'need a hammer, two planks and two nails'}
  if op!='remove_barricade':
   blocked={oid for h in w.homes.values() for oid,d in h.get('defenses',{}).items() if d.get('hp',0)>0}|{opening['id']}
   occupants=[x for x in w.actors.values() if not x.dead and w.buildings.containing(pos(x)) is b]
   if any(not w.buildings.exit_plan(pos(x),blocked)['ok'] for x in occupants):return {'ok':False,'why':'keep this opening clear: someone needs it to escape'}
  seconds=5
 else:return {'ok':False,'why':'unknown work action'}
 if op in ("chop","mine","forage","fish"):
  seconds*=1-.04*skill_level(a,"mining" if op=="mine" else "foraging")
 a.sprinting=False
 a.channel={'kind':'work','op':op,'args':copy.deepcopy(args),'start':pos(a),'ends':w.now+seconds,'total':seconds}
 from app.game import weather
 w.noise(a.lat,a.lng,(35 if op in ('chop','mine','salvage','craft','barricade') else 8)*(TUNE['rain_noise_mult'] if weather.rain(a.lat,a.lng,w.now) else 1),a)
 return {'ok':True,'channel':seconds,'message':'Working: '+(spec['name'] if spec else op.replace('_',' '))}


def finish(w,a,ch):
 if dist(pos(a),ch['start'])>1 or a.end<4 and ch['op']!='rest':
  w._ev(a,'work',message='Work interrupted; materials were kept.');return
 args=ch['args'];op=ch['op'];oid=args.get('object');o=target(w,a,oid) if oid else None
 # Revalidate tools/materials/target at completion without starting another channel.
 before=a.channel;a.channel=None;oldnoise=w.noise;w.noise=lambda *x,**y:None
 try:check=start(w,a,args)
 finally:a.channel=before;w.noise=oldnoise
 if not check['ok']:w._ev(a,'work',message=check['why']);return
 defaults(a);h=a.home;skill='carpentry';message='Completed '+op.replace('_',' ')
 if op=='craft':
  spec=RECIPES[args['recipe']]
  for code,n in spec['need'].items():assert a.take(code,n)
  for code,n in spec.get('out',{}).items():a.add(code,n)
  if spec.get('tool'):tool(a,spec['tool'])['cond']-=1
  if spec.get('object'):
   kind=spec['object'];obj=dict(id=f'built:{a.home_owner or a.id}:{h["next_object"]}',kind=kind,lat=args['lat'],lng=args['lng'],rotation=args.get('rotation',0)%180,hp=OBJECTS[kind]['hp'],items=[],next_item=1,capacity=OBJECTS[kind].get('capacity',0),floor_level=a.floor_level)
   h['next_object']+=1
   if kind in GROW:obj['ready']=w.now+GROW[kind][0]
   if kind=='rainbarrel':obj.update(water=0,fill_at=w.now)
   h['objects'].append(obj)
  skill=spec['skill'];message=spec['name']+' completed'
 elif op in ('chop','mine','forage','fish'):
  h['nodes'][oid]=o['remaining']-1
  yields={'chop':{'log':2},'mine':{'ore' if o['kind']=='ore' else 'stone':3},'forage':{'stone':3,'branch':3,'scrap':2,'nails':3,'fuel':1} if o['kind']=='rubble' else {'rawfood':2,'seeds':1,'branch':2,'cloth':1},'fish':{'rawfood':2}}[op]
  for code,n in yields.items():a.add(code,n)
  needtool={'chop':'axe','mine':'pickaxe','fish':'rod'}.get(op)
  if needtool:tool(a,needtool)['cond']-=1
  skill='mining' if op=='mine' else 'foraging';message='Gathered '+', '.join(f'{n} {ITEMS[c]["name"]}' for c,n in yields.items())
 elif op=='salvage':
  materials={'plank':3,'nails':4,'cloth':2,'scrap':2} if o.get('generated') else {c:max(1,n//3) for c,n in next((r['need'] for r in RECIPES.values() if r.get('object')==o['kind']),{}).items() if n>1}
  for code,n in materials.items():a.add(code,n)
  if o.get('generated'):h['mutations'][oid]=None
  else:h['objects']=[x for x in h['objects'] if x['id']!=oid]
  tool(a,'hammer')['cond']-=1;message='Salvaged planks, nails, cloth and scrap'
 elif op=='repair_gear':
  row=a.item(args['item']);code='cloth' if ITEMS[row['code']]['kind'] in ('clothing','bag') else 'scrap';a.take(code,2)
  row['cond']=min(ITEMS[row['code']].get('cond',10),row['cond']+5);message='Repaired '+ITEMS[row['code']]['name']
 elif op in ('move','repair','rest','collect','harvest','fuel','toggle','open_gate'):
  changed=copy.deepcopy(o)
  if op=='move':changed.update(lat=args['lat'],lng=args['lng'])
  elif op=='repair':
   code='plate' if a.count('plate') else 'plank';a.take(code,1);changed['hp']=min(OBJECTS[o['kind']]['hp'],o['hp']+(70 if code=='plate' else 35))
  elif op=='rest':a.end=min(100,a.end+45);a.sleep=max(0,a.sleep-35);a.panic=max(0,a.panic-25);message='Rested: recovered endurance and sleep'
  elif op=='collect':changed['water']-=1;a.add('dirtywater',1)
  elif op=='harvest':
   grow,crop=GROW[o['kind']]
   for code,n in crop.items():a.add(code,n)
   changed['ready']=w.now+grow;skill='foraging';message='Harvested '+', '.join(f'{n} {ITEMS[c]["name"]}' for c,n in crop.items())+'. Replanted.'
  elif op=='fuel':a.take('fuel',1);changed['fuel']=min(600,changed.get('fuel',0)+180)
  elif op=='toggle':
   if not changed.get('on') and changed.get('fuel',0)<=0:return
   changed['on']=not changed.get('on',False)
  elif op=='open_gate':changed['open']=not changed.get('open',False)
  if o.get('generated'):h['mutations'][oid]=changed
  else:h['objects']=[changed if x['id']==oid else x for x in h['objects']]
  if op in ('rest','toggle','open_gate'):skill=None
 elif op in ('slow','take'):
  changed=copy.deepcopy(o)
  if op=='slow':
   spec=SLOW[args['recipe']]
   for code,n in spec['need'].items():assert a.take(code,n)
   changed['job']=dict(recipe=args['recipe'],rule=spec['rule'],name=spec['name'],out=dict(spec['out']),skill=spec['skill'],started=w.now,ready=w.now+spec['seconds'])
   skill=None;message=spec['name'].split(' (')[0]+': started. Ready in about '+wait_text(spec['seconds'])+', whether or not you wait.'
  else:
   job=changed.pop('job')
   for code,n in job['out'].items():a.add(code,n)
   skill=job.get('skill');message='Collected '+', '.join(f'{n} {ITEMS[c]["name"]}' for c,n in job['out'].items())
  h['objects']=[changed if x['id']==oid else x for x in h['objects']]
 elif op in ('barricade','repair_opening','remove_barricade'):
  oid=args['opening'];b,opening=w.buildings.opening(oid)
  if op=='remove_barricade':h['defenses'].pop(oid,None)
  else:
   a.take('plank',2);a.take('nails',2);tool(a,'hammer')['cond']-=1
   h['defenses'][oid]={'hp':80,'building':b.id};opening['open']=False;w.buildings.dirty.add(oid);w.buildings.revision+=1
 a.end=max(0,a.end-(0 if op=='rest' else 6));a.dirty=True
 h['revision']+=1
 if skill:award(a,skill,30 if op=='take' else 12)
 w._ev(a,'work',message=message)


def update(w,a,dt):
 if a.lat==0 and a.lng==0:return
 a.dirty=True
 a.hunger=min(100,a.hunger+dt/45)
 a.thirst=min(100,a.thirst+dt/30*(1.5 if a.sprinting else 1))
 a.sleep=min(100,a.sleep+dt/90)
 if (a.hunger>90 or a.thirst>90) and a.hp>5:a.hp=max(5,a.hp-dt*.03);a.dirty=True
 def decay(items,factor):
  for i in items:
   if ITEMS[i['code']].get('perishable'):
    i['cond']=max(0,i.get('cond',100)-dt*100/1800*factor);a.dirty=True
 decay(a.items,1)
 defaults(a)
 if not a.home:return
 # Members on different floors still share one utility/food tick per base instant.
 r=w._level_root or w
 ticks=getattr(r,'_home_ticks',None)
 if ticks is None:r._home_ticks={};ticks=r._home_ticks
 key=a.home_owner or a.id
 if ticks.get(key)==w.now:return
 ticks[key]=w.now
 powered=False
 from app.game import weather
 raining=bool(a.home['objects']) and weather.rain(a.home['lat'],a.home['lng'],w.now) is not None
 for o in a.home['objects']:
  if o['kind']=='rainbarrel':
   elapsed=w.now-o.get('fill_at',w.now);per=TUNE['rain_barrel_s'] if raining else 30   # rain where the barrel stands
   if elapsed>=per:o['water']=min(5,o.get('water',0)+int(elapsed/per));o['fill_at']=w.now;a.dirty=True
  if o['kind']=='generator' and o.get('on'):
   if o.get('hp',0)<=0:o['on']=False;continue
   o['fuel']=max(0,o.get('fuel',0)-dt);o['on']=o['fuel']>0;powered|=o['on'];a.dirty=True
   if o['on'] and w.now-o.get('noise_at',0)>=5:w.noise(o['lat'],o['lng'],55,a);o['noise_at']=w.now
 a.home['powered']=any(o['kind']=='generator' and o.get('on') and dist([o['lat'],o['lng']],[a.home['lat'],a.home['lng']])<20 for o in a.home['objects'])
 # Refrigeration has a gameplay benefit: fresh supplies last longer when powered.
 for o in a.home['objects']+list(x for x in a.home.get('mutations',{}).values() if x):
  cold=o['kind']=='fridge' and any(g['kind']=='generator' and g.get('on') and dist([g['lat'],g['lng']],[o['lat'],o['lng']])<20 for g in a.home['objects'])
  decay(o.get('items',[]),.1 if cold else 1)
 decay(a.home['items'],1)


def objective(a):
 if not a.home:return 'Find a room, choose Home, and secure a cupboard for supplies.'
 kinds={o['kind'] for o in a.home.get('objects',[]) if o.get('hp',0)>0}
 if not a.home.get('items'):return 'Store spare water or bandages at home before a supply trip.'
 if 'workbench' not in kinds:return 'Dismantle spare furniture: collect 6 planks and 6 nails for a workbench.'
 if not a.count('axe'):return 'Scavenge rubble, then craft a stone axe to gather logs.'
 if not any(k in kinds for k in ('fence','gate','stone_wall','metal_fence')):return 'Chop a tree, saw logs, and build a fence away from your escape route.'
 if 'campfire' not in kinds or 'rainbarrel' not in kinds:return 'Prepare a cooking fire and rain barrel for food and drinking water.'
 if 'furnace' not in kinds:return 'Make a pickaxe at your workbench; mine stone and build a furnace.'
 if 'metal_fence' not in kinds:return 'Mine ore and smelt it with wood fuel to build a stronger metal defense.'
 if 'generator' not in kinds:return 'Bring scrap and iron home; rebuild a generator for refrigerated supplies.'
 return 'Keep fuel and food stocked, repair defenses, and explore new deposits.'


def view(w,a):
 obs=objects(w,a)
 la0,la1,ln0,ln1=_decode_bbox(cell_of(a.lat,a.lng,7))
 cells={cell_of(a.lat+dy*(la1-la0),a.lng+dx*(ln1-ln0),7) for dx in (-1,0,1) for dy in (-1,0,1)}
 ns=[n for cell in sorted(cells) for n in nodes(w,a,cell) if dist(pos(a),[n['lat'],n['lng']])<180]
 return {'objects':[{**o,'name':o.get('name',OBJECTS[o['kind']]['name']),'symbol':OBJECTS[o['kind']]['symbol'],'powered':o['kind']=='fridge' and any(g['kind']=='generator' and g.get('on') and dist([g['lat'],g['lng']],[o['lat'],o['lng']])<20 for g in (a.home or {}).get('objects',[])),'reachable':in_range(w,a,o)} for o in obs if not o.get('generated') or (dist(pos(a),[o['lat'],o['lng']])<180 and w.visible(pos(a),[o['lat'],o['lng']]) and (not o.get('building') or o['building']==(w.buildings.containing(pos(a)).id if w.buildings.containing(pos(a)) else None)))],
         'objective':objective(a),'resources':ns,'depletion':copy.deepcopy((a.home or {}).get('nodes',{})),'recipes':{k:{**r,'locked':bool(r.get('knowledge') and r['knowledge'] not in a.knowledge)} for k,r in RECIPES.items()},'slow':SLOW,'needs':{'hunger':round(a.hunger),'thirst':round(a.thirst),'sleep':round(a.sleep)},
         'defenses':copy.deepcopy((a.home or {}).get('defenses',{})),'powered':(a.home or {}).get('powered',False)}


def sync_geometry(w):
 barriers=[]
 protected={oid for h in w.homes.values() for oid,d in h.get('defenses',{}).items() if d.get('hp',0)>0}
 # Boards only need putting up or taking down when the set of boarded openings changes, or when
 # buildings arrive or are laid out again. Visiting every opening of every loaded town on every
 # tick grew with the map.
 key=(w.buildings.stamp(),frozenset(protected))
 if key!=getattr(w,'_boards_key',None):
  w._boards_key=key
  for building in w.buildings.items.values():
   for opening in building.openings:
    wanted=opening['id'] in protected
    if bool(opening.get('barricaded'))!=wanted:opening['barricaded']=wanted;w.buildings.revision+=1
 for pid,h in w.homes.items():
  for oid,d in h.get('defenses',{}).items():
   if d.get('hp',0)<=0:continue
   _,o=w.buildings.opening(oid)
   if o and o['open']:
    o['open']=False;w.buildings.revision+=1;w.buildings.dirty.add(oid)
  for o in h.get('objects',[]):
   if o.get('floor_level',0)!=(w._level_key[1] if w._level_key else 0):continue
   if not OBJECTS.get(o['kind'],{}).get('solid') or o.get('hp',0)<=0 or o.get('open'):continue
   angle=math.radians(o.get('rotation',0));dx,dy=math.cos(angle)*1.3,math.sin(angle)*1.3
   barriers.append(dict(id=o['id'],owner=pid,a=shift(o['lat'],o['lng'],-dx,-dy),b=shift(o['lat'],o['lng'],dx,dy)))
 key=repr(barriers)
 if key!=getattr(w,'_barrier_key',None):
  w._barrier_key=key;w.buildings.obstacles=barriers;w.buildings.revision+=1


def barrier_snapshots(w,a):
 return [dict(id=o['id'],construction=True,outline=[],walls=[[o['a'],o['b']]],openings=[],rooms=[])
         for o in w.buildings.obstacles if dist(pos(a),o['a'])<180]


def batter_opening(w,oid,stepm):
 for pid,h in w.homes.items():
  d=h.get('defenses',{}).get(oid)
  if d and d.get('hp',0)>0:
   d['hp']=max(0,d['hp']-stepm*18);w.home_dirty.add(pid)
   if pid in w.actors:w.actors[pid].dirty=True
   return True
 return False


def batter_object(w,z,stepm):
 if z.state not in ('chase','engaged'):return
 from app.game.buildings import point_segment
 for barrier in w.buildings.obstacles:
  origin=[z.lat,z.lng]
  toxy=lambda p:((p[1]-z.lng)*111320*math.cos(math.radians(z.lat)),(p[0]-z.lat)*111320)
  if point_segment((0,0),toxy(barrier['a']),toxy(barrier['b']))<1.3:
   pid=barrier['owner'];h=w.homes[pid]
   o=next((x for x in h['objects'] if x['id']==barrier['id']),None)
   if o:o['hp']=max(0,o['hp']-stepm*18);w.home_dirty.add(pid)
   if pid in w.actors:w.actors[pid].dirty=True
   break
