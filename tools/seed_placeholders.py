"""Give the regions round a point placeholder shelters that run out soon, to watch a live map refresh.

    DATABASE_URL=sqlite+aiosqlite:////tmp/osz-refresh.db python -m tools.seed_placeholders 44.9778 -93.265 60

Local test databases only. It stands in for a map-server outage that ended: start the server on
this database, stand a survivor at the point, and after the given seconds the loader asks the
map server again and swaps the shelters for the real streets (see tools/mobile_map_refresh_check.mjs).
"""
import asyncio
import sys
import time
from types import SimpleNamespace

from app.db import get_engine, get_sessionmaker
from app.game.building_loader import fallback_records, wanted_regions
from app.models import Base, BuildingRegion


async def main(lat, lng, seconds):
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    regions = wanted_regions([SimpleNamespace(lat=lat, lng=lng, dead=False)])
    async with get_sessionmaker()() as s:
        for region in regions:
            row = await s.get(BuildingRegion, region) or BuildingRegion(id=region)
            row.source, row.records, row.expires_at = 'generated', fallback_records(region), time.time() + seconds
            s.add(row)
        await s.commit()
    print('placeholders for', seconds, 's in', ' '.join(regions))


if __name__ == '__main__':
    asyncio.run(main(float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 60))
