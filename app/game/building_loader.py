"""Background OSM geometry cache. Network work never runs in the simulation tick."""
from __future__ import annotations

import asyncio
import logging
import math
import time

import httpx
from sqlalchemy import select

from app.db import get_sessionmaker
from app.geo import _decode_bbox, cell_of
from app.models import BuildingRegion, BuildingOpening
from app.config import get_settings
from app.game.buildings import Buildings, osm_xml, overpass_json

log=logging.getLogger('osz.buildings')
MAX_BYTES=5_000_000
MAX_XML_BYTES=20_000_000    # the same area is several times larger as OSM XML
DAY=86400
RETRY_DELAYS=(2,)           # seconds to wait before asking a busy map server once more
FETCH_GAP_S=5               # politeness gap between network fetches (cached regions never wait)
GENERATED_TTL=3600          # look again for real outlines an hour after falling back
EMPTY_TTL=DAY               # the map server answered and has no buildings here: ask again tomorrow
NEIGHBOUR_M=250             # also map regions this close to a survivor
UNLOAD_KEEP_M=700           # outlines stay while anyone is this close: further than zombies are kept (420 m)
UNLOAD_AFTER_S=900          # and for this long after the last survivor left


def fallback_records(region):
    """Clearly fictional shelters so a map outage leaves something enterable nearby."""
    alphabet='0123456789bcdefghjkmnpqrstuvwxyz'
    out=[]
    import math
    for letter in alphabet:
        child=region+letter
        la0,la1,ln0,ln1=_decode_bbox(child)
        lat,lng=(la0+la1)/2,(ln0+ln1)/2
        mx=111320*max(.01,math.cos(math.radians(lat)))
        out.append({'id':'generated:'+child,'name':'Abandoned shelter','source':'generated','type':'cabin',
                    'outline':[[lat+y/111320,lng+x/mx] for x,y in ((-8,-6),(8,-6),(8,6),(-8,6))]})
    return out


def _box(record):
    outline=record.get('outline') or [[0,0]]
    lats=[p[0] for p in outline];lngs=[p[1] for p in outline]
    return min(lats),max(lats),min(lngs),max(lngs)


def in_use(world,records):
    """Ids of the buildings somebody has made a home of, boarded up, or is standing in."""
    homes=(getattr(world,'homes',None) or {}).values()
    claimed={h.get('building') for h in homes}|{d.get('building') for h in homes for d in h.get('defenses',{}).values()}
    people=[a for a in (getattr(world,'actors',None) or {}).values() if not a.dead]
    out=set()
    for r in records:
        la0,la1,ln0,ln1=_box(r)
        if r['id'] in claimed or any(la0<=a.lat<=la1 and ln0<=a.lng<=ln1 for a in people):out.add(r['id'])
    return out


def refreshed(old,new,world):
    """A region's new map, plus any building in use that the new map no longer has.

    Placeholder shelters go when the real outlines arrive, but never from under someone: a shelter
    that is a home, or has a survivor in it, stays, and a real building that would stand on it is
    left out until the next refresh finds the shelter empty.
    """
    ids={r['id'] for r in new}
    held=in_use(world,[r for r in old if r['id'] not in ids])
    keep=[r for r in old if r['id'] in held]
    if not keep:return new
    boxes=[_box(r) for r in keep]
    def apart(r):
        a=_box(r)
        return not any(a[0]<=b[1] and b[0]<=a[1] and a[2]<=b[3] and b[2]<=a[3] for b in boxes)
    return [r for r in new if apart(r)]+keep


async def fetch_records(region,client):
    la0,la1,ln0,ln1=_decode_bbox(region)
    query=f'[out:json][timeout:20];way["building"]({la0},{ln0},{la1},{ln1});out geom;'
    errors=[]
    # One small region per request, persistent caching and globally serial fetches.
    # A deployed operator can configure a private endpoint without altering clients.
    import os
    endpoint=os.environ.get('OSZ_OVERPASS_URL','https://overpass-api.de/api/interpreter')
    # The public endpoint answers 429/504 when it is busy; a short wait usually clears it,
    # and real outlines are worth far more to a new player than placeholder shelters.
    for delay in (0,)+tuple(RETRY_DELAYS):
        if delay:await asyncio.sleep(delay)
        try:
            r=await client.post(endpoint,data={'data':query})
            r.raise_for_status()
            if len(r.content)>MAX_BYTES:raise ValueError('map response too large')
            data=r.json()
            # A query that ran out of time or memory still answers 200, with a remark and nothing in it.
            if data.get('remark') and not data.get('elements'):raise ValueError('map query did not finish')
            return overpass_json(data),'osm'
        except (httpx.HTTPError,ValueError,KeyError) as e:
            errors.append(type(e).__name__)
            busy=isinstance(e,httpx.TimeoutException) or (isinstance(e,httpx.HTTPStatusError) and e.response.status_code in (429,502,503,504))
            if not busy:break
    # The editing API fallback is deliberately a single bounded read, cached for 30 days.
    try:
        r=await client.get('https://api.openstreetmap.org/api/0.6/map',params={'bbox':f'{ln0},{la0},{ln1},{la1}'})
        r.raise_for_status()
        if len(r.content)>MAX_XML_BYTES:raise ValueError('map response too large')
        return osm_xml(r.text),'osm'
    except Exception as e:
        errors.append(type(e).__name__)
    log.warning('geometry unavailable for region %s (%s); using generated shelters',region,','.join(errors))
    return fallback_records(region),'generated'


