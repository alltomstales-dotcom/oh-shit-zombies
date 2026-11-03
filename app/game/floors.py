"""Fictional upper floors in isolated simulation layers, sharing players and durable homes.

No latitude trickery: floors retain the real footprint. Ground-floor actors/zombies
never run in an upstairs layer. Persistent level state is separate from survivor lives.
"""
import copy
import math
from app.game.buildings import Building, Buildings, point_segment


def count(b):
    area=abs(sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(b.poly,b.poly[1:]+b.poly[:1])))/2
    if b.type in ('garage','garages','shed','roof','greenhouse') or area<55:return 1
    return 3 if area>=800 and b.type in ('apartments','office','hospital','commercial') else 2


def landing(b):
    if not b.rooms:return None
    start=b.ll(b.rooms[0]['pos'])
    for dx,dy in ((-1.8,0),(0,-1.8),(1.8,0),(0,1.8),(0,0)):
        p=b.xy(start);q=(p[0]+dx,p[1]+dy)
        if b.contains(b.ll(q)) and all(point_segment(q,*w)>.6 for w in b.walls):return b.ll(q)
    return start


class FloorGeometry(Buildings):
    def clear(self,start,end,radius=.28,vision=False,ignore=None):
        if not vision and not any(b.contains(end) for b in self.items.values()):return False
        return super().clear(start,end,radius,vision,ignore)


def root(w):return w._level_root or w


def layer(w,a):
    r=root(w)
    if not a.floor_level or not a.floor_building:return r
    key=(a.floor_building,a.floor_level)
    cached=r.levels.get(key)
    if cached is not None and getattr(cached,'_awaiting_blueprint',False) and (a.floor_building in r.buildings.items or r.level_states.get(key,{}).get('outline')):
        r.levels.pop(key);cached=None
    if cached is None:
        base=r.buildings.items.get(a.floor_building)
        saved=r.level_states.get(key,{})
        if base is None and saved.get('outline'):
            base=Building(id=a.floor_building,outline=saved['outline'],type=saved.get('type','yes'),name=saved.get('name','Building'))
            r.buildings.items[base.id]=base
        if base is None:
            # A corrupt/missing blueprint must never expose ground-floor attacks upstairs.
            from app.game.sim import World
            paused=World(tune=r.T,light_fn=r.light_fn);paused._level_root=r;paused._level_key=key;paused.now=r.now
            paused.buildings=FloorGeometry();paused.actors={a.id:a};paused.homes=r.homes
            paused.memories=r.memories;paused.memory_dirty=r.memory_dirty;paused.home_dirty=r.home_dirty
            paused._awaiting_blueprint=True;r.levels[key]=paused
            return paused
        from app.game.sim import World, Zed
        from app.rng import seeded
        cached=World(rng=seeded('floor:'+str(key)),tune=r.T,light_fn=r.light_fn)
        cached._level_root=r;cached._level_key=key;cached.now=r.now
        b=copy.deepcopy(base);b.floor_level=a.floor_level
        for o in b.openings:
            o['id']=base.id+f':f{a.floor_level}:'+o['id'].rsplit(':',1)[-1]
            o.update(open=False,broken=False,damage=0.,barricaded=False,locked=False,alarm=False,alarm_triggered=False,curtain=False,curtain_closed=False,glass_cleared=False)
            if o['label']=='Entrance':o.update(kind='window',label='Upper window')
            o.update(saved.get('openings',{}).get(o['id'],{}))
        for i,room in enumerate(b.rooms):
            room['id']=base.id+f':f{a.floor_level}:r{i}'
            room['name']=('Bedroom' if i==0 else 'Study') if base.type in ('house','residential','apartments','cabin','detached','yes') else ('Upper hall' if i==0 else 'Upper storage')
        cached.buildings=FloorGeometry();cached.buildings.items[b.id]=b
        cached.homes=r.homes;cached.home_dirty=r.home_dirty;cached.memories=r.memories;cached.memory_dirty=r.memory_dirty
        cached.durable_learning=getattr(r,'durable_learning',False);cached.durable_loot=getattr(r,'durable_loot',False);cached.durable_corpses=getattr(r,'durable_corpses',False)
        cached.dead_until=r.dead_until
        cached.corpses={cid:copy.deepcopy(body) for cid,body in r.upper_corpses.items() if (body.get('floor_building'),body.get('floor_level'))==key}
        cached.corpse_ready=set(cached.corpses)
        # One possible inhabitant beyond the landing room; never put a zombie on the stairs.
        if 'inhabitants' in saved:
            for row in saved['inhabitants']:
                if r.dead_until.get(row['id'],0)>r.now:continue
                z=Zed(**row);z.state='idle';z.target=None;z.goal=None;z.t_state=r.now+2
                cached.zeds[z.id]=z
        elif len(b.rooms)>1 and not cached.protected_home(landing(b)):
            zid=base.id+f':f{a.floor_level}:inhabitant'
            rng=seeded(zid)
            if rng.random()<.65 and r.dead_until.get(zid,0)<=r.now:
                lat,lng=b.ll(b.rooms[-1]['pos']);z=Zed(id=zid,lat=lat,lng=lng,home=(lat,lng),variant=rng.randrange(16))
                z.t_state=r.now+rng.uniform(2,8);cached.zeds[z.id]=z
        r.levels[key]=cached
    cached.actors={pid:actor for pid,actor in r.actors.items() if (actor.floor_building,actor.floor_level)==key}
    return cached


