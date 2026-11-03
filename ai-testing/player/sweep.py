#!/usr/bin/env python3
"""Difficulty sweep: many five-minute lives on several throwaway servers at once.

Each worker owns one container from the osz-sweep image, on its own loopback port, with a fresh
SQLite copy of the template (the cached Chicago and Minneapolis map regions, nothing else) for every
life, so every life meets the same day's zombies, like the reset in schedule.py. The containers
cannot reach OpenStreetMap: both map hosts resolve to 127.0.0.1 inside them.

sweep.py PLAN.json [workers]    PLAN is a list of {"setting": name, "dials": {...}, "arm": "b", "tag": "..."}
Lives with a summary.json are skipped, so a stopped sweep resumes where it was.
"""
import json, os, queue, shutil, subprocess, sys, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, 'sweep_runs'); ROOT = '/tmp/osz-sweep'; PAUSE = os.path.join(HERE, 'PAUSE')
LIMIT = 300
LOG = open(os.path.join(HERE, 'sweep.log'), 'a', buffering=1); lock = threading.Lock()
def say(*a):
    with lock:LOG.write(time.strftime('%H:%M:%S ') + ' '.join(map(str, a)) + '\n')
def avail():
    return int(open('/proc/meminfo').read().split('MemAvailable:')[1].split()[0]) // 1024
def gate():
    while os.path.exists(PAUSE) or avail() < 2048:
        say('paused', 'file' if os.path.exists(PAUSE) else f'memory {avail()} MB'); time.sleep(30)
def server(k, dials, image='osz-sweep:latest', extra_env=None):
    name, port, d = f'osz-sweep-{k}', 8131 + k, f'{ROOT}/w{k}'
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d); os.chmod(d, 0o777)
    shutil.copy(f'{ROOT}/template/osz.db', f'{d}/osz.db')
    env = dict(ENV='dev', DATABASE_URL='sqlite+aiosqlite:////data/osz.db', SECRET_KEY='sweep-not-public-0123456789', REAL_GPS='0', FREE_TEXT='0',
               TRUST_PROXY='cloudflare', OSZ_OVERPASS_URL='http://127.0.0.1:9/', MAX_PLAYERS='30', DIFFICULTY='classic', DIFFICULTY_TUNE=json.dumps(dials), **(extra_env or {}))
    cmd = ['docker', 'run', '-d', '--name', name, '--user', '1000:1000', '--cpus', '1', '--memory', '448m', '--memory-swap', '448m',
           '-v', f'{d}:/data', '--add-host', 'overpass-api.de:127.0.0.1', '--add-host', 'api.openstreetmap.org:127.0.0.1', '-p', f'127.0.0.1:{port}:8000']
    for a, b in env.items():cmd += ['-e', f'{a}={b}']
    r = subprocess.run(cmd + [image], capture_output=True, text=True)
    if r.returncode:say('docker run failed', k, r.stderr[:300]); return None
    for _ in range(60):
        c = subprocess.run(['curl', '-s', '-m', '2', '-o', '/dev/null', '-w', '%{http_code}', f'http://127.0.0.1:{port}/healthz'], capture_output=True, text=True).stdout
        if c == '200':time.sleep(1); return port
        time.sleep(1)
    say('server did not come up', k); return None
def worker(k, q):
    while True:
        if os.path.exists(os.path.join(HERE, 'STOP')):return        # finish the life in hand, start no more
        try:job = q.get_nowait()
        except queue.Empty:return
        gate(); out = os.path.join(RUNS, job['tag'])
        if os.path.exists(f'{out}/summary.json'):continue
        shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
        json.dump(job, open(f'{out}/setting.json', 'w'))
        port = server(k, job['dials'], image=job.get('image', 'osz-sweep:latest'))
        if not port:q.put(job); time.sleep(10); continue
        t0 = time.time()
        r = subprocess.run([sys.executable, 'run.py', job['arm'], job['tag'], str(job.get('limit', LIMIT))], cwd=HERE, capture_output=True, text=True,
                           timeout=job.get('limit', LIMIT) + 180, env=dict(os.environ, BASE=f'127.0.0.1:{port}', OSZ_RUNS=RUNS))
        logs = subprocess.run(['docker', 'logs', f'osz-sweep-{k}'], capture_output=True, text=True)
        open(f'{out}/server.log', 'w').write(logs.stdout + logs.stderr)
        try:
            d = json.loads(r.stdout.strip().splitlines()[-1])
            say(f'w{k}', job['tag'], 'lived', d['lived_s'], 'died', d['died'], 'dmg', d['hit_dmg'], 'met', d['met'], 'kills', d['kills'], 'containers', d['containers'], 'took', round(time.time() - t0))
        except Exception:
            say(f'w{k}', job['tag'], 'FAILED', r.stdout[-200:], r.stderr[-400:])
        subprocess.run(['docker', 'rm', '-f', f'osz-sweep-{k}'], capture_output=True)
def main():
    plan = json.load(open(sys.argv[1])); n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    q = queue.Queue()
    for j in plan:q.put(j)
    say('sweep start', sys.argv[1], len(plan), 'lives', n, 'workers')
    ts = [threading.Thread(target=worker, args=(k, q)) for k in range(n)]
    for t in ts:t.start(); time.sleep(3)
    for t in ts:t.join()
    say('sweep finished', sys.argv[1])
if __name__ == '__main__':
    main()
