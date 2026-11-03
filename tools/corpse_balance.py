"""Scripted fighter ceiling versus a stated, reproducible room-search budget.

python -m tools.corpse_balance
Not a human pacing claim: the fighter gets every corpse item for free; room
searching is modeled at one completed container per minute, including approach,
search, transfer and departure. Actual room loot comes from the game generator.
"""
from app.game.buildings import Building
from app.game.sim import Actor, World, shift
from tools.walk_bots import walk


def main():
    rows=[walk(n,20,'fighter',False,1,{},True) for n in range(30)]
    hours=sum(r['minutes'] for r in rows)/60
    kills=sum(r['kills'] for r in rows)/hours
    bodies=sum(r['body_loot_qty'] for r in rows)/hours
    results={}
    origin=(44.9778,-93.265)
    outline=[list(shift(*origin,x,y)) for x,y in ((0,0),(20,0),(20,12),(0,12))]
    for theme in ('Kitchen','Bathroom','Bedroom','Garage'):
        total=0
        for n in range(60):
            w=World();a=Actor(id=1,lat=origin[0],lng=origin[1]);w.add_actor(a,100)
            b=Building(id=f'budget:{theme}:{n}',outline=outline,type='house');b.rooms[0]['name']=theme
            w.buildings.items[b.id]=b;w._building_loot()
            total+=sum(q for _,q in w.stashes['room:'+b.rooms[0]['id']]['loot'])
        results[theme]=total
    assert bodies<min(results.values()),'farming ceiling exceeds room-search budget'
    print({'walks':len(rows),'simulated_hours':round(hours,2),'fighter_kills_per_hour':round(kills,2),
           'body_item_ceiling_per_hour':round(bodies,2),'room_items_per_hour_at_one_search_per_minute':results,
           'deaths':sum(r['died'] is not None for r in rows)})


if __name__=='__main__':main()
