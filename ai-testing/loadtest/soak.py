#!/usr/bin/env python3
"""Soak test: hours of players coming and going. soak.py HOURS [target=20]

Keeps about `target` walking bots on the server (it wanders between 70% and 100% of it). Each bot
plays for 2 to 20 minutes, walking, swinging and searching now and then, then leaves: most delete
their account as a quitting viewer's data should go, some just close the tab and come back later
with the same token. A bot that dies starts a new survivor, as a player would. Starts are mostly
Chicago, some Minneapolis and Manchester.

Every minute one line goes to soak/<start>.jsonl: bots online, joins/leaves/deaths that minute, ping
p50/p95/max, frame gaps, the app's and database's memory and CPU, database size and row counts, app
restarts, and new error lines in the app log. Stop early with a file named STOP_SOAK next to this.
It pauses (no new bots) while the machine has under 2 GB available."""
import asyncio, collections, json, math, os, random, statistics as st, subprocess, sys, time
import httpx, websockets
BASE = os.environ.get('BASE', '127.0.0.1:8120'); APP = os.environ.get('APP', 'osz-stack-app-1'); DB = os.environ.get('DBC', 'osz-stack-db-1')
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else 20
HERE = os.path.dirname(os.path.abspath(__file__)); STOP = os.path.join(HERE, 'STOP_SOAK')
os.makedirs(os.path.join(HERE, 'soak'), exist_ok=True)
OUT = os.path.join(HERE, 'soak', time.strftime('%Y%m%d_%H%M') + '.jsonl')
M = 111320.0
rnd = random.Random(20261103)
minute = collections.Counter(); pings = []; gaps = []; errors = collections.Counter(); online = set(); saved_tokens = []
seq = 0
ENDING = False

def avail_mb():
    return int(open('/proc/meminfo').read().split('MemAvailable:')[1].split()[0]) // 1024

async def bot(i, http, token=None):
    hdr = {'cf-connecting-ip': f'198.19.{(i // 250) % 250}.{i % 250 + 1}'}
    start = rnd.choices(['chicago', 'minneapolis', 'manchester'], [7, 2, 1])[0]
    stay = rnd.uniform(120, 1200); keep = rnd.random() < 0.3
    try:
        if token is None:
            r = await http.post(f'http://{BASE}/api/session', json={'device_id': os.urandom(16).hex(), 'name': 'x'}, headers=hdr)
            if r.status_code != 200:errors[f'session {r.status_code}'] += 1; return
            token = r.json()['token']; minute['new_accounts'] += 1
        else:
            minute['returning'] += 1
        t0 = time.time(); pos = None; angle = rnd.random() * 6.28; last = None; dead_at = None
        async with websockets.connect(f'ws://{BASE}/ws?token={token}', additional_headers=hdr, max_size=None, open_timeout=30, compression='deflate') as ws:
            online.add(i); minute['joins'] += 1
            async def rx():
                nonlocal pos, last, dead_at
                async for m in ws:
                    d = json.loads(m); t = d.get('t')
                    if t == 'hello':
                        await ws.send(json.dumps({'t': 'act', 'id': 1, 'a': 'background', 'occupation': 'generalist', 'trait': 'balanced', 'life_id': d.get('life_id')}))
                        await ws.send(json.dumps({'t': 'act', 'id': 2, 'a': 'place', 'start': start, 'reason': 'launch', 'source': 'manual', 'lat': 0, 'lng': 0, 'accuracy': 1,
                                                  'timestamp': time.time() * 1000, 'ticket': d['placement_ticket'], 'request': os.urandom(8).hex()}))
                    elif t == 's':
                        now = time.time()
                        if last:gaps.append(now - last)
                        last = now; minute['frames'] += 1; minute['bytes'] += len(m)
                        y = d['you']
                        if y['lat'] or y['lng']:pos = [y['lat'], y['lng']]
                        if y.get('dead') and dead_at is None:dead_at = now; minute['deaths'] += 1
                    elif t == 'pong':
                        pings.append(time.time() * 1000 - d['c'])
                    elif t == 'full':
                        minute['refused_full'] += 1
            task = asyncio.create_task(rx()); nextmove = nextping = 0; nextact = time.time() + rnd.uniform(3, 8)
            while time.time() - t0 < stay and not task.done() and not ENDING:
                now = time.time()
                if dead_at and now - dead_at > 6:
                    dead_at = None; pos = None; await ws.send(json.dumps({'t': 'new'})); minute['new_lives'] += 1
                if pos and now >= nextmove and not dead_at:
                    angle += rnd.uniform(-.35, .35)
                    p = [pos[0] + math.sin(angle) * 1.6 / M, pos[1] + math.cos(angle) * 1.6 / (M * math.cos(math.radians(pos[0])))]
                    await ws.send(json.dumps({'t': 'pos', 'lat': p[0], 'lng': p[1], 'acc': 1, 'mode': 'desk', 'placement_epoch': 1, 'floor_epoch': 0})); nextmove = now + .25
                if now >= nextping:
                    await ws.send(json.dumps({'t': 'ping', 'c': now * 1000})); nextping = now + 2
                if pos and now >= nextact and not dead_at:
                    await ws.send(json.dumps({'t': 'act', 'id': 3, 'a': rnd.choice(['swing', 'swing', 'shove', 'search'])})); nextact = now + rnd.uniform(3, 8)
                await asyncio.sleep(.05)
            task.cancel()
    except Exception as e:
        errors[type(e).__name__] += 1
    finally:
        online.discard(i); minute['leaves'] += 1
    if keep:
        saved_tokens.append((token, time.time() + rnd.uniform(60, 900)))
    else:
        try:
            r = await http.delete(f'http://{BASE}/api/me', headers={'authorization': 'Bearer ' + token, **hdr})
            minute['deleted'] += 1
        except Exception as e:errors['delete ' + type(e).__name__] += 1

