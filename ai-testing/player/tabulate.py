#!/usr/bin/env python3
"""The arm table, rewritten after every life, and spliced into REPORT.md between its markers."""
import glob, json, os, random, re, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {'a': 'a floor: random legal actions', 'b': 'b scripts alone', 'c': 'c scripts + Jev', 'd': 'd scripts + slow seat (Haiku)', 'e': 'e scripts + goals (Haiku)', 'f': 'f full stack: Haiku + Jev + scripts', 'g': 'g full stack: Sonnet + Jev + scripts'}
def load(prefix):
    out = {}
    for f in sorted(glob.glob(f'{HERE}/runs/{prefix}_*/summary.json')):
        s = json.load(open(f)); out.setdefault(s['arm'], []).append(s)
    return out
def pct(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else None
def lat(tag):
    rows = []
    for l in open(f'{HERE}/runs/{tag}/events.jsonl'):
        d = json.loads(l)
        if d.get('type') == 'decision' and d.get('layer') == 'FAST':rows.append(d['latency_ms'])
        elif d.get('type') == 'stale_decision':rows.append(d['latency_ms'])
    return rows
def dmg_rate(L):
    met = sum(s['met'] for s in L); return sum(s['hit_dmg'] for s in L) / met if met else float('nan')
def table(by):
    head = '| arm | lives | deaths | median s alive (cap 300) | zombie-hit dmg per zombie met | zombies met per life | all health lost per life | kills per life | containers per life | mission | FAST calls/s in sight | FAST p50 / p95 ms | stale % | $ per hour |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    rows = [head]
    for k in sorted(by):
        L = by[k]; n = len(L); hours = sum(s['lived_s'] for s in L) / 3600 or 1
        lats = [x for s in L for x in lat(s['tag'])]
        fr, sl = sum(s['fast_fresh'] for s in L), sum(s['fast_stale'] for s in L)
        sight = sum(s.get('sight_s', 0) for s in L)
        rows.append('| {} | {} | {} | {:.0f} | {:.1f} | {:.1f} | {:.1f} | {:.1f} | {:.1f} | {}/{} | {} | {} | {} | {} |'.format(
            NAMES[k], n, sum(s['died'] for s in L), st.median(s['lived_s'] for s in L), dmg_rate(L), st.mean(s['met'] for s in L), st.mean(s['hp_lost'] for s in L), st.mean(s['kills'] for s in L), st.mean(s['containers'] for s in L), sum(s['mission'] for s in L), n,
            f"{sum(s.get('sight_calls', 0) for s in L) / sight:.1f}" if sight and k in 'cdfg' else '-',
            f"{pct(lats, .5):.0f} / {pct(lats, .95):.0f}" if lats else '-',
            f"{100 * sl / (fr + sl):.0f}" if fr + sl else '-',
            f"{(sum(s['jev_usd'] + s['plan_cost'] for s in L)) / hours:.2f}"))
    return '\n'.join(rows)
def boot(A, B, fn, n=4000, seed=7):
    r = random.Random(seed); out = []
    for _ in range(n):
        a = [r.choice(A) for _ in A]; b = [r.choice(B) for _ in B]
        x, y = fn(a), fn(b)
        if x == x and y == y:out.append(x - y)
    out.sort()
    return (out[int(len(out) * .05)], out[int(len(out) * .95)]) if out else (float('nan'), float('nan'))
def compare(by, x, y):
    """Bar 2: is x better than y?"""
    if x not in by or y not in by:return None
    X, Y = by[x], by[y]
    cont = lambda L: st.mean(s['containers'] for s in L)
    dx, dy = dmg_rate(X), dmg_rate(Y); cx, cy = cont(X), cont(Y)
    per10 = lambda L: 10 * sum(s['died'] for s in L) / len(L)
    d_ci = boot(X, Y, dmg_rate); c_ci = boot(X, Y, cont)
    better_d = dy > 0 and dx <= .75 * dy and d_ci[1] < 0
    better_c = cx >= 1.25 * cy and c_ci[0] > 0
    better_m = per10(Y) - per10(X) >= 2
    worse_d = dy >= 0 and dx >= 1.25 * dy and dx > 0 and d_ci[0] > 0
    worse_c = cy > 0 and cx <= .75 * cy and c_ci[1] < 0
    worse_m = per10(X) - per10(Y) >= 2
    verdict = 'helps' if (better_d or better_c or better_m) and not (worse_d or worse_c or worse_m) else ('hurts' if (worse_d or worse_c or worse_m) and not (better_d or better_c or better_m) else ('mixed' if (better_d or better_c or better_m) else 'no measurable benefit'))
    return f"| {x} vs {y} | {len(X)} / {len(Y)} | {dx:.2f} vs {dy:.2f} | [{d_ci[0]:.2f}, {d_ci[1]:.2f}] | {cx:.1f} vs {cy:.1f} | [{c_ci[0]:.1f}, {c_ci[1]:.1f}] | {per10(X):.0f} vs {per10(Y):.0f} | **{verdict}** |"
def main():
    by = load('S'); loud = load('L')
    txt = '### Primary: natural play, Chicago, 300 s limit\n\n' + table(by) + '\n\n'
    txt += '### Bar 2: does a layer help?\n\n| comparison | lives | dmg per zombie met | 90% CI of difference | containers | 90% CI of difference | deaths per 10 | verdict |\n|---|---|---|---|---|---|---|---|\n'
    for x, y in (('b', 'a'), ('c', 'b'), ('e', 'b'), ('f', 'b'), ('f', 'c'), ('f', 'e')):
        r = compare(by, x, y)
        if r:txt += r + '\n'
    if loud:
        txt += '\n### Secondary: "loud" scenario, screaming every 15 s after 40 s\n\n' + table(loud) + '\n\n| comparison | lives | dmg per zombie met | 90% CI of difference | containers | 90% CI of difference | deaths per 10 | verdict |\n|---|---|---|---|---|---|---|---|\n'
        for x, y in (('c', 'b'), ('e', 'b'), ('f', 'b'), ('f', 'c'), ('f', 'e')):
            r = compare(loud, x, y)
            if r:txt += r + '\n'
    open(f'{HERE}/arm_table.md', 'w').write(txt)
    rp = os.path.join(HERE, '..', 'REPORT.md')
    if os.path.exists(rp):
        s = open(rp).read()
        s2 = re.sub(r'<!-- ARM TABLE -->.*?<!-- /ARM TABLE -->', lambda m: '<!-- ARM TABLE -->\n' + txt + '\n<!-- /ARM TABLE -->', s, flags=re.S)
        if s2 != s:open(rp, 'w').write(s2)
if __name__ == '__main__':
    main()
