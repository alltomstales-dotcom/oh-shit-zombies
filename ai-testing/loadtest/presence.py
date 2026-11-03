#!/usr/bin/env python3
"""Do players see each other? presence.py [N=3] [SECONDS=90] [start=chicago]

Bot 0 stands where it was placed. The others ask the server for a walking route to it and follow
it, as a player's client does (with a fresh route, or the way out of a building, after 3 s without
progress), until they are within 4 m of it and can see it, not through a wall. Then they stand. Every frame each bot receives is checked for
`others`: who it saw, when, from how far, with what name and state. Names are compared with the
names the server handed out at sign-up, and ids with the account ids, which must never appear.
Writes presence_results.json next to this file. Deletes its accounts afterwards."""
import asyncio, json, math, os, sys, time
import httpx, websockets
BASE = os.environ.get('BASE', '127.0.0.1:8120')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
START = sys.argv[3] if len(sys.argv) > 3 else 'chicago'
M = 111320.0
def dist(a, b):
    return math.hypot((a[0] - b[0]) * M, (a[1] - b[1]) * M * math.cos(math.radians(a[0])))

class Bot:
    def __init__(self, i):
        self.i = i; self.hdr = {'cf-connecting-ip': f'198.18.200.{i + 1}'}
        self.pos = None; self.route = []; self.routing = False; self.seen = {}; self.frames = 0; self.with_others = 0
        self.sight = None; self.others_bytes = 0; self.leaks = []; self.err = None; self.arrived_at = None

async def run(bot, bots, t0, stop, http):
    r = await http.post(f'http://{BASE}/api/session', json={'device_id': os.urandom(16).hex(), 'name': 'x'}, headers=bot.hdr)
    j = r.json(); bot.token = j['token']; bot.name = j['player']['name']; bot.pid = j['player']['id']
    async with websockets.connect(f'ws://{BASE}/ws?token={bot.token}', additional_headers=bot.hdr, max_size=None, compression='deflate') as ws:
        async def rx():
            async for m in ws:
                d = json.loads(m)
                if d.get('t') == 'hello':
                    await ws.send(json.dumps({'t': 'act', 'id': 1, 'a': 'background', 'occupation': 'generalist', 'trait': 'balanced', 'life_id': d.get('life_id')}))
                    await ws.send(json.dumps({'t': 'act', 'id': 2, 'a': 'place', 'start': START, 'reason': 'launch', 'source': 'manual', 'lat': 0, 'lng': 0, 'accuracy': 1,
                                              'timestamp': time.time() * 1000, 'ticket': d['placement_ticket'], 'request': os.urandom(8).hex()}))
                elif d.get('t') == 'r' and d.get('a') == 'route':
                    bot.routing = False; bot.routes = getattr(bot, 'routes', []) + [(d.get('ok'), d.get('why'), len(d.get('route') or []))]
                    if d.get('ok') and d.get('route'):bot.route = [list(p) for p in d['route']]
                elif d.get('t') == 'r' and d.get('a') == 'exit_route':
                    bot.routing = False; bot.routes = getattr(bot, 'routes', []) + [('exit', d.get('ok'), d.get('why'), d.get('opening'))]
                    if d.get('ok') and d.get('route'):bot.route = [list(p) for p in d['route']]
                    if d.get('opening'):
                        bot.mid = getattr(bot, 'mid', 10) + 1
                        await ws.send(json.dumps({'t': 'act', 'id': bot.mid, 'a': 'opening', 'opening': d['opening'], 'op': 'open'}))
                elif d.get('t') == 'r' and not d.get('ok'):
                    bot.fails = getattr(bot, 'fails', []) + [(d.get('a'), d.get('why'))]
                elif d.get('t') == 's':
                    y = d['you']; bot.frames += 1; bot.sight = d.get('sight')
                    if y['lat'] or y['lng']:bot.pos = [y['lat'], y['lng']]
                    bot.epochs = (y.get('placement_epoch', 1), y.get('floor_epoch', 0))
                    bot.inside = d.get('inside'); bot.track = getattr(bot, 'track', [])
                    if not bot.track or time.time() - bot.track[-1][0] > 2:bot.track.append((time.time(), bot.pos, bot.inside, sum(1 for z in d.get('z', []) if z[6])))
                    others = d.get('others') or []
                    bot.visible_now = {o[3] for o in others}
                    bot.others_bytes += len(json.dumps(others))
                    if others:bot.with_others += 1
                    for o in others:
                        oid, lat, lng, name, state, heading = o
                        e = bot.seen.setdefault(oid, dict(name=name, first_s=round(time.time() - t0, 1), first_m=round(dist(bot.pos, (lat, lng)), 1) if bot.pos else None, states={}, frames=0, min_m=1e9))
                        e['frames'] += 1; e['states'][state] = e['states'].get(state, 0) + 1
                        if bot.pos:e['min_m'] = round(min(e['min_m'], dist(bot.pos, (lat, lng))), 1)
                        if str(oid) in {str(b.pid) for b in bots if hasattr(b, 'pid')} or len(o) != 6:bot.leaks.append(o)
        task = asyncio.create_task(rx())
        while not stop.is_set():
            await asyncio.sleep(0.2)
            if bot.i == 0 or not bot.pos or not bots[0].pos:continue
            goal = bots[0].pos
            if dist(bot.pos, goal) < 4 and bots[0].name in getattr(bot, 'visible_now', set()):
                bot.route = []; bot.arrived_at = bot.arrived_at or round(time.time() - t0, 1); continue
            now = time.time(); ref = getattr(bot, 'ref', None)
            if ref is None or dist(bot.pos, ref[1]) > 1.0:bot.ref = (now, list(bot.pos))
            elif now - ref[0] > 3.0 and not bot.routing:              # stuck: out of the building, or a fresh route
                bot.ref = (now, list(bot.pos)); bot.route = []; bot.mid = getattr(bot, 'mid', 10) + 1; bot.routing = True
                bot.unsticks = getattr(bot, 'unsticks', 0) + 1
                await ws.send(json.dumps({'t': 'act', 'id': bot.mid, 'a': 'exit_route'} if bot.inside else {'t': 'act', 'id': bot.mid, 'a': 'route', 'lat': goal[0], 'lng': goal[1]}))
                continue
            if not bot.route and not bot.routing:
                bot.mid = getattr(bot, 'mid', 10) + 1; bot.routing = True; await ws.send(json.dumps({'t': 'act', 'id': bot.mid, 'a': 'route', 'lat': goal[0], 'lng': goal[1]}))
                continue
            while bot.route and dist(bot.pos, bot.route[0]) < 1.0:bot.route.pop(0)
            if bot.route:
                wp = bot.route[0]; d = dist(bot.pos, wp); f = min(1.0, 3.0 / d) if d else 1.0
                p = [bot.pos[0] + (wp[0] - bot.pos[0]) * f, bot.pos[1] + (wp[1] - bot.pos[1]) * f]
                await ws.send(json.dumps({'t': 'pos', 'lat': p[0], 'lng': p[1], 'acc': 1, 'mode': 'desk', 'placement_epoch': bot.epochs[0], 'floor_epoch': bot.epochs[1]}))
        task.cancel()

