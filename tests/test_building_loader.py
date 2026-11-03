import httpx
import pytest

from app.game.building_loader import fallback_records, fetch_records
from app.game.buildings import Buildings


def test_generated_fallback_is_stable_and_explicitly_labelled():
    records=fallback_records('9zvxvs')
    assert records==fallback_records('9zvxvs')
    assert len(records)==32
    assert all(r['source']=='generated' for r in records)
    geometry=Buildings();geometry.add(records)
    assert len(geometry.items)==32
    assert all(b.rooms and any(o['kind']=='door' for o in b.openings) for b in geometry.items.values())


@pytest.mark.asyncio
async def test_remote_geometry_failure_keeps_playable_fallback():
    async def respond(request):return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        records,source=await fetch_records('9zvxvs',client)
    assert source=='generated' and len(records)==32


@pytest.mark.asyncio
async def test_successful_overpass_outline_is_real_and_closed():
    data={'elements':[{'type':'way','id':42,'tags':{'building':'house'},'geometry':[
        {'lat':44.9,'lon':-93.2},{'lat':44.9,'lon':-93.1998},
        {'lat':44.9001,'lon':-93.1998},{'lat':44.9001,'lon':-93.2},{'lat':44.9,'lon':-93.2}]}]}
    async def respond(request):return httpx.Response(200,json=data)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        records,source=await fetch_records('9zvxvs',client)
    assert source=='osm' and records[0]['id']=='osm:w:42'
    geometry=Buildings();geometry.add(records)
    assert len(geometry.items)==1


@pytest.mark.asyncio
async def test_geometry_and_openings_survive_new_loader_without_network(maker):
    from types import SimpleNamespace
    from app.game.building_loader import BuildingLoader
    world=SimpleNamespace(buildings=Buildings())
    loader=BuildingLoader(world)
    async def offline(request):return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        assert await loader.load('9zvxvs',client)
    b=next(iter(world.buildings.items.values()));o=b.openings[0]
    o['open']=True;world.buildings.dirty.add(o['id'])
    await loader.flush()
    assert not world.buildings.dirty
    restored=SimpleNamespace(buildings=Buildings())
    async def unexpected(request):raise AssertionError('cached geometry should not fetch')
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as client:
        assert await BuildingLoader(restored).load('9zvxvs',client)
    assert restored.buildings.opening(o['id'])[1]['open']
    assert len(restored.buildings.items)==len(world.buildings.items)
    # Reloading a cache must not revert newer, unsaved changes in the active world.
    o['open']=False;world.buildings.dirty.add(o['id'])
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as client:
        assert await loader.load('9zvxvs',client)
    assert not o['open']


@pytest.mark.asyncio
async def test_geometry_is_published_only_after_opening_restore(maker,monkeypatch):
    from types import SimpleNamespace
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.game.building_loader import BuildingLoader
    original_world=SimpleNamespace(buildings=Buildings())
    async def offline(request):return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        await BuildingLoader(original_world).load('9zvxvs',client)
    restored=SimpleNamespace(buildings=Buildings())
    execute=AsyncSession.execute
    observed=[]
    async def observe(session,statement,*args,**kw):
        if 'building_opening' in str(statement):
            observed.append(True)
            assert not restored.buildings.items,'partially restored geometry must not be visible'
        return await execute(session,statement,*args,**kw)
    monkeypatch.setattr(AsyncSession,'execute',observe)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        await BuildingLoader(restored).load('9zvxvs',client)
    assert observed and len(restored.buildings.items)==32


@pytest.mark.asyncio
async def test_busy_map_server_is_asked_again_before_falling_back():
    data={'elements':[{'type':'way','id':7,'tags':{'building':'yes'},'geometry':[
        {'lat':44.9,'lon':-93.2},{'lat':44.9,'lon':-93.1998},
        {'lat':44.9001,'lon':-93.1998},{'lat':44.9001,'lon':-93.2},{'lat':44.9,'lon':-93.2}]}]}
    calls=[]
    async def respond(request):
        calls.append(request.url.host)
        return httpx.Response(504) if len(calls)==1 else httpx.Response(200,json=data)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        records,source=await fetch_records('9zvxvs',client)
    assert source=='osm' and records[0]['id']=='osm:w:7'
    assert calls==['overpass-api.de','overpass-api.de']


@pytest.mark.asyncio
async def test_dense_area_xml_fallback_is_accepted_above_the_json_limit():
    from app.game import building_loader
    way=('<node id="1" lat="44.9" lon="-93.2"/><node id="2" lat="44.9" lon="-93.1998"/>'
         '<node id="3" lat="44.9001" lon="-93.1998"/><node id="4" lat="44.9001" lon="-93.2"/>'
         '<way id="9"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="building" v="yes"/></way>')
    xml='<osm>'+way+'<!--'+'x'*(building_loader.MAX_BYTES+1000)+'--></osm>'
    async def respond(request):
        return httpx.Response(400) if request.method=='POST' else httpx.Response(200,text=xml)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        records,source=await fetch_records('9zvxvs',client)
    assert source=='osm' and [r['id'] for r in records]==['osm:w:9']


