#!/usr/bin/env python3
"""Summarise a soak file: soak_summary.py soak/<file>.jsonl [window_min=15]"""
import json, statistics as st, sys
rows = [json.loads(l) for l in open(sys.argv[1])]; W = int(sys.argv[2]) if len(sys.argv) > 2 else 15
data = [r for r in rows if not r.get('end')]; end = next((r for r in rows if r.get('end')), None)
print(f"{len(data)} minutes, {data[0]['t']} to {data[-1]['t']}")
p95 = [r['ping_p95'] for r in data if r.get('ping_p95') is not None]
print(f"minutes with ping p95 under 500 ms: {sum(1 for x in p95 if x < 500)} of {len(p95)} ({100 * sum(1 for x in p95 if x < 500) / len(p95):.1f}%); worst p95 {max(p95)} ms; median p50 {st.median(r['ping_p50'] for r in data if r.get('ping_p50') is not None)} ms")
print(f"app memory MB: first {data[0].get('app_mem_mb')}, max {max(r.get('app_mem_mb', 0) for r in data)}, last {data[-1].get('app_mem_mb')}; db bytes first {data[0].get('db_bytes')}, last {data[-1].get('db_bytes')}")
tot = lambda k: sum(r.get(k) or 0 for r in data)
print(f"joins {tot('joins')}, leaves {tot('leaves')}, new accounts {tot('new_accounts')}, returning {tot('returning')}, deleted {tot('deleted')}, deaths {tot('deaths')}, new lives {tot('new_lives')}, refused full {tot('refused_full')}")
print(f"app restarts {data[-1].get('app_restarts')} (started {data[-1].get('app_started')}); log error lines {tot('log_errors')}; slow ticks {tot('slow_ticks')}; client errors {sum(sum(r['errors'].values()) for r in data)} {dict(sum((__import__('collections').Counter(r['errors']) for r in data), __import__('collections').Counter()))}")
print('| window | online (mean) | ping p50 median | ping p95 median / worst | app MB (end) | app CPU % (mean) | db MB (end) | players rows | corpses | deaths |')
print('|---|---:|---:|---|---:|---:|---:|---:|---:|---:|')
for i in range(0, len(data), W):
    c = data[i:i + W]
    pp = [r['ping_p95'] for r in c if r.get('ping_p95') is not None]
    print(f"| {c[0]['t'][11:16]} | {st.mean(r['online'] for r in c):.1f} | {st.median(r['ping_p50'] for r in c if r.get('ping_p50') is not None):.0f} | {st.median(pp):.0f} / {max(pp)} | {c[-1].get('app_mem_mb')} | {st.mean(r.get('app_cpu', 0) for r in c):.0f} | {c[-1].get('db_bytes', 0) / 1e6:.2f} | {c[-1].get('players')} | {c[-1].get('corpses')} | {sum(r.get('deaths') or 0 for r in c)} |")
if end: print('after tidy:', {k: end['after_tidy'].get(k) for k in ('players', 'survivors', 'tokens', 'corpses', 'db_bytes', 'app_mem_mb')})
