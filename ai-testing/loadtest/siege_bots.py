#!/usr/bin/env python3
"""Siege bots over the real socket: N scripted survivors each play one siege at once, with the same
policy as tools/siege_sim.py, seeing only what a player's frame shows, a quarter-second late.
Measures what the bar needs (each bot's end time and result) and what the load test needs (ping,
frame gaps, the app's CPU, the server's own siege stats lines).

  siege_bots.py N [--base 127.0.0.1:8140] [--app osz-siege-test] [--out file.jsonl] [--limit S]
Each bot makes a throwaway account and deletes it afterwards."""
import argparse, asyncio, json, math, os, random, statistics as st, subprocess, sys, time
import httpx, websockets
sys.path.insert(0, os.path.expanduser('~/osz-stack/tools'))
sys.path.insert(0, os.path.expanduser('~/osz-stack/src'))
from siege_sim import Policy                     # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('n', type=int); ap.add_argument('--base', default='127.0.0.1:8140'); ap.add_argument('--app', default='osz-siege-test')
ap.add_argument('--out'); ap.add_argument('--limit', type=float, default=1900.0); ap.add_argument('--stagger', type=float, default=2.0)
ap.add_argument('--tag', default=''); ap.add_argument('--again', action='store_true', help='start a new siege at once after each end (load tests)')
o = ap.parse_args()
OUT = o.out or os.path.expanduser(f'~/osz-stack/loadtest/siege/{time.strftime("%Y%m%d_%H%M")}_{o.n}{o.tag}.jsonl')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
pings, gaps = [], []
results = []
T_START = time.time()


def log(**kw):
    with open(OUT, 'a') as f:
        f.write(json.dumps(dict(wall=time.strftime('%H:%M:%S'), **kw)) + '\n')


async def bot(i, http):
    t_start = time.time()
    while True:
        await one_siege(i, http)
        if not o.again or time.time() - t_start > o.limit - 5:
            return