def test_regions_near_a_survivor_are_mapped_after_their_own():
    from types import SimpleNamespace
    from app.game.building_loader import wanted_regions, NEIGHBOUR_M
    from app.geo import _decode_bbox, cell_of
    la0,la1,ln0,ln1=_decode_bbox('9zvxvs')
    middle=SimpleNamespace(lat=(la0+la1)/2,lng=(ln0+ln1)/2,dead=False)
    assert wanted_regions([middle])==['9zvxvs']
    edge=SimpleNamespace(lat=(la0+la1)/2,lng=ln1-.0001,dead=False)
    regions=wanted_regions([edge])
    assert regions[0]=='9zvxvs' and cell_of(edge.lat,ln1+.0001,6) in regions and len(regions)==2
    assert wanted_regions([SimpleNamespace(lat=0,lng=0,dead=False),SimpleNamespace(lat=1,lng=1,dead=True)])==[]
    assert NEIGHBOUR_M<300


@pytest.mark.asyncio
async def test_placeholder_shelters_are_replaced_by_real_outlines_on_a_later_load(maker):
    import time
    from types import SimpleNamespace
    from app.db import get_sessionmaker
    from app.models import BuildingRegion
    from app.game import building_loader
    from app.game.building_loader import BuildingLoader
    async with get_sessionmaker()() as s:       # a row from before the one-hour rule: held for a day
        s.add(BuildingRegion(id='9zvxvs',source='generated',records=fallback_records('9zvxvs'),
                             expires_at=time.time()+building_loader.DAY-600));await s.commit()
    data={'elements':[{'type':'way','id':42,'tags':{'building':'house'},'geometry':[
        {'lat':44.9,'lon':-93.2},{'lat':44.9,'lon':-93.1998},
        {'lat':44.9001,'lon':-93.1998},{'lat':44.9001,'lon':-93.2},{'lat':44.9,'lon':-93.2}]}]}
    async def respond(request):return httpx.Response(200,json=data)
    world=SimpleNamespace(buildings=Buildings())
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await BuildingLoader(world).load('9zvxvs',client)
    assert list(world.buildings.items)==['osm:w:42']
    async with get_sessionmaker()() as s:
        row=await s.get(BuildingRegion,'9zvxvs')
        assert row.source=='osm' and row.expires_at>time.time()+building_loader.DAY


@pytest.mark.asyncio
async def test_quiet_regions_are_forgotten_with_their_doors_saved_and_come_back_without_network(maker):
    from types import SimpleNamespace
    from app.geo import _decode_bbox
    from app.game.building_loader import BuildingLoader, UNLOAD_AFTER_S, UNLOAD_KEEP_M
    la0,la1,ln0,ln1=_decode_bbox('9zvxvs');inside=((la0+la1)/2,(ln0+ln1)/2)
    walker=SimpleNamespace(lat=inside[0],lng=inside[1],dead=False)
    world=SimpleNamespace(buildings=Buildings(),actors={1:walker},zeds={})
    loader=BuildingLoader(world)
    async def offline(request):return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        assert await loader.load('9zvxvs',client)
    loader.loaded.add('9zvxvs');count=len(world.buildings.items);assert count
    b=next(iter(world.buildings.items.values()));o=b.openings[0];o['open']=True;world.buildings.dirty.add(o['id'])
    assert await loader.forget_far(1000.0)==[] and len(world.buildings.items)==count       # somebody is standing in it
    # just outside the box but inside the keep distance: zombies there may still be loaded
    walker.lat=la1+(UNLOAD_KEEP_M-50)/111320
    last=1000.0+UNLOAD_AFTER_S*3
    assert await loader.forget_far(last)==[]
    walker.lat=la1+(UNLOAD_KEEP_M+200)/111320
    assert await loader.forget_far(last+10)==[]                                             # only just left
    world.zeds[7]=SimpleNamespace(lat=inside[0],lng=inside[1])
    assert await loader.forget_far(last+UNLOAD_AFTER_S+1)==[]                            # something still walks there
    world.zeds.clear()
    assert await loader.forget_far(last+UNLOAD_AFTER_S+2)==['9zvxvs']
    assert not world.buildings.items and '9zvxvs' not in loader.loaded and '9zvxvs' not in world.resource_regions
    assert not world.buildings.dirty and world.buildings.containing(inside) is None
    # coming back: the database has the map and the open door, and nothing is fetched
    async def unexpected(request):raise AssertionError('a forgotten region should come back from the cache')
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as client:
        assert await loader.load('9zvxvs',client)
    assert len(world.buildings.items)==count and world.buildings.opening(o['id'])[1]['open']


