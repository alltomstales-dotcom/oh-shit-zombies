"""Geometry rules for the upcoming playable building phase."""
import math
from app.game.buildings import Building, Buildings, inside, osm_xml, segment_distance, mix


def house():
    lat,lng=44.9778,-93.265
    mx=111320*math.cos(math.radians(lat))
    points=[[lat+y/111320,lng+x/mx] for x,y in ((0,0),(20,0),(20,12),(0,12))]
    b=Building(id='test:house',outline=points)
    return b


def test_rooms_and_doors_stay_inside_footprint():
    b=house()
    assert len(b.rooms)==2
    assert len([o for o in b.openings if o['kind']=='door'])==2
    for r in b.rooms:
        assert inside(r['pos'],b.poly)
        assert all(segment_distance(r['pos'],r['pos'],*wall)>1.5 for wall in b.walls)
    assert b.snapshot()==house().snapshot()


def test_closed_door_blocks_then_open_door_allows_entry():
    b=house()
    o=b.openings[0]
    p=tuple((a+c)/2 for a,c in zip(o['a'],o['b']))
    outside,interior=b.ll((p[0],p[1]-2)),b.ll((p[0],p[1]+2))
    assert b.blocks(outside,interior)
    o['open']=True
    assert not b.blocks(outside,interior)
    assert b.blocks(b.ll((1,-2)),b.ll((1,2)))


def test_window_allows_sight_but_blocks_walking_until_broken():
    b=house();o=next(o for o in b.openings if o['kind']=='window')
    p=tuple((a+c)/2 for a,c in zip(o['a'],o['b']))
    a,c=b.ll((p[0],p[1]-2)),b.ll((p[0],p[1]+2))
    assert b.blocks(a,c)
    assert not b.blocks(a,c,0,vision=True)
    o['broken']=True
    assert not b.blocks(a,c)


def test_route_around_wall_and_into_open_rooms_is_clear():
    b=house();world=Buildings();world.items[b.id]=b
    start,goal=b.ll((-3,5)),b.ll((23,5))
    route=world.route(start,goal)
    assert route and len(route)>1
    for p in route:
        assert world.clear(start,p)
        start=p
    for o in b.openings:o['open']=True
    start,goal=b.ll((10,-3)),b.ll(b.rooms[1]['pos'])
    route=world.route(start,goal)
    assert route
    for p in route:
        assert world.clear(start,p)
        start=p


def test_closed_building_has_no_route_to_interior_and_moves_stop():
    b=house();world=Buildings();world.items[b.id]=b
    start,goal=b.ll((10,-1)),b.ll((10,1))
    assert world.move(start,goal)==start
    assert world.route(start,goal,limit=1200)==[]


def test_osm_parser_skips_open_and_complex_shapes():
    xml='<osm>'+''.join(f'<node id="{i}" lat="{y}" lon="{x}"/>' for i,(x,y) in enumerate(((1,1),(2,1),(2,2),(1,2)),1))
    xml+='<way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/><tag k="building" v="house"/></way>'
    xml+='<way id="11"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="building" v="yes"/></way></osm>'
    records=osm_xml(xml)
    assert len(records)==1 and records[0]['id']=='osm:w:10'
    assert len(records[0]['outline'])==4

def test_exit_plan_opens_closed_doors_in_reachable_stages():
    b=house();world=Buildings();world.items[b.id]=b
    start=b.ll(b.rooms[0]['pos'])
    opened=[]
    for _ in range(5):
        result=world.exit_plan(start)
        assert result['ok'],result
        for p in result['route']:
            assert world.clear(start,p)
            start=p
        if not result['opening']:
            assert not b.contains(start)
            break
        _,door=world.opening(result['opening'])
        assert not door['open']
        center=mix(door['a'],door['b'],.5)
        assert math.dist(b.xy(start),center)<2.7
        door['open']=True;opened.append(door['label'])
    else:assert False,'exit did not finish'
    assert 'Entrance' in opened and 'Room door' in opened
    assert not next(o for o in b.openings if o['kind']=='window')['open']


