#!/usr/bin/env python3
"""Records one unscored life in the browser: capture.py CLIP ARM LIMIT_S [loud] [start=chicago].
Keeps footage/CLIP/{clip.mp4, frames.json, events.jsonl, plan_raw.jsonl, summary.json, death_replay.json}.
These lives never count in the arm table: the browser is in the loop."""
import asyncio, json, os, shutil, statistics as st, subprocess, sys, time
import httpx
import core, brain, run, schedule

HERE = os.path.dirname(os.path.abspath(__file__)); FOOT = os.path.join(HERE, '..', 'footage')
FF = os.path.join(HERE, '..', 'tools', 'ffmpeg')


class BrowserTransport:
    def __init__(self, out, start):
        self.out, self.start = out, start; self.token = None; self.p = None; self.stopped = None; self.errors = []

    async def join(self, c):
        self.c = c
        self.p = await asyncio.create_subprocess_exec('node', os.path.join(HERE, 'capture.mjs'), self.out, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=2 ** 24)
        self.reader = asyncio.create_task(self._read())
        await self._cmd(k='begin', start=self.start)

    async def _cmd(self, **o):
        self.p.stdin.write((json.dumps(o) + '\n').encode()); await self.p.stdin.drain()

    async def _read(self):
        while True:
            line = await self.p.stdout.readline()
            if not line:
                self.c.ended = True; return
            j = json.loads(line); k = j.get('k')
            if k == 'ws':
                await self.c.incoming(j['p'])
            elif k == 'token':
                self.token = j['token']
            elif k == 'stopped':
                self.stopped = j
            elif k in ('error', 'pageerror', 'lowmem'):
                self.errors.append(j); self.c.log('capture_' + k, m=j.get('m'), on=j.get('on'))
                if k == 'lowmem':
                    self.c.ended = True

    async def send(self, m):
        if m['t'] == 'pos':
            await self._cmd(k='goal', p=[m['lat'], m['lng']])
        elif m['t'] == 'act':
            args = {k: v for k, v in m.items() if k not in ('t', 'id', 'a')}
            if m['a'] == 'route':
                args['nav'] = -1          # the page ignores this answer; the agent follows the route itself
            await self._cmd(k='fire', a=m['a'], args=args)

    async def leave(self, c):
        await asyncio.sleep(4.0)          # hold on the death card or the last frame
        await self._cmd(k='stop')
        try:
            await asyncio.wait_for(self.p.wait(), 60)
        except asyncio.TimeoutError:
            self.p.kill()
        await asyncio.sleep(0.2)
        if self.token:
            async with httpx.AsyncClient(timeout=30) as http:
                await http.delete(f'http://{core.BASE}/api/me', headers={'authorization': 'Bearer ' + self.token, 'cf-connecting-ip': '198.18.78.1'})


def encode(out):
    fj = json.load(open(f'{out}/frames.json')); fr = fj['frames']
    if len(fr) < 2:
        return dict(frames=len(fr))
    with open(f'{out}/concat.txt', 'w') as f:
        for a, b in zip(fr, fr[1:]):
            f.write(f"file 'frames/{a['file']}'\nduration {max(0.001, b['t'] - a['t']):.4f}\n")
        f.write(f"file 'frames/{fr[-1]['file']}'\n")
    subprocess.run(['nice', '-n', '15', FF, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'concat.txt', '-vf', 'fps=60,scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-threads', '3', 'clip.mp4'], cwd=out, check=True)
    gaps = sorted(b['t'] - a['t'] for a, b in zip(fr, fr[1:]))
    dur = fr[-1]['t'] - fr[0]['t']
    info = dict(frames=len(fr), seconds=round(dur, 1), mean_fps=round(len(fr) / dur, 1), gap_p50_ms=round(gaps[len(gaps) // 2] * 1000), gap_p95_ms=round(gaps[int(len(gaps) * .95)] * 1000), gap_max_ms=round(gaps[-1] * 1000), first_frame_wall_ts=fr[0]['t'], last_frame_wall_ts=fr[-1]['t'], mp4='clip.mp4 (constant 60 fps; frames repeated to hold the real capture timing, see mean_fps)', mp4_mb=round(os.path.getsize(f'{out}/clip.mp4') / 1e6, 1))
    json.dump(info, open(f'{out}/capture_info.json', 'w'), indent=1)
    shutil.rmtree(f'{out}/frames'); os.remove(f'{out}/concat.txt')
    return info


async def main():
    clip, arm, limit = sys.argv[1], sys.argv[2], float(sys.argv[3]); loud = 'loud' in sys.argv
    start = next((a[6:] for a in sys.argv if a.startswith('start=')), 'chicago')
    out = os.path.abspath(os.path.join(FOOT, clip)); os.makedirs(out, exist_ok=True)
    if schedule.avail() < 2048:
        print('under 2 GB available; not recording'); return
    if 'noreset' not in sys.argv:
        schedule.reset()
    # the timing panel for other models needs real states: keep a sample of what FAST was asked
    orig = brain.Agent.state_for_model; sample = open(f'{HERE}/state_samples.jsonl', 'a', buffering=1)

    def sampled(self, s):
        st8 = orig(self, s)
        if s.zs or int(time.time()) % 10 == 0:
            sample.write(json.dumps({'state': st8, 'legal': self.legal(s)}) + '\n')
        return st8
    brain.Agent.state_for_model = sampled
    t = BrowserTransport(out, start)
    s = await run.life(arm, clip, limit, out=out, start=start, transport=t, loud=loud)
    print(json.dumps({k: s[k] for k in ('lived_s', 'died', 'cause', 'hit_dmg', 'hp_lost', 'met', 'kills', 'containers', 'fast_calls', 'fast_p50', 'plan_calls')}))
    print('browser errors', t.errors[:5])
    print(json.dumps(encode(out)))

if __name__ == '__main__':
    asyncio.run(main())