def sh(*a):
    return subprocess.run(a, capture_output=True, text=True, timeout=60).stdout

def sample(since):
    out = {}
    for name, c in (('app', APP), ('db', DB)):
        try:
            cpu, mem = sh('docker', 'stats', '--no-stream', '--format', '{{.CPUPerc}}|{{.MemUsage}}', c).strip().split('|')
            out[f'{name}_cpu'] = float(cpu.strip('%')); u = mem.split('/')[0].strip()
            out[f'{name}_mem_mb'] = float(u.replace('MiB', '')) if 'MiB' in u else float(u.replace('GiB', '')) * 1024
        except Exception:pass
    q = ("select pg_database_size('osz'), (select count(*) from player), (select count(*) from survivor), (select count(*) from session_token), "
         "(select count(*) from world_corpse), (select count(*) from zed_dead), (select count(*) from building_opening), (select count(*) from world_events), (select count(*) from building_region)")
    try:
        v = sh('docker', 'exec', DB, 'psql', '-U', 'osz', '-d', 'osz', '-Atc', q).strip().split('|')
        out.update(db_bytes=int(v[0]), players=int(v[1]), survivors=int(v[2]), tokens=int(v[3]), corpses=int(v[4]), zed_dead=int(v[5]), openings=int(v[6]), world_events=int(v[7]), regions=int(v[8]))
    except Exception:pass
    try:
        info = json.loads(sh('docker', 'inspect', APP))[0]
        out.update(app_restarts=info['RestartCount'], app_started=info['State']['StartedAt'], app_health=info['State'].get('Health', {}).get('Status'))
    except Exception:pass
    logs = sh('docker', 'logs', '--since', since, APP) + subprocess.run(['docker', 'logs', '--since', since, APP], capture_output=True, text=True).stderr
    out['log_lines'] = len(logs.splitlines()); out['log_errors'] = sum(1 for l in logs.splitlines() if 'ERROR' in l or 'Traceback' in l or 'Exception' in l)
    out['slow_ticks'] = logs.count('slow tick'); out['log_tail'] = [l[:200] for l in logs.splitlines() if 'ERROR' in l or 'Traceback' in l or 'slow tick' in l][:3]
    return out

async def main():
    global seq, pings, gaps, ENDING
    t_end = time.time() + HOURS * 3600; tasks = set(); f = open(OUT, 'a', buffering=1)
    print('writing', OUT, flush=True)
    async with httpx.AsyncClient(timeout=30) as http:
        next_sample = time.time() + 60; since = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()); want = TARGET
        while time.time() < t_end and not os.path.exists(STOP):
            now = time.time()
            if rnd.random() < 0.01:want = rnd.randint(int(TARGET * .7), TARGET)
            if sum(1 for t in tasks if not t.done()) < want and avail_mb() >= 2048:
                due = [x for x in saved_tokens if x[1] <= now]
                if due and rnd.random() < 0.5:
                    saved_tokens.remove(due[0]); seq += 1; tasks.add(asyncio.create_task(bot(seq, http, token=due[0][0])))
                else:
                    seq += 1; tasks.add(asyncio.create_task(bot(seq, http)))
            tasks = {t for t in tasks if not t.done()}
            if now >= next_sample:
                ps = sorted(pings); gs = sorted(gaps); pings, gaps = [], []
                row = dict(t=time.strftime('%Y-%m-%d %H:%M:%S'), elapsed_min=round((now - (t_end - HOURS * 3600)) / 60, 1), online=len(online), want=want,
                           ping_p50=round(ps[len(ps) // 2]) if ps else None, ping_p95=round(ps[int(len(ps) * .95)]) if ps else None, ping_max=round(ps[-1]) if ps else None,
                           gap_p95_ms=round(gs[int(len(gs) * .95)] * 1000) if gs else None, kb_per_player_s=round(minute['bytes'] / 1024 / 60 / max(1, len(online)), 1),
                           errors=dict(errors), host_avail_mb=avail_mb(), load=float(open('/proc/loadavg').read().split()[0]), **{k: v for k, v in minute.items() if k != 'bytes'})
                row.update(await asyncio.to_thread(sample, since)); since = time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())
                f.write(json.dumps(row) + '\n'); minute.clear(); errors.clear(); next_sample = now + 60
                print(row['t'], 'online', row['online'], 'ping', row['ping_p50'], row['ping_p95'], 'app', row.get('app_mem_mb'), 'MB', row.get('app_cpu'), '% db', row.get('db_bytes'), 'errs', row.get('log_errors'), flush=True)
            await asyncio.sleep(rnd.uniform(1.0, 6.0))
        print('ending: waiting for bots to leave', flush=True)
        ENDING = True                                      # bots finish their loop and delete or keep as planned
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 120)
        for token, _ in saved_tokens:                      # tidy: the returning-player accounts go too
            try:await http.delete(f'http://{BASE}/api/me', headers={'authorization': 'Bearer ' + token, 'cf-connecting-ip': '198.19.250.1'})
            except Exception:pass
    f.write(json.dumps(dict(t=time.strftime('%Y-%m-%d %H:%M:%S'), end=True, after_tidy=sample(since))) + '\n')
    print('done', OUT)

asyncio.run(main())