def test_exit_plan_does_not_mutate_shared_opening_state():
    b=house();world=Buildings();world.items[b.id]=b
    result=world.exit_plan(b.ll(b.rooms[0]['pos']))
    assert result['ok']
    assert not any(o['open'] for o in b.openings)


def test_far_apart_points_are_blocked_without_walking_the_whole_grid():
    import time
    from app.game.buildings import Buildings
    geometry=Buildings()
    started=time.perf_counter()
    assert not geometry.clear((0.0,0.0),(41.95,-87.74))
    assert not geometry.clear((44.9778,-93.265),(41.95,-87.74),radius=0,vision=True)
    assert geometry.route((44.9778,-93.265),(41.95,-87.74))==[]
    assert list(geometry.candidates((0.0,0.0),(41.95,-87.74)))==[]
    assert time.perf_counter()-started<.5
    assert geometry.clear((44.9778,-93.265),(44.9790,-93.2640))


def test_route_planning_copies_only_nearby_outlines():
    from app.game.buildings import Buildings
    from app.game.building_loader import fallback_records
    geometry=Buildings();geometry.add(fallback_records('9zvxvs')+fallback_records('dp3wek'))
    here=next(b for b in geometry.items.values() if b.id.startswith('generated:9zvxvs'))
    start=here.ll(here.rooms[0]['pos'])
    local=geometry.local_copy(start)
    assert 0<len(local.items)<len(geometry.items)
    assert all(i.startswith('generated:9zvxvs') for i in local.items)
    assert local.items[here.id] is not here and local.exit_plan(start)['ok']==geometry.exit_plan(start)['ok']
    goal=[start[0]+60/111320,start[1]]
    assert local.route(start,goal)==geometry.route(start,goal)


def _city_blocks(rows=9,cols=7):
    """Staggered 30m x 40m blocks with 8m streets: several blocks of detours between two corners."""
    lat0,lng0=44.97,-93.27;mx=111320*math.cos(math.radians(lat0));out=[]
    for r in range(rows):
        for c in range(cols):
            x=c*38+(19 if r%2 else 0);y=r*48
            out.append({'id':f'osm:w:{r}{c}','type':'yes','source':'osm','name':'Block',
                        'outline':[[lat0+(y+dy)/111320,lng0+(x+dx)/mx] for dx,dy in ((0,0),(30,0),(30,40),(0,40))]})
    return out,(lat0-4/111320,lng0-4/mx),(lat0+(rows*48+2)/111320,lng0+(cols*38+10)/mx)


def test_a_walk_of_several_blocks_finds_a_route():
    geometry=Buildings();records,start,goal=_city_blocks();geometry.add(records)
    assert not geometry.clear(start,goal)
    route=geometry.route(start,goal)
    assert route and route[-1]==goal
    legs=[start]+route
    assert all(geometry.clear(a,b) for a,b in zip(legs,legs[1:]))


def test_walk_to_a_fence_or_gate_stops_beside_it():
    """The fence's own position is on the barrier, so nothing can stand there."""
    g=Buildings();lat,lng=45.0,-93.0;mx=111320*math.cos(math.radians(lat))
    g.obstacles=[dict(id='fence',owner=1,a=[lat,lng-1.3/mx],b=[lat,lng+1.3/mx])]
    start=(lat-6/111320,lng)
    path=g.route(start,(lat,lng))
    assert path,'a built fence must be reachable with Walk here'
    end=path[-1];away=(lat-end[0])*111320
    assert .5<away<2.7                       # on the walker's side and within working reach
    anchor=start
    for p in path:
        assert g.clear(anchor,p);anchor=p
    assert g.route((lat+6/111320,lng),(lat,lng))[-1][0]>lat
    # an ordinary destination is untouched
    assert g.route(start,(lat-3/111320,lng))==[(lat-3/111320,lng)]


def _terrace(n=3,front=6.0,depth=15.0):
    """Attached houses in a row: narrow fronts on the street, long side walls shared."""
    lat,lng=44.9778,-93.265;mx=111320*math.cos(math.radians(lat))
    ll=lambda x,y:[lat+y/111320,lng+x/mx]
    return [{'id':'t:%d'%i,'type':'house','outline':[ll(i*front,0),ll((i+1)*front,0),ll((i+1)*front,depth),ll(i*front,depth)]} for i in range(n)]


