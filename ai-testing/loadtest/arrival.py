#!/usr/bin/env python3
"""Does a new survivor arrive to buildings? For each start city: join, place, and look at the first
frames after placement: are buildings there, and is the server still 'mapping'?"""
import asyncio, json, os, sys, time
import httpx, websockets
BASE = os.environ.get('BASE', '127.0.0.1:8120')
async def one(city, i):
    hdr = {'cf-connecting-ip': f'198.18.210.{i + 1}'}
    async with httpx.AsyncClient(timeout=30) as http:
        tok = (await http.post(f'http://{BASE}/api/session', json={'device_id': os.urandom(16).hex(), 'name': 'x'}, headers=hdr)).json()['token']
        out = dict(city=city)
        try:
            async with websockets.connect(f'ws://{BASE}/ws?token={tok}', additional_headers=hdr, max_size=None) as ws:
                t0 = time.time(); placed = None; nb = 0
                async for m in ws:
                    d = json.loads(m)
                    if d.get('t') == 'hello':
                        await ws.send(json.dumps({'t': 'act', 'id': 1, 'a': 'place', 'start': city, 'reason': 'launch', 'source': 'manual', 'lat': 0, 'lng': 0, 'accuracy': 1, 'timestamp': time.time() * 1000, 'ticket': d['placement_ticket'], 'request': os.urandom(8).hex()}))
                    elif d.get('t') == 's' and (d['you']['lat'] or d['you']['lng']):
                        if placed is None:
                            placed = time.time(); out.update(first_frame_s=round(placed - t0, 2), buildings_in_first_frame=len(d.get('buildings') or []), mapping_in_first_frame=d.get('mapping'), arriving=d['you'].get('arriving'))
                        nb = max(nb, len(d.get('buildings') or []))
                        if time.time() - placed > 3: out['buildings_after_3s'] = nb; break
                    if time.time() - t0 > 60: out['timeout'] = True; break
        finally:
            await http.delete(f'http://{BASE}/api/me', headers={'authorization': 'Bearer ' + tok, **hdr})
        return out
async def main():
    for i, c in enumerate(sys.argv[1:] or ['chicago', 'minneapolis', 'manchester']):
        print(json.dumps(await one(c, i)))
asyncio.run(main())
