"""Local-only b-roll fixture (2026-11-03): the ordinary app, with no zombies (so a calm feature clip can be
staged) and, once per survivor after placement, 2 cloth (a curtain), 4 stone and 3 branches (a cooking
fire). Modelled on src/tools/serve_windows.py. Everything else (map, buildings, actions, drawers) is the
real game. Never point this at a real database.
    cd ~/osz-stack/src && DATABASE_URL=sqlite+aiosqlite:////tmp/x.db python ../tools/serve_broll.py 8150
"""
import os
import sys

sys.path.insert(0, os.environ.get('OSZ_SRC', os.getcwd()))
import uvicorn  # noqa: E402
from app.game.content import TUNE  # noqa: E402
from app.game.sim import World  # noqa: E402

assert os.environ.get('DATABASE_URL', '').startswith('sqlite'), 'local SQLite only'
TUNE.update(herd_chance=0., heli_chance=0.)
original = World._step_actor
seeded = set()


def step(w, a, dt):
    w.zeds.clear()
    if a.id not in seeded and a.placed_at and not a.location_loading_until:
        seeded.add(a.id)
        a.add('cloth', 2); a.add('stone', 4); a.add('branch', 3)
    original(w, a, dt)


World._step_actor = step
if __name__ == '__main__':
    uvicorn.run('app.main:app', host='127.0.0.1', port=int(sys.argv[1]), log_level='warning')
