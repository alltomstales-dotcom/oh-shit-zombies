"""Local-only fatal-wound fixture; ordinary death/new-life/search/transfer persistence.
Never use a production database. Seeds one damaged knife and fatal neck bleeding
once per connected player after current-location placement and mapping settle.
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uvicorn
from app.game.sim import World
from app.game.content import TUNE
assert os.environ.get('DATABASE_URL','').startswith('sqlite'), 'local SQLite only'
TUNE.update(herd_chance=0.,heli_chance=0.)
original=World._step_actor
seeded=set()
def step(w,a,dt):
 w.zeds.clear()
 if a.id not in seeded and a.placed_at and w.now-a.placed_at>8 and not a.location_loading_until:
  seeded.add(a.id);a.add('knife',1,2);a.hp=.1
  a.wounds.append({'id':a._next_wound_id,'part':'neck','kind':'bite','t':w.now,'bleeding':True,'bandaged':False,'clean':False})
  a._next_wound_id+=1;a.dirty=True
 original(w,a,dt)
World._step_actor=step
from app.main import app
from app.game.hub import get_hub
@app.get('/_fixture/recovery')
def diagnostic():
 w=get_hub().world
 return {'bodies':[{'id':b['id'],'ready':b['id'] in w.corpse_ready,'owner':b.get('owner')} for b in w.corpses.values()], 'actors':[{'id':a.id,'dead':a.dead,'visible':[(b['id'],w.visible((a.lat,a.lng),(b['lat'],b['lng']))) for b in w.corpses.values()]} for a in w.actors.values()]}
app.router.routes.insert(0,app.router.routes.pop())
if __name__=='__main__':uvicorn.run('app.main:app',host='127.0.0.1',port=int(sys.argv[1]),log_level='warning')