def _leads_out(g,b,o):
    others={x['id'] for x in b.openings if x is not o}
    return g.exit_plan(b.ll(b.rooms[0]['pos']),others)['ok']


def test_a_house_in_the_middle_of_a_terrace_can_be_left():
    g=Buildings();g.add(_terrace())
    b=g.items['t:1']
    outside=[o for o in b.openings if o['label']!='Room door']
    assert {o['label'] for o in outside}=={'Entrance','Window'}
    assert all(_leads_out(g,b,o) for o in outside),'door and window must both open onto the street or yard'
    # the same house on its own keeps the ordinary layout and the same opening ids
    alone=Buildings();alone.add([_terrace()[1]]);lone=alone.items['t:1']
    assert {o['label']:o['id'] for o in lone.openings if o['label'] in ('Entrance','Window','Room door')}=={o['label']:o['id'] for o in b.openings if o['label'] in ('Entrance','Window','Room door')}
    assert lone.entrance_edge!=b.entrance_edge


def test_a_detached_building_keeps_its_default_layout():
    g=Buildings();g.add([_terrace()[0]]);b=g.items['t:0']
    plain=Building(id='t:0',type='house',outline=_terrace()[0]['outline'])
    assert b.walls==plain.walls and [(o['id'],o['a'],o['b']) for o in b.openings]==[(o['id'],o['a'],o['b']) for o in plain.openings]


def test_a_neighbour_loaded_later_moves_the_door_and_keeps_its_state():
    first,second,third=_terrace()
    g=Buildings();g.add([second]);b=g.items['t:1']
    door=next(o for o in b.openings if o['label']=='Entrance');door.update(open=True,damage=.4);oid=door['id']
    g.add([first,third])                       # the neighbours arrive with the next map region
    again=next(o for o in b.openings if o['label']=='Entrance')
    assert again['id']==oid and again['open'] and again['damage']==.4
    assert all(_leads_out(g,b,o) for o in b.openings if o['label']!='Room door')
    # loading order does not change where things end up
    together=Buildings();together.add([first,second,third]);same=together.items['t:1']
    assert [(o['id'],o['label'],o['a'],o['b']) for o in same.openings]==[(o['id'],o['label'],o['a'],o['b']) for o in b.openings]


def test_a_building_tagged_only_building_yes_is_not_shown_as_yes():
    from app.game.buildings import Buildings, overpass_json
    ring=[(44.9,-93.2),(44.9,-93.1998),(44.9001,-93.1998),(44.9001,-93.2),(44.9,-93.2)]
    way=lambda i,tags:{'type':'way','id':i,'tags':tags,'geometry':[{'lat':y+i*.001,'lon':x} for y,x in ring]}
    g=Buildings();g.add(overpass_json({'elements':[way(1,{'building':'yes'}),way(2,{'building':'yes','name':'Corner Shop'}),way(3,{'building':'fire_station'})]}))
    shown={b.id:b.snapshot()['name'] for b in g.items.values()}
    assert shown=={'osm:w:1':'Building','osm:w:2':'Corner Shop','osm:w:3':'Fire Station'}


def test_extra_windows_preserve_legacy_openings_and_allow_independent_entry():
    b=house()
    assert [(o['label'],o['id']) for o in b.openings[:3]]==[
        ('Entrance','test:house:0'),('Window','test:house:1'),('Room door','test:house:2')]
    panes=[o for o in b.openings if o['kind']=='window']
    assert len(panes)==3
    assert len({o['id'] for o in b.openings})==len(b.openings)
    for o in panes:
        p=mix(o['a'],o['b'],.5)
        start,end=b.ll((p[0],p[1]-1)),b.ll((p[0],p[1]+1))
        assert b.blocks(start,end)
        o['open']=True
        assert not b.blocks(start,end)
        o['barricaded']=True
        assert b.blocks(start,end)
        o['barricaded']=False
    old={o['label']:(o['id'],o['open']) for o in b.openings}
    b.relayout(b.entrance_edge,b.window_edge)
    assert {o['label']:(o['id'],o['open']) for o in b.openings}==old
