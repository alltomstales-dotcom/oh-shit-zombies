"""Local testing only: the ordinary app with the shared sky sped up, so a browser check can see
rain and a whole helicopter pass in a few minutes instead of waiting hours for the real schedule.

    DATABASE_URL=sqlite+aiosqlite:////tmp/osz-sky.db python tools/serve_fast_sky.py 8020

It rains all the time and a helicopter comes in every four-minute block: heard for 25 s, overhead
for 70 s. A first hour is not spared and it also flies at night, so the check runs at any time.
Never point this at the production database.
"""
import os
import sys

import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.game.content import TUNE  # noqa: E402

assert "sqlite" in os.environ.get("DATABASE_URL", ""), "a local SQLite DATABASE_URL only"
TUNE.update(rain_chance=1.0, heli_chance=1.0, heli_block_s=240.0, heli_warn_s=25.0, heli_over_s=70.0,
            heli_spare_new_s=0.0, heli_min_light=0.0)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8020, log_level="warning")
