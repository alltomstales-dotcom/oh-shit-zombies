"""Local-only window fixture: ordinary app, two cloth, no ambient attackers.
Window actions, channel completion, item/geometry commits and reload use real code.
"""
import os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uvicorn
from app.game.sim import World
from app.game.content import TUNE
assert os.environ.get('DATABASE_URL','').startswith('sqlite'),'local SQLite only'
TUNE.update(herd_chance=0.,heli_chance=0.)
original=World._step_actor;seeded=set()
def step(w,a,dt):
 w.zeds.clear()
 if a.id not in seeded and a.placed_at and not a.location_loading_until:
  seeded.add(a.id);a.add('cloth',2)
 original(w,a,dt)
World._step_actor=step
if __name__=='__main__':uvicorn.run('app.main:app',host='127.0.0.1',port=int(sys.argv[1]),log_level='warning')