async def one_siege(i, http):
    hdr = {'cf-connecting-ip': f'198.18.{40 + i // 250}.{i % 250 + 1}'}
    r = await http.post(f'http://{o.base}/api/session', json={'device_id': os.urandom(16).hex(), 'name': 'x'}, headers=hdr)
    token = r.json()['token']
    pol = Policy(random.Random(i)); frame = {}; body = {}; last = None; info = {}; ended = None
    t0 = time.time(); queue = []
    try:
        async with websockets.connect(f'ws://{o.base}/ws/siege?token={token}', additional_headers=hdr, max_size=None, open_timeout=30) as ws:
            async def rx():
                nonlocal frame, body, last, info, ended
                async for m in ws:
                    d = json.loads(m); t = d.get('t')
                    if t == 's':
                        now = time.time()
                        if last: gaps.append(now - last)
                        last = now
                        queue.append((now, d))
                        if d.get('body'): body = d['body']
                        info = d.get('siege') or info
                        if info.get('over') and ended is None:
                            ended = info['over']
                    elif t == 'pong':
                        pings.append(time.time() * 1000 - d['c'])
                    elif t == 'full':
                        log(bot=i, refused=d.get('why')); return
            task = asyncio.create_task(rx()); next_ping = 0; mid = 10; picked_for = None
            while not task.done() and time.time() - t0 < o.limit and not (o.again and time.time() - T_START > o.limit):
                await asyncio.sleep(0.05)
                now = time.time()
                if now >= next_ping:
                    next_ping = now + 2; await ws.send(json.dumps({'t': 'ping', 'c': now * 1000}))
                if ended is not None:
                    break
                while queue and now - queue[0][0] >= 0.25:     # what the bot sees arrives a quarter-second late
                    frame = queue.pop(0)[1]
                if not frame:
                    continue
                s = frame.get('siege') or {}
                if s.get('choice') and picked_for != (s['level'], tuple(c['id'] for c in s['choice'])):
                    picked_for = (s['level'], tuple(c['id'] for c in s['choice']))
                    mid += 1; await ws.send(json.dumps({'t': 'act', 'id': mid, 'a': 'siege_pick', 'pick': pol.pick(s['choice'])}))
                    continue
                y = frame['you']
                you = {'lat': y['lat'], 'lng': y['lng'], 'hp': y['hp'], 'end': y['end'],
                       'wounds': body.get('wounds', []), 'bandages': sum(it['qty'] for it in body.get('items', []) if it['code'] == 'bandage')}
                boss = (s.get('boss') or {}).get('id')
                zs = [{'id': z[0], 'lat': z[1], 'lng': z[2], 'state': z[3], 'boss': z[0] == boss} for z in frame.get('z', [])]
                busy = y.get('busy', 0) > 0.05 or bool(y.get('channel'))
                act, args, target = pol.decide(now, you, zs, s.get('chests') or [], s.get('arena') or {}, busy)
                if target and now - getattr(bot, f'_p{i}', 0) >= 0.25:      # the real client sends at most ~9 a second
                    setattr(bot, f'_p{i}', now)
                    await ws.send(json.dumps({'t': 'pos', 'lat': target[0], 'lng': target[1], 'acc': 1, 'mode': 'desk',
                                              'placement_epoch': y.get('placement_epoch', 1), 'floor_epoch': 0}))
                if act and now - getattr(bot, f'_a{i}', 0) > 0.3:
                    setattr(bot, f'_a{i}', now)
                    mid += 1; await ws.send(json.dumps({'t': 'act', 'id': mid, 'a': act, **args}))
            await asyncio.sleep(1.0)
            task.cancel()
    except Exception as e:
        log(bot=i, error=repr(e)[:200])
    finally:
        try:
            await http.delete(f'http://{o.base}/api/me', headers={'authorization': 'Bearer ' + token, **hdr})
        except Exception:
            pass
    row = dict(bot=i, result=(ended or {}).get('result'), t=(ended or {}).get('t'), kills=(ended or {}).get('kills'),
               level=(ended or {}).get('level'), bosses=(ended or {}).get('bosses'), score=(ended or {}).get('score'),
               cause=(ended or {}).get('cause'), haul=len((ended or {}).get('haul') or []), wall_s=round(time.time() - t0))
    results.append(row); log(**row)
    print(json.dumps(row), flush=True)


def docker_stats(name):
    try:
        out = subprocess.run(['docker', 'stats', '--no-stream', '--format', '{{.CPUPerc}}|{{.MemUsage}}', name], capture_output=True, text=True, timeout=30).stdout.strip()
        cpu, mem = out.split('|'); return float(cpu.strip('%')), mem.split('/')[0].strip()
    except Exception:
        return None, None


async def sampler(stop):
    global pings, gaps
    while not stop.is_set():
        await asyncio.sleep(60)
        ps, gs = sorted(pings), sorted(gaps); pings, gaps = [], []
        cpu, mem = await asyncio.to_thread(docker_stats, o.app)
        row = dict(minute=True, bots=sum(1 for r in results) , ping_p50=round(ps[len(ps)//2]) if ps else None, ping_p95=round(ps[int(len(ps)*.95)]) if ps else None,
                   gap_p95_ms=round(gs[int(len(gs)*.95)] * 1000) if gs else None, app_cpu=cpu, app_mem=mem)
        log(**row); print('minute', json.dumps(row), flush=True)


async def main():
    stop = asyncio.Event()
    async with httpx.AsyncClient(timeout=30) as http:
        samp = asyncio.create_task(sampler(stop))
        tasks = []
        for i in range(o.n):
            tasks.append(asyncio.create_task(bot(i, http)))
            await asyncio.sleep(o.stagger)
        await asyncio.gather(*tasks)
        stop.set(); samp.cancel()
    done = [r for r in results if r['t'] is not None]
    if done:
        print('ends (min):', sorted(round(r['t'] / 60, 1) for r in done))
        print('dead before 10:00:', sum(1 for r in done if r['result'] == 'dead' and r['t'] < 600), 'of', len(done),
              '| extracted:', sum(1 for r in done if r['result'] == 'extracted'))
    print('out', OUT)

asyncio.run(main())
