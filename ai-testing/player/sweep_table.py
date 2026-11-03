#!/usr/bin/env python3
"""The sweep table: one row per setting and arm, from each life's summary.json and events.jsonl.
sweep_table.py [prefix ...]  ->  prints markdown, and writes ../SWEEP.md when run with --write."""
import glob, json, os, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__)); RUNS = os.path.join(HERE, 'sweep_runs')
def lives(prefixes):
    out = {}
    for f in sorted(glob.glob(f'{RUNS}/*/summary.json')):
        tag = os.path.basename(os.path.dirname(f))
        if tag.startswith('smoke') or (prefixes and not any(tag.startswith(p) for p in prefixes)):continue
        s = json.load(open(f)); job = json.load(open(f'{os.path.dirname(f)}/setting.json'))
        s['setting'] = job['setting']; s['dials'] = job['dials']; s['minutes'] = per_minute(os.path.dirname(f))
        out.setdefault((job['setting'], s['arm']), []).append(s)
    return out
def per_minute(d):
    """zombies met and zombie-hit damage in each minute of the life."""
    met = [0] * 5; dmg = [0.0] * 5
    for l in open(f'{d}/events.jsonl'):
        e = json.loads(l)
        if e.get('type') != 'marker' or e.get('life_s') is None:continue
        m = min(4, int(e['life_s'] // 60))
        if e['marker'] == 'zombie_met':met[m] += 1
        elif e['marker'] in ('hit', 'bite'):dmg[m] += e.get('dmg') or 0
    return dict(met=met, dmg=dmg)
def row(name, arm, L):
    n = len(L); deaths = [s for s in L if s['died']]; met = sum(s['met'] for s in L)
    early = sum(1 for s in L if s['died'] and s['lived_s'] < 60)
    first = st.mean(s['minutes']['dmg'][0] for s in L)
    m12 = sum(s['minutes']['met'][0] + s['minutes']['met'][1] for s in L); m45 = sum(s['minutes']['met'][3] + s['minutes']['met'][4] for s in L)
    d12 = sum(s['minutes']['dmg'][0] + s['minutes']['dmg'][1] for s in L); d45 = sum(s['minutes']['dmg'][3] + s['minutes']['dmg'][4] for s in L)
    # minutes 4-5 are only lived by those still alive: per surviving-life-minute rates
    alive45 = sum(max(0, min(120, s['lived_s'] - 180)) for s in L) / 60 or 1e-9; alive12 = sum(min(120, s['lived_s']) for s in L) / 60
    ttd = ', '.join(f"{s['lived_s']:.0f}" for s in sorted(deaths, key=lambda s: s['lived_s'])) or '-'
    return (f"| {name} | {arm} | {n} | {len(deaths)} ({100 * len(deaths) / n:.0f}%) | {ttd} | {early} | "
            f"{(sum(s['hit_dmg'] for s in L) / met) if met else float('nan'):.1f} | {met / n:.1f} | {st.mean(s['hp_lost'] for s in L):.0f} | {first:.1f} | "
            f"{m12 / alive12:.2f} → {m45 / alive45:.2f} | {d12 / alive12:.1f} → {d45 / alive45:.1f} | {st.mean(s['containers'] for s in L):.1f} |")
HEAD = ('| setting | arm | lives | deaths | seconds at death | deaths < 60 s | zombie-hit dmg per zombie met | zombies met per life | all health lost per life | hit dmg in first 60 s | met per minute, min 1-2 → 4-5 | hit dmg per minute, min 1-2 → 4-5 | containers |\n'
        '|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|---:|')
def table(prefixes=()):
    by = lives(prefixes); rows = [HEAD]
    for (name, arm) in sorted(by, key=lambda k: (k[0], k[1])):
        rows.append(row(name, arm, by[(name, arm)]))
    return '\n'.join(rows), by
if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    txt, by = table(args)
    print(txt)
    print()
    for (name, arm), L in sorted(by.items()):
        print(name, arm, json.dumps(L[0]['dials']))