def wanted_regions(actors):
    """Regions to map, nearest first: where each survivor stands, then any region within reach.

    A survivor near a region edge would otherwise see streets with no buildings across it.
    """
    own,near=[],[]
    for a in actors:
        if a.dead or (a.lat==0 and a.lng==0):continue
        own.append(cell_of(a.lat,a.lng,6))
        dlat=NEIGHBOUR_M/111320;dlng=NEIGHBOUR_M/(111320*max(.01,math.cos(math.radians(a.lat))))
        for y in (-dlat,0,dlat):
            for x in (-dlng,0,dlng):
                if -90<=a.lat+y<=90:near.append(cell_of(a.lat+y,(a.lng+x+180)%360-180,6))
    return list(dict.fromkeys(own+near))


def start_regions():
    """The map regions every public start city needs on arrival: where it is, and 250 m around."""
    from app.game.starts import STARTS
    from types import SimpleNamespace
    spots=[SimpleNamespace(lat=st['lat'],lng=st['lng'],dead=False) for st in STARTS]
    return list(dict.fromkeys(r for spot in spots for r in wanted_regions([spot])))


class BuildingLoader:
    def __init__(self,world):
        self.world=world
        # Public servers keep the start cities' maps in memory from boot, and never forget them: in
        # Minneapolis a new survivor's arrival protection once ran out about 50 s before the walls came.
        # The running server sets this (hub.get_hub); a bare loader, as in tests, pins nothing.
        self.pinned=[]
        self.loaded=set()
        self.world.resource_regions=self.loaded
        self.task=None
        self.next_fetch=0.0
        self.members={}             # region -> ids of the buildings its map holds
        self.last_near={}           # region -> when a survivor was last within UNLOAD_KEEP_M
        self.expires={}             # region -> when its map should be asked for again

    def start(self):
        self.task=asyncio.create_task(self._loop())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:await self.task
            except asyncio.CancelledError:pass
        await self.flush()

    async def _loop(self):
        async with httpx.AsyncClient(timeout=25,headers={'User-Agent':f"OhShitZombies/0.1 (+{get_settings().base_url or 'https://osz-production.up.railway.app'})"}) as client:
            while True:
                try:
                    await self.flush()
                    for region in wanted_regions(list(self.world.actors.values())):
                        if region not in self.loaded and await self.load(region,client):self.loaded.add(region)
                    for region in self.pinned:            # cached ones cost nothing; a missing one waits its turn
                        if region not in self.loaded and await self.load(region,client):self.loaded.add(region)
                    await self.forget_far()
                    await self.refresh_due(client)
                except asyncio.CancelledError:raise
                except Exception:log.exception('building cache update failed')
                await asyncio.sleep(2)

    async def load(self,region,client,again=False):
        """Bring a region's map into the world. `again` asks the map server afresh for a loaded one."""
        now=time.time();gone=[]
        async with get_sessionmaker()() as s:
            row=await s.get(BuildingRegion,region)
            # Placeholder shelters are kept only briefly, so a map-server hiccup does not leave an
            # area without its real buildings for a day. (Rows written before this rule held a day.)
            stale=row is not None and (row.expires_at<now or (row.source=='generated' and row.expires_at-now>GENERATED_TTL))
            if row is None or stale or again:
                if now<self.next_fetch:
                    return False
                records,source=await fetch_records(region,client)
                self.next_fetch=time.time()+FETCH_GAP_S
                answered=source!='generated'
                # Empty mapped rural regions also retain a small fictional shelter loop.
                if not records:records,source=fallback_records(region),'empty'
                if row is None:
                    row=BuildingRegion(id=region)
                    s.add(row)
                elif not answered and row.records:
                    records,source=row.records,row.source       # the map server is still away: nothing known is thrown out
                else:
                    records=refreshed(row.records or [],records,self.world)
                    kept={r['id'] for r in records};gone=[r['id'] for r in row.records or [] if r['id'] not in kept]
                row.records=records;row.source=source
                row.expires_at=now+(GENERATED_TTL if not answered else 30*DAY if source=='osm' else EMPTY_TTL)
                await s.commit()
            self.expires[region]=row.expires_at
            self.members[region]={r['id'] for r in row.records}
            incoming=Buildings()
            incoming.add([r for r in row.records if r['id'] not in self.world.buildings.items])
            ids=[o['id'] for b in incoming.items.values() for o in b.openings]
            if ids:
                states=(await s.execute(select(BuildingOpening).where(BuildingOpening.id.in_(ids)))).scalars()
                for state in states:
                    _,o=incoming.opening(state.id)
                    if o:
                        o['open']=bool(state.state.get('open',False))
                        for k in ('curtain','curtain_closed','glass_cleared'):o[k]=bool(state.state.get(k,False))
                        o['broken']=bool(state.state.get('broken',False))
                        o['damage']=float(state.state.get('damage',0))
                        o['locked']=bool(state.state.get('locked',o['locked'])) and not o['open']
                        o['alarm_triggered']=bool(state.state.get('alarm_triggered',False))
        # Publish footprints and restored openings together, with no intervening await.
        if gone:        # what the refreshed map no longer has leaves in the same moment the new walls arrive
            elsewhere=set().union(*(self.members.get(r,()) for r in self.loaded if r!=region))
            gone=self.world.buildings.remove([i for i in gone if i not in elsewhere])
        self.world.buildings.items.update(incoming.items)
        self.world.buildings.revision+=len(incoming.items)+len(gone)
        if gone:
            self.world.buildings.dirty-={i for i in self.world.buildings.dirty if self.world.buildings.opening(i)[1] is None}
            if hasattr(self.world,'buildings_gone'):self.world.buildings_gone(gone,region)
            log.info('map of %s refreshed: %d buildings out, %d in',region,len(gone),len(incoming.items))
        # Doors that now face a building from an earlier region move to a wall facing open ground.
        self.world.buildings.face_open_air(list(incoming.items))
        if hasattr(self.world,"protect_unmapped_spawns"):
            self.world.protect_unmapped_spawns(region)
        return True

    @staticmethod
    def metres_to(region,lat,lng):
        """How far a point is from a region's box (0 inside it)."""
        la0,la1,ln0,ln1=_decode_bbox(region)
        dy=max(la0-lat,0,lat-la1)*111320
        dx=max(ln0-lng,0,lng-ln1)*111320*max(.01,math.cos(math.radians(lat)))
        return math.hypot(dx,dy)

    async def forget_far(self,now=None):
        """Drop the outlines of regions nobody has been near for a while.

        A long-running server otherwise keeps every town anyone ever walked through: memory, and a
        slower sweep each time Python tidies its heap. Door states are saved before the walls go,
        and the region's map is still in the database, so coming back needs no network.
        """
        now=time.time() if now is None else now
        world=self.world
        live=[a for a in world.actors.values() if not a.dead and not (a.lat==0 and a.lng==0)]
        gone=[]
        for region in list(self.loaded):
            if region in self.pinned:continue
            if any(self.metres_to(region,a.lat,a.lng)<=UNLOAD_KEEP_M for a in live):
                self.last_near[region]=now;continue
            if now-self.last_near.setdefault(region,now)<UNLOAD_AFTER_S:continue
            if any(cell_of(z.lat,z.lng,6)==region for z in world.zeds.values()):continue     # walls stay while anything walks there
            gone.append(region)
        if not gone:return []
        await self.flush()
        done=[]
        for region in gone:
            kept=set().union(*(self.members.get(r,()) for r in self.loaded if r!=region))
            ids=[i for i in self.members.get(region,()) if i not in kept and i in world.buildings.items]
            openings={o['id'] for i in ids for o in world.buildings.items[i].openings}
            if openings&world.buildings.dirty:continue      # a door state did not reach the database: try again later
            world.buildings.remove(ids)
            self.loaded.discard(region);self.members.pop(region,None);self.last_near.pop(region,None);self.expires.pop(region,None)
            done.append(region)
        if done:log.info('forgot %d quiet map regions; %d buildings stay loaded',len(done),len(world.buildings.items))
        return done

    async def refresh_due(self,client,now=None):
        """Ask again for one loaded region whose map has run out.

        That used to happen only when a region was loaded, so a street given placeholder shelters
        during a map-server hiccup kept them for as long as anyone stayed there.
        """
        now=time.time() if now is None else now
        if now<self.next_fetch:return None
        people=list((getattr(self.world,'actors',None) or {}).values())
        order=[r for r in wanted_regions(people) if r in self.loaded]        # where survivors stand comes first
        region=next((r for r in order+[r for r in self.loaded if r not in order] if self.expires.get(r,now)<now),None)
        if region is None:return None
        await self.load(region,client,again=True)
        return region

    async def flush(self):
        lock=getattr(self,'state_lock',None)
        if lock is not None:
            async with lock:await self._flush()
        else:await self._flush()

    async def _flush(self):
        geometry=self.world.buildings
        pending={}
        for oid in list(geometry.dirty):
            _,o=geometry.opening(oid)
            if o:
                from app.game.buildings import OPENING_STATE
                pending[oid]={k:o[k] for k in OPENING_STATE}
        if not pending:return
        async with get_sessionmaker()() as s:
            for oid,state in pending.items():
                row=await s.get(BuildingOpening,oid)
                if row is None:
                    row=BuildingOpening(id=oid);s.add(row)
                row.state=state
            await s.commit()
        for oid,state in pending.items():
            _,o=geometry.opening(oid)
            if o and all(o[k]==v for k,v in state.items()):geometry.dirty.discard(oid)
