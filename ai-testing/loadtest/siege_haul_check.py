#!/usr/bin/env python3
"""End-to-end: does a siege's haul reach the survival home's cupboard on a real server?
Against the throwaway siege test server only (container osz-siege-test, SQLite at /tmp/osz-siege-test).
1. new account; 2. a home cupboard written straight into that server's database (the check is about the
haul, not about walking into a building); 3. restart, so the server loads homes; 4. one siege played by the
bot until a chest has been opened, then leave; 5. read the cupboard back from the database.
The account is deleted at the end."""
import asyncio, json, os, random, sqlite3, subprocess, sys, time
import httpx, websockets
sys.path.insert(0, os.path.expanduser('~/osz-stack/tools')); sys.path.insert(0, os.path.expanduser('~/osz-stack/src'))
from siege_sim import Policy
BASE = '127.0.0.1:8140'; DB = '/tmp/osz-siege-test/osz.db'; hdr = {'cf-connecting-ip': '198.18.99.1'}


def up():
    for _ in range(60):
        try:
            if httpx.get(f'http://{BASE}/healthz', timeout=2).status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit('server did not come up')


async def main():
    subprocess.run(['docker', 'start', 'osz-siege-test'], capture_output=True); up()
    r = httpx.post(f'http://{BASE}/api/session', json={'device_id': os.urandom(16).hex(), 'name': 'x'}, headers=hdr).json()
    token, pid = r['token'], r['player']['id']
    home = {'name': 'Test flat', 'lat': 41.8807, 'lng': -87.6278, 'building': 'test', 'floor_level': 0, 'capacity': 40.0,
            'revision': 1, 'items': [{'id': 1, 'code': 'water', 'qty': 1, 'cond': None}], 'next_item': 2, 'receipts': []}
    con = sqlite3.connect(DB); con.execute('insert into player_home (player_id, state) values (?, ?)', (pid, json.dumps(home))); con.commit(); con.close()
    print('home written for player', pid, home['items'])
    subprocess.run(['docker', 'restart', 'osz-siege-test'], capture_output=True); up(); await asyncio.sleep(3)
    pol = Policy(random.Random(5)); body = {}; over = None; opened = 0
    async with websockets.connect(f'ws://{BASE}/ws/siege?token={token}', additional_headers=hdr, max_size=None) as ws:
        t0 = time.time(); mid = 10; last_pos = 0; last_act = 0; picked = None
        while time.time() - t0 < 900:
            m = json.loads(await ws.recv())
            if m.get('t') != 's':
                continue
            body = m.get('body') or body; s = m['siege']
            for e in m.get('ev', []):
                if e.get('e') == 'siege_chest_open':
                    opened += 1
                    print(f"{s['t']:.0f} s: chest opened: {e.get('upgrade_name')}, find {e['qty']} x {e['find_name']}")
            if s.get('over'):
                over = s; break
            if opened and s['haul']:
                await ws.send(json.dumps({'t': 'leave'})); print('leaving at', s['t'], 's with haul', s['haul'])
                break
            if s.get('choice') and picked != s['level']:
                picked = s['level']; mid += 1
                await ws.send(json.dumps({'t': 'act', 'id': mid, 'a': 'siege_pick', 'pick': pol.pick(s['choice'])})); continue
            y = m['you']; now = time.time(); boss = (s.get('boss') or {}).get('id')
            you = {'lat': y['lat'], 'lng': y['lng'], 'hp': y['hp'], 'end': y['end'], 'wounds': body.get('wounds', []),
                   'bandages': sum(i['qty'] for i in body.get('items', []) if i['code'] == 'bandage')}
            zs = [{'id': z[0], 'lat': z[1], 'lng': z[2], 'state': z[3], 'boss': z[0] == boss} for z in m.get('z', [])]
            act, args, target = pol.decide(now, you, zs, s.get('chests') or [], s['arena'], y.get('busy', 0) > .05 or bool(y.get('channel')))
            if target and now - last_pos > .25:
                last_pos = now; await ws.send(json.dumps({'t': 'pos', 'lat': target[0], 'lng': target[1], 'acc': 1, 'mode': 'desk', 'placement_epoch': 1, 'floor_epoch': 0}))
            if act and now - last_act > .3:
                last_act = now; mid += 1; await ws.send(json.dumps({'t': 'act', 'id': mid, 'a': act, **args}))
    if over:
        print('the siege ended before leaving:', over['over'])
    await asyncio.sleep(14)                                       # the hub saves homes every 10 s
    con = sqlite3.connect(DB); state = json.loads(con.execute('select state from player_home where player_id=?', (pid,)).fetchone()[0]); con.close()
    print('cupboard now:', [(i['code'], i['qty']) for i in state['items']], 'revision', state['revision'])
    lines = subprocess.run(['docker', 'logs', '--since', '20m', 'osz-siege-test'], capture_output=True, text=True).stderr
    print([l for l in lines.splitlines() if 'siege over' in l][-1:])
    httpx.delete(f'http://{BASE}/api/me', headers={'authorization': 'Bearer ' + token, **hdr})
    con = sqlite3.connect(DB); print('account rows left:', con.execute('select count(*) from player where id=?', (pid,)).fetchone()[0]); con.close()

asyncio.run(main())