def stairs(w,a,op='up'):
    r=root(w);current=layer(w,a);b=current.buildings.containing((a.lat,a.lng))
    if a.location_loading_until>r.now:return {'ok':False,'why':'wait for nearby buildings to finish mapping'}
    if b is None or count(b)<2:return {'ok':False,'why':'there are no stairs in this building'}
    point=landing(b)
    if not point:return {'ok':False,'why':'stairs unavailable'}
    from app.game.sim import dist_m
    if dist_m(a.lat,a.lng,*point)>2.7 or not current.buildings.clear((a.lat,a.lng),point):return {'ok':False,'why':'approach the stairs first'}
    if a.dead or a.channel or current.now<a.busy_until-.05:return {'ok':False,'why':'finish your current action first'}
    if any(z.alive and z.target==a.id and z.state=='engaged' for z in current.zeds.values()):return {'ok':False,'why':'shove free before using the stairs'}
    if op not in ('up','down'):return {'ok':False,'why':'choose upstairs or downstairs'}
    level=a.floor_level+(1 if op=='up' else -1)
    if not 0<=level<count(b):return {'ok':False,'why':'no floor in that direction'}
    a.floor_level=level;a.floor_building=b.id if level else None;a.floor_epoch+=1
    a.lat,a.lng=point;a.raw=(*point,1.);a.speed=0;a.sprinting=False;a.quiet=False;a.dirty=True
    # Release pursuers on the level left behind. They cannot bite through a ceiling.
    for z in current.zeds.values():
        if z.target==a.id:z.target=None;z.state='idle';z.goal=None
    destination=layer(r,a);destination._wall_clearance(a)
    return {'ok':True,'floor':level,'floor_epoch':a.floor_epoch,'message':'Ground floor' if not level else 'Floor '+str(level+1)}


def state(w):
    b=next(iter(w.buildings.items.values()),None)
    if b is None:return {}
    return {'outline':copy.deepcopy(b.outline),'type':b.type,'name':b.name,
            'inhabitants':[{k:copy.deepcopy(getattr(z,k)) for k in ('id','lat','lng','home','kind','variant','hp','hp_max')} for z in w.zeds.values() if z.alive],
            'openings':{o['id']:{k:copy.deepcopy(o[k]) for k in ('open','broken','damage','locked','alarm','alarm_triggered','barricaded','curtain','curtain_closed','glass_cleared')} for o in b.openings}}


def exit_plan(geometry,start):
    """Walk to the stairs, opening interior passages on the way; never exit an upper window."""
    from app.game.buildings import mix
    b=geometry.containing(start)
    if b is None:return {'ok':False,'why':'stairs unavailable'}
    goal=landing(b)
    closed=[o for o in b.openings if o['kind']=='door' and not o['open'] and not o['broken'] and not o['barricaded']]
    try:
        for o in closed:o['open']=True
        path=geometry.route(start,goal)
    finally:
        for o in closed:o['open']=False
    if not path:return {'ok':False,'why':'the stairs are blocked; clear the passage first'}
    route=[];anchor=start
    for target in path:
        if geometry.clear(anchor,target):route.append(target);anchor=target;continue
        distance=math.dist(b.xy(anchor),b.xy(target));last=anchor
        for i in range(1,max(2,math.ceil(distance/.2))+1):
            point=mix(anchor,target,min(1,i*.2/max(distance,.001)))
            if not geometry.clear(last,point):break
            last=point
        nearest=min(closed,key=lambda o:point_segment(b.xy(last),o['a'],o['b']),default=None)
        if nearest is None or point_segment(b.xy(last),nearest['a'],nearest['b'])>2.5:
            return {'ok':False,'why':'clear the passage to the stairs first'}
        route.append(list(last))
        return {'ok':True,'route':route,'opening':nearest['id'],'stairs':False}
    return {'ok':True,'route':route,'opening':None,'stairs':True}
