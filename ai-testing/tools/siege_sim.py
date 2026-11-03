"""Tune siege mode offline: a scripted survivor plays SiegeRuns in simulated time, as fast as the CPU goes.
The same policy plays over the real socket in loadtest/siege_bots.py; this one only skips the network.

  ~/venvs/osz/bin/python siege_sim.py RUNS [--scale X] [--hp a,b] [--json out.jsonl] [--seed N]
Prints each run's end time, cause, kills, level, peak alive, and the spread against the bar."""
import argparse, json, math, os, random, sqlite3, sys, time
sys.path.insert(0, os.environ.get('OSZ_SRC', '../src'))
from app.game import siege
from app.game.sim import dist_m, shift, delta_m

M = 111320.0
PRIORITY = ['wind', 'arc', 'heavy', 'jacket', 'quick', 'mend', 'weapon', 'bandage', 'charge', 'breath', 'feet']


def records():
    db = sqlite3.connect('/tmp/osz-sweep/template/osz.db')
    row = db.execute('select records from building_region where id=?', (siege.ARENA['region'],)).fetchone()
    return json.loads(row[0])


class Policy:
    """Reflex rules, the same in both harnesses. Sees a frame-like dict: you, zombies, chests, choice."""
    def __init__(self, rng):
        self.rng = rng; self.next_move = 0.0

    def pick(self, choice):
        ids = [c['id'] for c in choice]
        return min(range(len(ids)), key=lambda i: PRIORITY.index(ids[i]) if ids[i] in PRIORITY else 99)

    def decide(self, now, you, zs, chests, arena, busy):
        """Returns (action or None, args, move target or None). The survival bot's lesson: let it come,
        swing when it arrives, shove what has hold of you, finish what is on the ground."""
        p = (you['lat'], you['lng'])
        near = sorted(((dist_m(p[0], p[1], z['lat'], z['lng']), z) for z in zs), key=lambda x: x[0])
        on_me = [z for d, z in near if z.get('state') == 'engaged']
        act = None; args = {}
        bleeding = [w for w in you.get('wounds', []) if w.get('bleeding') and not w.get('bandaged')]
        if not busy:
            down = next((z for d, z in near if d <= 5.0 and z.get('state') in ('down', 'rising')), None)
            stag = next((z for d, z in near if d <= 3.3 and z.get('state') == 'stagger'), None)
            if down:
                act, args = 'swing', {'target': down['id']}
            elif on_me and you.get('end', 100) >= 8 and not all(z.get('boss') for z in on_me):
                act = 'shove'
            elif stag:
                act, args = 'swing', {'target': stag['id']}
            elif near and near[0][0] <= 3.3:
                act, args = 'swing', {'target': near[0][1]['id']}
            elif bleeding and you.get('bandages', 0) > 0 and not (near and near[0][0] < 5.0) and (you['hp'] < 75 or len(bleeding) >= 2):
                act, args = 'bandage', {'wound': bleeding[0]['id']}
        if act == 'bandage':
            return act, args, (p[0], p[1])
        crowd = [z for d, z in near if d < 6.0]
        others = [z for d, z in near if d < 9.0 and not z.get('boss')]
        boss_near = any(z.get('boss') and d < 9.0 for d, z in near) and len(others) >= 2
        target = None
        if boss_near or len(crowd) >= 3:
            ex = ny = 0.0
            for d, z in near:
                if d < 14.0:
                    dx, dy = delta_m(z['lat'], z['lng'], p[0], p[1])
                    wgt = (3.0 if z.get('boss') else 1.0) / max(1.0, d) ** 2
                    ex += dx / max(d, .1) * wgt; ny += dy / max(d, .1) * wgt
            cx, cy = delta_m(p[0], p[1], arena['lat'], arena['lng']); dc = math.hypot(cx, cy) or 1
            if dc > arena['r'] - 8:
                ex += cx / dc * 0.08; ny += cy / dc * 0.08
            mag = math.hypot(ex, ny)
            if mag > 1e-6:
                target = shift(p[0], p[1], ex / mag * 3.0, ny / mag * 3.0)
        elif chests and not (near and near[0][0] < 8.0):
            c = min(chests, key=lambda c: dist_m(p[0], p[1], c[1], c[2]))
            target = (c[1], c[2])
        elif near and near[0][0] < 15.0:
            target = (p[0], p[1])                       # hold still: let it come
        else:
            target = (arena['lat'], arena['lng'])
        return act, args, target