async def main():
    bots = [Bot(i) for i in range(N)]; stop = asyncio.Event(); t0 = time.time()
    async with httpx.AsyncClient(timeout=30) as http:
        tasks = [asyncio.create_task(run(b, bots, t0, stop, http)) for b in bots]
        await asyncio.sleep(SECS); stop.set()
        res = await asyncio.gather(*tasks, return_exceptions=True)
        for b, r in zip(bots, res):
            if isinstance(r, Exception):b.err = repr(r)[:160]
        for b in bots:
            try:await http.delete(f'http://{BASE}/api/me', headers={'authorization': 'Bearer ' + b.token, **b.hdr})
            except Exception:pass
    names = {b.name for b in bots}
    out = dict(when=time.strftime('%Y-%m-%d %H:%M:%S %Z'), base=BASE, n=N, secs=SECS, bots=[])
    for b in bots:
        others = {b2.name for b2 in bots if b2 is not b}
        saw = {e['name'] for e in b.seen.values()}
        out['bots'].append(dict(name=b.name, frames=b.frames, frames_with_others=b.with_others, sight_m=b.sight, arrived_s=b.arrived_at,
                                saw=b.seen, saw_everyone=others <= saw, names_all_generated=saw <= names, others_bytes_per_frame=round(b.others_bytes / max(1, b.frames)),
                                track=[(round(t - t0, 1), round(dist(p, bots[0].pos), 1) if p and bots[0].pos else None, ins, zs) for t, p, ins, zs in getattr(b, 'track', [])][:40],
                                leaks=b.leaks[:3], err=b.err, routes=getattr(b, 'routes', [])[:12], fails=getattr(b, 'fails', [])[:8]))
    out['pass'] = all(x['saw_everyone'] and x['names_all_generated'] and not x['leaks'] and not x['err'] for x in out['bots'])
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presence_results.json'), 'w'), indent=1)
    for x in out['bots']:
        print(x['name'], 'frames', x['frames'], 'with others', x['frames_with_others'], 'arrived', x['arrived_s'], 'saw everyone', x['saw_everyone'], 'generated names', x['names_all_generated'], 'bytes/frame', x['others_bytes_per_frame'], 'err', x['err'])
        print('    routes', x['routes'][:6], 'fails', x['fails'][:4])
        print('    track (s, m to bot 0, inside, zombies on it)', x['track'][:12])
        for oid, e in x['saw'].items():print('   ', oid, e['name'], 'first at', e['first_s'], 's from', e['first_m'], 'm; closest', e['min_m'], 'm; states', e['states'])
    print('PASS' if out['pass'] else 'FAIL')

asyncio.run(main())
