#!/usr/bin/env python3
"""Draws a death_replay.json top-down as an mp4 for the edit: replay.py RUN_DIR [out.mp4].
Walls, the survivor, every zombie the client was sent (red = holding on), health, and what each layer decided."""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
run = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(run, 'death_replay.mp4')
R = json.load(open(f'{run}/death_replay.json')); F = R['frames']
ev = [json.loads(l) for l in open(f'{run}/events.jsonl')]
t0, t1 = F[0]['t'], F[-1]['t']
acts = [e for e in ev if t0 - 0.5 <= e['wall_ts'] <= t1 + 0.5 and (e['type'] == 'decision' or e['type'] == 'marker')]
W, H, PPM = 1920, 1080, 22.0
font = ImageFont.load_default(size=34); small = ImageFont.load_default(size=26)
def xy(lat, lng, c):
    return (W * 0.42 + (lng - c[1]) * 111320 * math.cos(math.radians(c[0])) * PPM, H / 2 - (lat - c[0]) * 111320 * PPM)
COL = {'engaged': (230, 60, 50), 'down': (150, 150, 150), 'rising': (200, 160, 80), 'stagger': (240, 170, 60), 'chase': (240, 120, 60), 'alert': (240, 200, 60)}
tmp = f'{run}/_replay'; os.makedirs(tmp, exist_ok=True)
fps = 30; n = int((t1 - t0 + 1.5) * fps)
for i in range(n):
    t = t0 + i / fps; f = max((x for x in F if x['t'] <= t), key=lambda x: x['t'], default=F[0])
    y = f['you']; c = (y['lat'], y['lng'])
    im = Image.new('RGB', (W, H), (18, 20, 24)); d = ImageDraw.Draw(im)
    for b in R['buildings']:
        o = b.get('outline') or []
        if len(o) > 2:
            d.polygon([xy(p[0], p[1], c) for p in o], outline=(120, 110, 95), fill=(32, 32, 34))
    for z in f['z']:
        p = xy(z[1], z[2], c); col = COL.get(z[3], (120, 170, 120)) if z[6] else (110, 140, 110)
        d.ellipse([p[0] - 11, p[1] - 11, p[0] + 11, p[1] + 11], fill=col)
    p = xy(*c, c); d.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], fill=(90, 170, 255), outline=(255, 255, 255), width=3)
    sec = (f['game_t'] or t) - (F[-1]['game_t'] or t1)
    d.rectangle([W * 0.72, 0, W, H], fill=(10, 10, 12))
    d.text((W * 0.74, 30), f"health {y['hp']:.0f}   kills {y['kills']}", font=font, fill=(255, 255, 255))
    d.rectangle([W * 0.74, 80, W * 0.74 + 4.2 * max(0, y['hp']), 100], fill=(200, 60, 50))
    d.text((W * 0.74, 120), f"{t - t1:+.1f} s to death   holding on: {sum(1 for z in f['z'] if z[6] and z[3]=='engaged')}", font=small, fill=(200, 200, 200))
    rows = [e for e in acts if e['wall_ts'] <= t][-16:]
    yy = 180
    for e in rows:
        if e['type'] == 'decision':
            s = f"{e['wall_ts'] - t1:+.1f}s {e['layer']} {e['action']} ({e['latency_ms']:.0f} ms)"
        else:
            s = f"{e['wall_ts'] - t1:+.1f}s {e['marker'].upper()} {e.get('part') or ''}"
        d.text((W * 0.74, yy), s, font=small, fill=(255, 210, 120) if e['type'] == 'marker' else (170, 210, 255)); yy += 36
    d.text((20, H - 50), 'Replay from the client log: what the server sent this player in the last 10 s. Blue = survivor, red = zombie holding on.', font=small, fill=(150, 150, 150))
    im.save(f'{tmp}/{i:05d}.png')
FF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'ffmpeg')
subprocess.run(['nice', FF, '-v', 'error', '-y', '-framerate', str(fps), '-i', f'{tmp}/%05d.png', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', out], check=True)
for x in os.listdir(tmp):os.remove(f'{tmp}/{x}')
os.rmdir(tmp); print(out)
