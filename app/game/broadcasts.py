"""Regional radio reports and rare shared sounds, scheduled on the real clock."""
from app.geo import cell_of,_decode_bbox
from app.rng import seeded
from app.game import weather,herds,survival
from app.models import WorldEvent

BLOCK=6*3600

def event(region,block):
 rng=seeded(f'broadcast-event:{region}:{block}')
 if rng.random()>.5:return None
 la0,la1,ln0,ln1=_decode_bbox(region)
 kind=rng.choice(('gunshot','scream'))
 return dict(id=f'sound:{region}:{block}',at=block*BLOCK+rng.uniform(600,BLOCK-600),
             lat=rng.uniform(la0,la1),lng=rng.uniform(ln0,ln1),kind=kind,radius=140 if kind=='gunshot' else 90)

def due(w):
 regions={cell_of(a.lat,a.lng,6) for a in w.actors.values() if not a.dead and a.placed_at and not a.location_loading_until}
 for region in regions:
  e=event(region,int(w.now//BLOCK))
  if e and e['at']<=w.now<e['at']+5 and e['id'] not in w.broadcast_fired:yield e

async def load(s,now=None):
 from sqlalchemy import select,delete
 if now is not None:
  await s.execute(delete(WorldEvent).where(WorldEvent.fired_at<now-7*86400));await s.commit()
 return set((await s.execute(select(WorldEvent.id))).scalars())

def report(w,a):
 now=w.now;lines=[]
 rain=weather.rain(a.lat,a.lng,now)
 lines.append('Rain across the district; collect water while it lasts.' if rain else 'Dry conditions across the district.')
 h=weather.next_helicopter(a.lat,a.lng,now,blocks=2)
 if h and h[0]<now+7200:lines.append('Aircraft activity expected '+('now' if h[0]<=now else 'in about '+str(max(1,round((h[0]-now)/60)))+' minutes')+'. Stay sheltered; it draws a crowd outdoors.')
 herd=herds.next_crossing(a.lat,a.lng,now,blocks=2)
 if herd and herd['t0']<now+7200:lines.append('A migrating horde is crossing nearby '+('now' if herd['t0']<=now else 'in about '+str(max(1,round((herd['t0']-now)/60)))+' minutes')+'. Routes may change; keep an escape path.')
 region=cell_of(a.lat,a.lng,6)
 for block in (int(now//BLOCK),int(now//BLOCK)+1):
  e=event(region,block)
  if e and now-900<e['at']<=now+7200:
   lines.append(('Recent reports of ' if e['at']<=now else 'Reports of possible ')+('gunfire' if e['kind']=='gunshot' else 'distress calls')+' in the area. Sound can draw zombies away from safe routes.')
 lines.append('Reports cover the local district; they do not reveal hidden zombies. Listening stays quiet, and the world keeps moving.')
 return {'ok':True,'broadcast':{'at':now,'region':region,'lines':lines}}

def action(w,a,item=None,object=None,**_):
 if a.dead:return {'ok':False,'why':'start a new survivor first'}
 row=a.item(item) if item is not None else None
 portable=bool(row and row['code']=='radio')
 station=next((o for o in survival.objects(w,a) if o['id']==object and o['kind']=='radio' and o['hp']>0),None)
 if not portable and not (station and survival.dist([a.lat,a.lng],[station['lat'],station['lng']])<=2.7 and w.buildings.clear((a.lat,a.lng),(station['lat'],station['lng']))):
  return {'ok':False,'why':'carry a radio or approach a working household radio'}
 return report(w,a)