def frame_of(run):
    a = run.actor; w = run.world
    zs = [{'id': z.id, 'lat': z.lat, 'lng': z.lng, 'state': z.state, 'boss': bool(z.boss)} for z in w.zeds.values() if z.alive]
    you = {'lat': a.lat, 'lng': a.lng, 'hp': a.hp, 'end': a.end, 'wounds': a.wounds, 'bandages': a.count('bandage')}
    return you, zs, [[c['id'], c['lat'], c['lng'], c['kind']] for c in run.chests]


def play(seed, recs, waves=None, bosses=None, reflex_s=0.25, log=None, rate=None, delay=0.0):
    rng = random.Random(seed)
    run = siege.SiegeRun(1, 'Bot', recs, seed=seed, waves=waves, bosses=bosses, spawn_per_s=rate)
    pol = Policy(rng); dt = 0.2; next_think = 0.0; t0 = time.perf_counter(); ticks = 0; seen = []
    while not run.over:
        if run.choice:
            run.pick(pol.pick([{'id': k} for k in run.choice]))
        run.step(dt); ticks += 1
        if run.over:
            break
        snap = (run.t, frame_of(run), run.world.now < run.actor.busy_until - 0.05 or bool(run.actor.channel))
        seen.append(snap)
        while delay and len(seen) > 1 and run.t - seen[1][0] >= delay:   # what the socket bot sees: a frame `delay` old
            seen.pop(0)
        if run.t >= next_think:
            next_think = run.t + reflex_s
            (you, zs, chests), busy = (seen[0][1], seen[0][2]) if delay else (snap[1], snap[2])
            act, args, target = pol.decide(run.t, you, zs, chests, run.arena, busy)
            if target:
                lat, lng = run.clamp(*target)
                run.world.set_position(run.actor.id, lat, lng, 1.0)
            if act:
                run.world.act(run.actor.id, act, **args)
    o = run.over
    return dict(seed=seed, result=o['result'], t=o['t'], cause=o.get('cause'), kills=o['kills'], level=o['level'],
                bosses=o['bosses'], score=o['score'], peak=run.peak_alive, chests=len(o['haul']),
                taken=run.taken, ms_per_tick=round(1000 * (time.perf_counter() - t0) / max(1, ticks), 2))


def summary(rows):
    n = len(rows); ts = sorted(r['t'] for r in rows)
    before10 = sum(1 for r in rows if r['result'] == 'dead' and r['t'] < 600)
    full = sum(1 for r in rows if r['result'] == 'extracted')
    blocks = [0] * 7
    for r in rows:
        blocks[6 if r['result'] == 'extracted' else min(5, int(r['t'] // 300))] += 1
    ok = before10 <= n / 2 and full < n / 5 and sum(1 for b in blocks[:6] if b) >= 4
    return (f"{n} runs: dead before 10:00 {before10} ({100*before10/n:.0f}%), reached 30:00 {full} ({100*full/n:.0f}%), "
            f"deaths by 5-min block {blocks[:6]}, median end {ts[n//2]/60:.1f} min -> bar {'PASS' if ok else 'FAIL'}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', type=int); ap.add_argument('--scale', type=float); ap.add_argument('--hp')
    ap.add_argument('--bosshp', type=float, default=1.0); ap.add_argument('--bossdmg', type=float, default=1.0); ap.add_argument('--json'); ap.add_argument('--ramp'); ap.add_argument('--rate', type=float); ap.add_argument('--speed'); ap.add_argument('--delay', type=float, default=0.0); ap.add_argument('--seed', type=int, default=1)
    o = ap.parse_args()
    waves = siege.build_waves(scale=o.scale, hp_ramp=tuple(map(float, o.hp.split(','))) if o.hp else None,
                              floor_ramp=tuple(map(float, o.ramp.split(','))) if o.ramp else None,
                              speed_ramp=tuple(map(float, o.speed.split(','))) if o.speed else None)
    bosses = [dict(b, hp=round(b['hp'] * o.bosshp), dmg=round(b['dmg'] * o.bossdmg, 3)) for b in siege.BOSSES]
    recs = records(); rows = []
    for i in range(o.runs):
        r = play(o.seed + i, recs, waves, bosses, rate=o.rate, delay=o.delay); rows.append(r)
        print(json.dumps(r), flush=True)
        if o.json:
            open(o.json, 'a').write(json.dumps(dict(r, scale=o.scale or siege.SCALE, hp=o.hp, bosshp=o.bosshp, bossdmg=o.bossdmg, ramp=o.ramp, rate=o.rate, speed=o.speed, delay=o.delay)) + '\n')
    print(summary(rows))