@pytest.mark.asyncio
async def test_a_building_on_a_region_border_stays_while_either_region_is_loaded(maker):
    from types import SimpleNamespace
    from app.game.building_loader import BuildingLoader, UNLOAD_AFTER_S
    world=SimpleNamespace(buildings=Buildings(),actors={},zeds={})
    loader=BuildingLoader(world)
    async def offline(request):return httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        for region in ('9zvxvs','9zvxvt'):
            loader.next_fetch=0;assert await loader.load(region,client);loader.loaded.add(region)   # no politeness gap in a test
    shared=next(iter(loader.members['9zvxvs']));loader.members['9zvxvt'].add(shared)        # its outline crosses the border
    loader.last_near={'9zvxvs':0.0,'9zvxvt':UNLOAD_AFTER_S}                                # the second was visited later
    assert await loader.forget_far(UNLOAD_AFTER_S+1)==['9zvxvs']
    assert shared in world.buildings.items and not any(i in world.buildings.items for i in loader.members.get('9zvxvs',()))
    assert await loader.forget_far(UNLOAD_AFTER_S*2+1)==['9zvxvt'] and not world.buildings.items


def _house(way,lat,lng,size=.0001):
    ring=[(lat,lng),(lat,lng+size*2),(lat+size,lng+size*2),(lat+size,lng),(lat,lng)]
    return {'type':'way','id':way,'tags':{'building':'house'},'geometry':[{'lat':y,'lon':x} for y,x in ring]}


def _middle(record):
    return (sum(p[0] for p in record['outline'])/4,sum(p[1] for p in record['outline'])/4)


@pytest.mark.asyncio
async def test_a_street_of_placeholders_gets_its_real_map_while_someone_stays_but_not_from_under_them(maker):
    import time
    from types import SimpleNamespace
    from app.db import get_sessionmaker
    from app.models import BuildingRegion
    from app.game import building_loader
    from app.game.building_loader import BuildingLoader
    shelters=fallback_records('9zvxvs');stood_in,lived_in,boarded,empty=shelters[0],shelters[1],shelters[2],shelters[3]
    walker=SimpleNamespace(lat=_middle(stood_in)[0],lng=_middle(stood_in)[1],dead=False)
    homes={7:{'building':lived_in['id'],'defenses':{}},8:{'building':'osm:w:1','defenses':{'x':{'hp':80,'building':boarded['id']}}}}
    world=SimpleNamespace(buildings=Buildings(),actors={1:walker},zeds={},homes=homes)
    loader=BuildingLoader(world);answers=[]
    real=[_house(42,44.9,-93.2),_house(43,*_middle(lived_in))]            # the second would stand on somebody's home
    async def respond(request):
        answers.append(request.method)
        return httpx.Response(503) if len(answers)<3 else httpx.Response(200,json={'elements':real})
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await loader.load('9zvxvs',client);loader.loaded.add('9zvxvs')
        assert len(world.buildings.items)==32 and len(answers)==3          # busy twice, then the editing API also failed
        door=world.buildings.items[empty['id']].openings[0];door['open']=True;world.buildings.dirty.add(door['id'])
        assert await loader.refresh_due(client) is None                    # not yet an hour old
        loader.next_fetch=0;loader.expires['9zvxvs']=time.time()-1;revision=world.buildings.revision
        assert await loader.refresh_due(client)=='9zvxvs'
    kept={stood_in['id'],lived_in['id'],boarded['id']}
    assert set(world.buildings.items)==kept|{'osm:w:42'} and world.buildings.revision>revision
    assert not world.buildings.dirty                                       # a door of a shelter that is gone is not saved for ever
    assert loader.members['9zvxvs']==kept|{'osm:w:42'}
    async with get_sessionmaker()() as s:
        row=await s.get(BuildingRegion,'9zvxvs')
        assert row.source=='osm' and row.expires_at>time.time()+building_loader.DAY
        assert {r['id'] for r in row.records}==kept|{'osm:w:42'}
    assert loader.expires['9zvxvs']>time.time()+building_loader.DAY and loader.next_fetch>time.time()
    # after a restart the same street comes back from the database, home shelter and all
    again=SimpleNamespace(buildings=Buildings(),actors={},zeds={},homes=homes)
    async def unexpected(request):raise AssertionError('a refreshed region should come back from the cache')
    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as client:
        assert await BuildingLoader(again).load('9zvxvs',client)
    assert set(again.buildings.items)==kept|{'osm:w:42'}


