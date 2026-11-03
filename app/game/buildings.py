"""Deterministic fictional interiors inside real OSM footprints.

All collision tests use local metres. Layouts describe a single playable ground floor;
they do not claim to represent actual rooms, entrances or public access.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import hashlib
import math
import xml.etree.ElementTree as ET

M = 111320.0
OPENING_STATE = ('open','broken','damage','locked','alarm_triggered','curtain','curtain_closed','glass_cleared')


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def mix(a, b, t):
    return a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t


def inside(p, poly):
    yes = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > p[1]) != (b[1] > p[1]):
            if p[0] < (b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0]:
                yes = not yes
    return yes


def point_segment(p, a, b):
    d = sub(b, a)
    n = d[0]*d[0]+d[1]*d[1]
    t = max(0, min(1, ((p[0]-a[0])*d[0]+(p[1]-a[1])*d[1])/n)) if n else 0
    q = mix(a, b, t)
    return math.dist(p, q)


def intersects(a, b, c, d):
    ab, cd = sub(b, a), sub(d, c)
    det = cross(ab, cd)
    if abs(det) < 1e-8:
        if abs(cross(sub(c, a), ab)) > 1e-7:
            return False
        return min(point_segment(c,a,b),point_segment(d,a,b),point_segment(a,c,d),point_segment(b,c,d)) < 1e-7
    t, u = cross(sub(c,a),cd)/det, cross(sub(c,a),ab)/det
    return -1e-7 <= t <= 1+1e-7 and -1e-7 <= u <= 1+1e-7


def segment_distance(a,b,c,d):
    return 0 if intersects(a,b,c,d) else min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))


def osm_xml(text):
    """Read closed building ways only. Incomplete/multipolygon footprints are skipped."""
    root = ET.fromstring(text)
    nodes = {n.attrib['id']: [float(n.attrib['lat']),float(n.attrib['lon'])] for n in root.findall('node')}
    out = []
    # A courtyard or multipart relation needs polygon holes; never turn it into solid rooms.
    complex_members = {m.attrib.get('ref') for r in root.findall('relation')
                       if any(t.attrib.get('k')=='building' for t in r.findall('tag'))
                       for m in r.findall('member') if m.attrib.get('type')=='way'}
    for w in root.findall('way'):
        tags = {t.attrib['k']: t.attrib['v'] for t in w.findall('tag')}
        refs = [n.attrib['ref'] for n in w.findall('nd')]
        if tags.get('building','no')=='no' or w.attrib['id'] in complex_members:
            continue
        if len(refs)<4 or refs[0]!=refs[-1] or any(n not in nodes for n in refs):
            continue
        out.append({'id':'osm:w:'+w.attrib['id'],'outline':[nodes[n] for n in refs[:-1]],
                    'name':tags.get('name') or tags.get('building','Building').replace('_',' ').title(),
                    'source':'osm','type':tags.get('building','yes')})
    return out


def overpass_json(data):
    out=[]
    complex_members={m.get('ref') for r in data.get('elements',[]) if r.get('type')=='relation'
                     for m in r.get('members',[]) if m.get('type')=='way'}
    for w in data.get('elements',[]):
        g=w.get('geometry',[]);tags=w.get('tags',{})
        if w.get('type')!='way' or w.get('id') in complex_members or tags.get('building','no')=='no':
            continue
        if len(g)<4 or g[0]!=g[-1] or any('lat' not in p or 'lon' not in p for p in g):
            continue
        out.append({'id':'osm:w:'+str(w['id']),'outline':[[p['lat'],p['lon']] for p in g[:-1]],
                    'name':tags.get('name') or tags.get('building','Building').replace('_',' ').title(),
                    'source':'osm','type':tags.get('building','yes')})
    return out


@dataclass
class Building:
    id: str
    outline: list
    name: str = 'Building'
    source: str = 'osm'
    type: str = 'yes'
    walls: list = field(default_factory=list)
    openings: list = field(default_factory=list)
    rooms: list = field(default_factory=list)

    def __post_init__(self):
        self.origin = self.outline[0]
        self.mx = M*max(.01,math.cos(math.radians(self.origin[0])))
        self.poly = [self.xy(p) for p in self.outline]
        self.bounds = (min(p[0] for p in self.poly),min(p[1] for p in self.poly),max(p[0] for p in self.poly),max(p[1] for p in self.poly))
        if not self.walls:
            self._layout()

    def xy(self,p):
        return (p[1]-self.origin[1])*self.mx, (p[0]-self.origin[0])*M

    def ll(self,p):
        return [self.origin[0]+p[1]/M,self.origin[1]+p[0]/self.mx]

    def _opening(self,a,b,kind,label):
        length=math.dist(a,b)
        if length<3:
            self.walls.append([a,b]);return
        gap=min(2.4,length*.45)
        lo,hi=mix(a,b,.5-gap/length/2),mix(a,b,.5+gap/length/2)
        self.walls.extend([[a,lo],[hi,b]])
        self.openings.append({'id':self.id+':'+str(len(self.openings)), 'kind':kind,
                              'label':label,'a':lo,'b':hi,'open':False,'broken':False,'damage':0.0,'locked':False,'alarm':False,'alarm_triggered':False,'barricaded':False,'curtain':False,'curtain_closed':False,'glass_cleared':False})

    def default_edges(self):
        """Wall numbers for the entrance and the window: the longest wall and the one opposite."""
        edges=list(zip(self.poly,self.poly[1:]+self.poly[:1]))
        longest=max(range(len(edges)),key=lambda i:math.dist(*edges[i]))
        return longest,(longest+len(edges)//2)%len(edges)

    def relayout(self,entrance,window):
        """Move the outside door and window to other walls. Each keeps its id and its state."""
        old={o['label']:o for o in self.openings};rooms=self.rooms
        self.walls=[];self.openings=[];self.rooms=[]
        self._layout(entrance,window,rooms)        # the rooms and what is in them stay where they were
        used={o['id'] for o in old.values()};n=0
        for o in self.openings:
            was=old.get(o['label'])
            if was:
                o.update({k:was[k] for k in ('id','alarm','barricaded',*OPENING_STATE)})
            else:
                while self.id+':'+str(n) in used:n+=1
                o['id']=self.id+':'+str(n);used.add(o['id'])

    def _layout(self,entrance=None,window=None,rooms=None):
        edges=list(zip(self.poly,self.poly[1:]+self.poly[:1]))
        longest,opposite=self.default_edges()
        if entrance is None:entrance=longest
        if window is None:window=opposite
        self.entrance_edge,self.window_edge=entrance,window
        for i,(a,b) in enumerate(edges):
            if i==entrance:
                self._opening(a,b,'door','Entrance')
            elif i==window:
                self._opening(a,b,'window','Window')
            else:self.walls.append([a,b])
        # General outlines use a conservative split only where the polygon has one span.
        a,b=edges[longest];d=math.dist(a,b)
        self.u=((b[0]-a[0])/d,(b[1]-a[1])/d)
        self.v=(-self.u[1],self.u[0])
        projected=[(p[0]*self.u[0]+p[1]*self.u[1],p[0]*self.v[0]+p[1]*self.v[1]) for p in self.poly]
        ulo,uhi=min(p[0] for p in projected),max(p[0] for p in projected)
        umid=ulo+(uhi-ulo)*.38  # avoid a T junction across the entrance/window midpoints
        spans=[]
        for p,q in zip(projected,projected[1:]+projected[:1]):
            if (p[0]>umid)!=(q[0]>umid):
                spans.append(p[1]+(q[1]-p[1])*(umid-p[0])/(q[0]-p[0]))
        split=len(spans)==2 and d>=12 and abs(spans[1]-spans[0])>=7
        self.split=umid if split else None
        if split:
            ends=[(umid*self.u[0]+y*self.v[0],umid*self.u[1]+y*self.v[1]) for y in sorted(spans)]
            self._opening(*ends,'door','Room door')
        if rooms is not None:
            self.rooms=rooms;self._extra_windows();return
        # Choose actual interior sample points, at least 1.5m clear of all walls.
        x0,y0,x1,y1=self.bounds
        candidates=[]
        for ix in range(1,min(30,max(2,int((x1-x0)/2)))):
            for iy in range(1,min(30,max(2,int((y1-y0)/2)))):
                p=(x0+(x1-x0)*ix/min(30,max(2,int((x1-x0)/2))),y0+(y1-y0)*iy/min(30,max(2,int((y1-y0)/2))))
                clearance=max(.35,min(1.6,min(x1-x0,y1-y0)*.2))
                if inside(p,self.poly) and all(point_segment(p,*w)>clearance for w in self.walls):
                    candidates.append(p)
        residential=self.type in ('house','residential','apartments','cabin','detached')
        # Fictional room themes vary by footprint, without changing collision,
        # room IDs, samples or saved entrance geometry.
        home_pair=[['Kitchen','Bedroom'],['Kitchen','Bathroom'],['Bathroom','Bedroom']]
        theme=int.from_bytes(hashlib.sha256(self.id.encode()).digest()[:2],'big')%3
        names=home_pair[theme] if residential else ['Lobby','Storage']
        if self.type in ('garage','garages','shed'):names=['Garage','Garage']
        if self.type in ('retail','supermarket'):names=['Shop floor','Stockroom']
        if self.type in ('hospital','clinic'):names=['Reception','Treatment room']
        for side,label in enumerate(names if split else ['Interior']):
            choices=[p for p in candidates if not split or int(p[0]*self.u[0]+p[1]*self.u[1]>umid)==side]
            if choices:
                c=(sum(p[0] for p in choices)/len(choices),sum(p[1] for p in choices)/len(choices))
                p=min(choices,key=lambda p:math.dist(p,c))
                self.rooms.append({'id':self.id+':r'+str(side),'name':label,'pos':p})
        self._extra_windows()

    def _extra_windows(self):
        """More panes on the existing outward-facing window wall; legacy IDs stay intact.

        Add after room placement so old cupboards and room door IDs do not move.
        Using this wall also preserves the terrace's choice of a street/yard face.
        """
        pane=next((o for o in self.openings if o['label']=='Window'),None)
        if pane is None:return
        edge=(self.poly[self.window_edge],self.poly[(self.window_edge+1)%len(self.poly)])
        sections=[w for w in self.walls if math.dist(*w)>=5
                  and all(point_segment(p,*edge)<1e-6 for p in w)]
        for n,w in enumerate(sections[:2],2):
            self.walls.remove(w)
            self._opening(*w,'window','Window '+str(n))

    def barriers(self,vision=False):
        yield from self.walls
        for o in self.openings:
            # Boards hold whatever is behind them, a smashed frame included.
            if o.get('barricaded') or vision and o.get('curtain_closed') or not (o['open'] or o['broken'] or vision and o['kind']=='window'):
                yield o['a'],o['b']

    def blocks(self,a,b,radius=.28,vision=False):
        p,q=self.xy(a),self.xy(b)
        x0,y0,x1,y1=self.bounds
        if max(p[0],q[0])<x0-radius or min(p[0],q[0])>x1+radius or max(p[1],q[1])<y0-radius or min(p[1],q[1])>y1+radius:
            return False
        return any(segment_distance(p,q,*w)<=radius for w in self.barriers(vision))

    def contains(self,p):
        return inside(self.xy(p),self.poly)

    def room_at(self,p):
        if not self.contains(p):return None
        xy=self.xy(p)
        side=int(self.split is not None and xy[0]*self.u[0]+xy[1]*self.u[1]>self.split)
        return self.rooms[min(side,len(self.rooms)-1)]['name'] if self.rooms else 'Interior'

    def snapshot(self):
        # OpenStreetMap's commonest tag is building=yes: that is not a name to show a player
        from app.game import floors
        return {'floor':getattr(self,'floor_level',0),'floors':floors.count(self),'stairs':floors.landing(self) if floors.count(self)>1 else None,'id':self.id,'name':'Building' if self.name in ('Yes','') else self.name,'source':self.source,'outline':self.outline,
                'walls':[[self.ll(a),self.ll(b)] for a,b in self.walls],
                'openings':[{**{k:o[k] for k in ('id','kind','label','open','broken','locked','barricaded','curtain','curtain_closed','glass_cleared')},'a':self.ll(o['a']),'b':self.ll(o['b'])} for o in self.openings],
                'rooms':[{'id':r['id'],'name':r['name'],'pos':self.ll(r['pos'])} for r in self.rooms]}


MAX_SPAN_CELLS=150          # about 3km: nothing in the game sees, walks or routes further in one leg


class _Table(dict):
    """Buildings by id. It counts its own changes, so the search grid knows when it is out of date."""
    version=0
    def __setitem__(self,k,v):super().__setitem__(k,v);self.version+=1
    def __delitem__(self,k):super().__delitem__(k);self.version+=1
    def update(self,*a,**k):super().update(*a,**k);self.version+=1
    def pop(self,*a):self.version+=1;return super().pop(*a)
    def popitem(self):self.version+=1;return super().popitem()
    def clear(self):super().clear();self.version+=1
    def setdefault(self,k,d=None):
        if k not in self:self.version+=1
        return super().setdefault(k,d)


class Buildings:
    def __init__(self):
        self._items=_Table()
        self.revision=0
        self.layouts=0              # counts doors and windows moved to another wall
        self.obstacles=[]
        self.dirty=set()

    @property
    def items(self):return self._items

    @items.setter
    def items(self,value):
        table=_Table(value);table.version=self._items.version+1;self._items=table

    def stamp(self):
        """Changes when a building arrives, leaves or is laid out again. Not when a door opens."""
        return (id(self._items),self._items.version,self.layouts)

    def _sync(self):
        # The grid, the door lookup and the arrival order depend only on which buildings are
        # loaded and how they are laid out. They used to be rebuilt after every opened door.
        key=self.stamp()
        if getattr(self,'_index_key',None)==key:return
        grid={};openings={};order={}
        for n,building in enumerate(self._items.values()):
            order[building.id]=n
            lat=[p[0] for p in building.outline];lng=[p[1] for p in building.outline]
            for y in range(math.floor(min(lat)*5000),math.floor(max(lat)*5000)+1):
                for x in range(math.floor(min(lng)*5000),math.floor(max(lng)*5000)+1):
                    grid.setdefault((y,x),[]).append(building)
            for o in building.openings:openings[o['id']]=(building,o)
        self._spatial=grid;self._openings=openings;self._order=order;self._missing=set();self._index_key=key

    def remove(self,ids):
        """Forget these buildings (their door states are saved by the loader first)."""
        gone=[i for i in ids if i in self._items]
        for i in gone:self._items.pop(i)
        return gone

    def add(self,records):
        added=[]
        for r in records:
            if r['id'] in self.items:continue
            poly=r.get('outline',[])
            if len(poly)<3 or len(poly)>150 or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in poly):continue
            clean=[]
            for p in poly:
                if not clean or p!=clean[-1]:clean.append(p)
            if len(clean)>1 and clean[0]==clean[-1]:clean.pop()
            if len(clean)<3:continue
            args={k:r[k] for k in ('id','name','source','type') if k in r}
            args['outline']=clean
            b=Building(**args)
            area=abs(sum(cross(a,c) for a,c in zip(b.poly,b.poly[1:]+b.poly[:1])))/2
            if area<10 or area>12000:continue
            if b.source=='osm':
                from app.rng import seeded
                rng=seeded('security:'+b.id)
                entrance=next((o for o in b.openings if o['label']=='Entrance'),None)
                if entrance:entrance.update(locked=rng.random()<.12,alarm=rng.random()<.10)
            self.items[b.id]=b
            self.revision+=1
            added.append(b.id)
        self.face_open_air(added)

    def open_air(self,b,i):
        """Can someone step out through the middle of this wall? Not when the next building is against it."""
        p,q=b.poly[i],b.poly[(i+1)%len(b.poly)];n=math.dist(p,q)
        if n<3:return False
        c=mix(p,q,.5);nx,ny=-(q[1]-p[1])/n,(q[0]-p[0])/n
        if inside((c[0]+nx*.6,c[1]+ny*.6),b.poly):nx,ny=-nx,-ny
        at=lambda t:b.ll((c[0]+nx*t,c[1]+ny*t))
        if any(self.containing(at(t)) is not None for t in (.6,1.5,2.5)):return False
        return not any(x.blocks(at(.6),at(2.5)) for x in self.candidates(at(.6),at(2.5),1))

    def face_open_air(self,ids):
        """Give these buildings, and the ones beside them, a door and a window onto walkable ground.

        The default layout puts the entrance on the longest wall. In a terrace or a city block that
        wall is often shared with the next building, which left nobody able to get in or out. The
        result depends only on which buildings stand there, not on the order the map arrived in.
        """
        todo={};moved=0
        for i in ids:
            b=self.items.get(i)
            if b is None:continue
            lat=[p[0] for p in b.outline];lng=[p[1] for p in b.outline]
            for x in self.candidates((min(lat),min(lng)),(max(lat),max(lng)),4):todo[x.id]=x
        for b in todo.values():
            if getattr(b,'entrance_edge',None) is None:continue      # walls supplied by hand
            entrance,window=want=b.default_edges()
            length=lambda i:math.dist(b.poly[i],b.poly[(i+1)%len(b.poly)])
            middle=lambda i:mix(b.poly[i],b.poly[(i+1)%len(b.poly)],.5)
            bad_door=not self.open_air(b,entrance)
            bad_window=length(window)>=3 and not self.open_air(b,window)
            if bad_door or bad_window:
                free=sorted((i for i in range(len(b.poly)) if self.open_air(b,i)),key=lambda i:(-length(i),i))
                if free:
                    door=free[0] if bad_door else entrance
                    rest=[i for i in free if i!=door]
                    if window!=door and not bad_window:pane=window
                    elif rest:pane=max(rest,key=lambda i:(math.dist(middle(i),middle(door)),-i))
                    else:pane=window if window!=door else entrance
                    want=(door,pane)
            if want!=(b.entrance_edge,b.window_edge):
                b.relayout(*want);moved+=1
        self.revision+=moved
        if moved:self.layouts+=1    # the door lookup holds the old openings

    def candidates(self,a,b=None,radius=0,line=False):
        # Degree-grid broad phase: small movement/A* legs inspect nearby outlines.
        # Keep the exact existing polygon/segment rules as the final authority.
        self._sync()
        b=b or a
        dy=radius/111320;dx=radius/(111320*max(.01,math.cos(math.radians(a[0]))))
        # The grid walk below is one step per 22m in each axis. Two points in different towns
        # would be billions of steps and freeze the server, so far-apart pairs get no candidates
        # here and clear() answers "blocked" for them.
        if abs(a[0]-b[0])*5000>MAX_SPAN_CELLS or abs(a[1]-b[1])*5000>MAX_SPAN_CELLS:return ()
        found={};grid=self._spatial
        ya,xa,yb,xb=a[0]*5000,a[1]*5000,b[0]*5000,b[1]*5000;py,px=dy*5000+1e-7,dx*5000+1e-7
        y0,y1=math.floor(min(ya,yb)-py),math.floor(max(ya,yb)+py)
        if line and y1-y0>1 and abs(xa-xb)>1:
            # A sight line or a step is thin: take only the cells it passes through (thickened by
            # the radius), not the whole rectangle between its ends. A 180 m look across a town
            # used to test every building in a 180 m square.
            for y in range(y0,y1+1):
                t0=min(1.0,max(0.0,(y-py-ya)/(yb-ya)));t1=min(1.0,max(0.0,(y+1+py-ya)/(yb-ya)))
                lo,hi=xa+t0*(xb-xa),xa+t1*(xb-xa)
                for x in range(math.floor(min(lo,hi)-px),math.floor(max(lo,hi)+px)+1):
                    for building in grid.get((y,x),()):found[building.id]=building
            return found.values()
        for y in range(y0,y1+1):
            for x in range(math.floor(min(xa,xb)-px),math.floor(max(xa,xb)+px)+1):
                for building in grid.get((y,x),()):found[building.id]=building
        return found.values()

    def near(self,p,radius):
        """Buildings with any part within `radius` metres, in the order they were loaded."""
        out=[]
        for b in self.candidates(p,p,radius):
            x,y=b.xy(p);x0,y0,x1,y1=b.bounds
            if math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1))<=radius:out.append(b)
        out.sort(key=lambda b:self._order[b.id])
        return out

    def first_blocking(self,a,b):
        """The earliest-loaded building in the way of a step, as a walk over every building found it."""
        hit=[x for x in self.candidates(a,b,.28,line=True) if x.blocks(a,b)]
        return min(hit,key=lambda x:self._order[x.id]) if hit else None

    def local_copy(self,a,b=None,radius=150):
        """A private copy of just the outlines around a route, for planning off the game loop.

        Copying every loaded building for each tap grew with every town anyone had visited.
        """
        import copy
        g=Buildings()
        g.items={x.id:copy.deepcopy(x) for x in self.candidates(a,b,radius)}
        g.obstacles=copy.deepcopy(self.obstacles)
        g.revision=self.revision
        return g

    def clear(self,a,b,radius=.28,vision=False,ignore=None):
        """Nothing solid between two points. `ignore` names one built barrier to leave out: its own reach test."""
        if abs(a[0]-b[0])*5000>MAX_SPAN_CELLS or abs(a[1]-b[1])*5000>MAX_SPAN_CELLS:return False
        mx=111320*max(.01,math.cos(math.radians(a[0])))
        xy=lambda p:((p[1]-a[1])*mx,(p[0]-a[0])*111320)
        if any(o.get("id")!=ignore and segment_distance((0,0),xy(b),xy(o["a"]),xy(o["b"]))<=max(radius,.02) for o in self.obstacles):return False
        return not any(x.blocks(a,b,radius,vision) for x in self.candidates(a,b,radius,line=True))

    def containing(self,p):
        return next((b for b in self.candidates(p) if b.contains(p)),None)

    def opening(self,oid):
        self._sync()
        hit=self._openings.get(oid)
        if hit is not None and self._items.get(hit[0].id) is hit[0] and any(o is hit[1] for o in hit[0].openings):return hit
        if oid in self._missing:return None,None
        for b in self._items.values():          # a layout altered by hand since the lookup was built
            for o in b.openings:
                if o['id']==oid:
                    self._openings[oid]=(b,o);return b,o
        self._missing.add(oid)                  # asked for every tick by homes in towns nobody is in
        return None,None

    def move(self,a,b):
        if self.clear(a,b):return b
        # A wall blocks the step; slide on one axis only if it is clear.
        for q in ([a[0],b[1]],[b[0],a[1]]):
            if self.clear(a,q):return q
        return a


    def exit_plan(self,start,blocked=()):
        """Plan one safe walking leg, stopping to open the next closed door."""
        b=self.containing(start)
        if b is None:return {'ok':False,'why':'already outside'}
        openings=sorted([o for o in b.openings if o["id"] not in blocked],key=lambda o:o["label"]!="Entrance")
        closed=[o for o in b.openings if o["id"] not in blocked and not o["open"] and not o["broken"]]
        path=[]
        try:
            for o in closed:o["open"]=True
            for opening in openings:
                center=mix(opening["a"],opening["b"],.5)
                edge=sub(opening["b"],opening["a"]);n=math.hypot(*edge)
                candidates=[b.ll((center[0]-edge[1]/n*t,center[1]+edge[0]/n*t)) for t in (-4,4,-2,2,-8,8)]
                for goal in candidates:
                    if b.contains(goal) or not self.clear(goal,goal):continue
                    path=self.route(start,goal)
                    if path:break
                if path:break
        finally:
            for o in closed:o["open"]=False
        if not path:return {"ok":False,"why":"no walkable exit for this outline"}
        route=[];anchor=start
        for target in path:
            if self.clear(anchor,target):
                route.append(target);anchor=target;continue
            # Find the last safe point along this leg before a closed passage.
            distance=math.dist(b.xy(anchor),b.xy(target))
            last=anchor
            for i in range(1,max(2,math.ceil(distance/.2))+1):
                point=mix(anchor,target,min(1,i*.2/max(distance,.001)))
                if not self.clear(last,point):break
                last=point
            nearest=min(closed,key=lambda o:point_segment(b.xy(last),o['a'],o['b']),default=None)
            if nearest is None or point_segment(b.xy(last),nearest['a'],nearest['b'])>2.5:
                return {'ok':False,'why':'exit path is obstructed'}
            route.append(list(last))
            return {'ok':True,'route':route,'opening':nearest['id']}
        return {'ok':True,'route':route,'opening':None}

    def beside_barrier(self,start,goal,off=1.1):
        """Where to stand for a destination that lies on a built fence or gate: near side first."""
        mx=M*max(.01,math.cos(math.radians(goal[0])))
        xy=lambda p:((p[1]-goal[1])*mx,(p[0]-goal[0])*M)
        for o in self.obstacles:
            a,b=xy(o['a']),xy(o['b'])
            if point_segment((0,0),a,b)>.6:continue
            n=math.dist(a,b) or 1;nx,ny=-(b[1]-a[1])/n*off,(b[0]-a[0])/n*off
            sides=sorted(((nx,ny),(-nx,-ny)),key=lambda p:math.dist(p,xy(start)))
            return [(goal[0]+y/M,goal[1]+x/mx) for x,y in sides]
        return [goal]

    def route(self,start,goal,limit=None):
        """A walkable path to the goal, or to a spot beside it when the goal is itself a barrier."""
        for spot in self.beside_barrier(start,goal):
            path=self._route(start,spot,limit)
            if path:return path
        return []

    def _route(self,start,goal,limit=None):
        """Bounded metre-grid A*. Routes only through currently open passages."""
        lat,lng=start;mx=M*max(.01,math.cos(math.radians(lat)))
        span=math.hypot((goal[1]-lng)*mx,(goal[0]-lat)*M)
        if span>1200:return []
        # A walk home across several blocks needs a larger search than a tap on the screen. Long
        # legs lean on the straight-line estimate, which finds a slightly longer path far sooner.
        if limit is None:limit=18000 if span<120 else 90000
        greed=1.0 if span<120 else 1.5
        if self.clear(start,goal):return [goal]
        def ll(p):return [lat+p[1]/M,lng+p[0]/mx]
        target=(round((goal[1]-lng)*mx),round((goal[0]-lat)*M))
        if math.hypot(*target)>1200:return []
        # Project walls once for this search; grid edges share a tiny spatial index.
        walls={}
        segments=[]
        for building in self.candidates(start,goal,70):
            segments.extend((building.ll(a),building.ll(b)) for a,b in building.barriers())
        segments.extend((o['a'],o['b']) for o in self.obstacles)
        for a,b in segments:
            a=((a[1]-lng)*mx,(a[0]-lat)*M);b=((b[1]-lng)*mx,(b[0]-lat)*M)
            for y in range(math.floor((min(a[1],b[1])-.28)/4),math.floor((max(a[1],b[1])+.28)/4)+1):
                for x in range(math.floor((min(a[0],b[0])-.28)/4),math.floor((max(a[0],b[0])+.28)/4)+1):
                    walls.setdefault((x,y),[]).append((a,b))
        edges={}
        def grid_clear(p,q):
            key=(p,q) if p<q else (q,p)
            if key not in edges:
                nearby=set()
                for y in range(math.floor(min(p[1],q[1])/4),math.floor(max(p[1],q[1])/4)+1):
                    for x in range(math.floor(min(p[0],q[0])/4),math.floor(max(p[0],q[0])/4)+1):
                        nearby.update(walls.get((x,y),()))
                edges[key]=not any(segment_distance(p,q,a,b)<=.28 for a,b in nearby)
            return edges[key]
        origin=(0,0);queue=[(math.hypot(*target),0,origin)];cost={origin:0};prev={}
        visited=set();end=None
        while queue and len(visited)<limit:
            _,g,p=heapq.heappop(queue)
            if p in visited:continue
            visited.add(p)
            if math.dist(p,target)<1.6 and self.clear(ll(p),goal):end=p;break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                q=(p[0]+dx,p[1]+dy);ng=g+math.hypot(dx,dy)
                if abs(q[0])>max(abs(target[0])+45,65) or abs(q[1])>max(abs(target[1])+45,65):continue
                if ng>=cost.get(q,math.inf) or not grid_clear(p,q):continue
                cost[q]=ng;prev[q]=p;heapq.heappush(queue,(ng+greed*math.dist(q,target),ng,q))
        if end is None:return []
        path=[goal]
        while end!=origin:path.append(ll(end));end=prev[end]
        path.reverse()
        simple=[];anchor=start;i=0
        while i<len(path):
            j=i
            while j+1<len(path) and self.clear(anchor,path[j+1]):j+=1
            simple.append(path[j]);anchor=path[j];i=j+1
        return simple
