#!/usr/bin/env python3
"""Runs the scored lives one at a time, in shuffled blocks, resetting the world between lives."""
import json, os, random, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); STACK = os.path.dirname(HERE)
PAUSE = f'{HERE}/PAUSE'; LOG = open(f'{HERE}/schedule.log', 'a', buffering=1)
LIMIT = 300
def say(*a):
    LOG.write(time.strftime('%H:%M:%S ') + ' '.join(map(str, a)) + '\n')
def avail():
    return int(open('/proc/meminfo').read().split('MemAvailable:')[1].split()[0]) // 1024
def sh(*a, **k):
    return subprocess.run(a, cwd=STACK, capture_output=True, text=True, **k)
def reset():
    sh('docker', 'compose', 'stop', 'app')
    q = 'delete from zed_dead; delete from world_corpse; delete from building_opening; delete from world_events;'
    r = sh('docker', 'compose', 'exec', '-T', 'db', 'psql', '-U', 'osz', '-d', 'osz', '-qc', q)
    if r.returncode:say('reset sql failed', r.stderr[:200])
    sh('docker', 'compose', 'up', '-d', 'app')
    for _ in range(90):
        if sh('curl', '-s', '-m', '2', '-o', '/dev/null', '-w', '%{http_code}', 'http://127.0.0.1:8120/healthz').stdout == '200':
            time.sleep(2); return True
        time.sleep(1)
    say('app did not come back'); return False
def gate():
    while os.path.exists(PAUSE) or avail() < 2048:
        say('paused', 'file' if os.path.exists(PAUSE) else f'memory {avail()} MB'); time.sleep(30)
def one(arm, tag, loud=False):
    gate()
    if os.path.exists(f'{HERE}/runs/{tag}/summary.json'):return
    if not reset():return
    t0 = time.time()
    r = subprocess.run([sys.executable, 'run.py', arm, tag, str(LIMIT)] + (['loud'] if loud else []), cwd=HERE, capture_output=True, text=True, timeout=LIMIT + 120)
    try:
        d = json.loads(r.stdout.strip().splitlines()[-1])
        say(tag, 'lived', d['lived_s'], 'died', d['died'], 'dmg', d['hit_dmg'], 'met', d['met'], 'kills', d['kills'], 'containers', d['containers'], 'took', round(time.time() - t0))
    except Exception:
        say(tag, 'FAILED', r.stdout[-200:], r.stderr[-400:])
    subprocess.run([sys.executable, 'tabulate.py'], cwd=HERE, capture_output=True)
def main():
    rng = random.Random(20261102)
    for block in range(10):
        order = ['a', 'b', 'c', 'e', 'f']
        if block in (1, 3, 5, 7): order += ['d', 'g']
        rng.shuffle(order)
        loud = ['b', 'c', 'e', 'f']; rng.shuffle(loud)
        say('block', block, order, 'loud', loud)
        for arm in order:
            one(arm, f'S_{arm}_{block:02d}')
        for arm in loud:
            one(arm, f'L_{arm}_{block:02d}', loud=True)
    say('all finished')
if __name__ == '__main__':
    main()