@pytest.mark.asyncio
async def test_a_map_server_that_is_still_away_is_asked_once_an_hour_and_costs_nothing_known(maker):
    import time
    from types import SimpleNamespace
    from app.db import get_sessionmaker
    from app.models import BuildingRegion
    from app.game import building_loader
    from app.game.building_loader import BuildingLoader
    world=SimpleNamespace(buildings=Buildings(),actors={},zeds={});loader=BuildingLoader(world);calls=[]
    async def offline(request):calls.append(1);return httpx.Response(500)
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        assert await loader.load('9zvxvs',client);loader.loaded.add('9zvxvs');asked=len(calls)
        loader.next_fetch=0;loader.expires['9zvxvs']=time.time()-1
        assert await loader.refresh_due(client)=='9zvxvs' and len(calls)==asked*2
        assert len(world.buildings.items)==32
        assert time.time()+building_loader.GENERATED_TTL-60<loader.expires['9zvxvs']<time.time()+building_loader.GENERATED_TTL+60
        loader.next_fetch=0
        assert await loader.refresh_due(client) is None and len(calls)==asked*2       # not again inside the hour
    # real outlines whose month ran out are kept through an outage, not swapped for placeholders
    async with get_sessionmaker()() as s:
        row=await s.get(BuildingRegion,'9zvxvs')
        row.source='osm';row.expires_at=time.time()-5
        row.records=[{'id':'osm:w:42','name':'House','source':'osm','type':'house',
                      'outline':[[44.9,-93.2],[44.9,-93.1998],[44.9001,-93.1998],[44.9001,-93.2]]}];await s.commit()
    cold=SimpleNamespace(buildings=Buildings(),actors={},zeds={})
    async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as client:
        assert await BuildingLoader(cold).load('9zvxvs',client)
    assert list(cold.buildings.items)==['osm:w:42']
    async with get_sessionmaker()() as s:
        row=await s.get(BuildingRegion,'9zvxvs')
        assert row.source=='osm' and time.time()<row.expires_at<time.time()+building_loader.GENERATED_TTL+60


@pytest.mark.asyncio
async def test_a_region_the_map_knows_is_empty_is_not_asked_about_every_hour(maker):
    import time
    from types import SimpleNamespace
    from app.db import get_sessionmaker
    from app.models import BuildingRegion
    from app.game import building_loader
    from app.game.building_loader import BuildingLoader
    world=SimpleNamespace(buildings=Buildings(),actors={},zeds={})
    async def nothing_here(request):return httpx.Response(200,json={'elements':[]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(nothing_here)) as client:
        assert await BuildingLoader(world).load('9zvxvs',client)
    assert len(world.buildings.items)==32
    async with get_sessionmaker()() as s:
        row=await s.get(BuildingRegion,'9zvxvs')
        assert row.source=='empty' and row.expires_at>time.time()+building_loader.EMPTY_TTL-60
    # a query that timed out answers 200 with a remark: that is an outage, not an empty map
    calls=[]
    async def gave_up(request):
        calls.append(request.method)
        return httpx.Response(200,json={'elements':[],'remark':'runtime error: Query timed out'}) if request.method=='POST' else httpx.Response(503)
    async with httpx.AsyncClient(transport=httpx.MockTransport(gave_up)) as client:
        records,source=await fetch_records('9zvxvt',client)
    assert source=='generated' and calls==['POST','GET']


def test_what_was_only_inside_a_replaced_shelter_goes_with_it():
    from app.game.sim import Actor, World
    w=World();shelters=fallback_records('9zvxvs');w.buildings.add(shelters);w.resource_regions={'9zvxvs'}
    here,far=w.buildings.items[shelters[0]['id']],shelters[1]['id']
    a=Actor(id=1);a.lat,a.lng=here.ll(here.rooms[0]['pos']);w.add_actor(a,0)
    cache={'id':f'hidden:{here.id}:1:0','lat':a.lat,'lng':a.lng,'kind':'bag','loot':[('water',1)],'building':here.id,'room':'Room'}
    a.building_searches[here.id]={'attempts':1,'caches':[cache]}
    a.building_searches[far]={'attempts':2,'caches':[]}
    w._building_loot()
    inside=[sid for sid,s in w.stashes.items() if s.get('building')==here.id]
    assert cache['id'] in inside and any(sid.startswith('room:') for sid in inside)
    w.buildings.remove([here.id]);w.buildings_gone([here.id],'9zvxvs')
    assert not any(s.get('building')==here.id for s in w.stashes.values())
    assert here.id not in a.building_searches and far in a.building_searches
    assert [e for e in a.events if e['e']=='map']
    w._building_loot();assert not any(s.get('building')==here.id for s in w.stashes.values())
    # somebody who was away when it happened: their record of the vanished shelter is dropped on return
    w.buildings.remove([far]);w._building_loot()
    assert far not in a.building_searches
    w.resource_regions=set();a.building_searches['generated:9zvxvtb']={'attempts':1,'caches':[]}
    w._building_loot();assert 'generated:9zvxvtb' in a.building_searches       # only unloaded, not gone
