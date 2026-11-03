#!/usr/bin/env python3
"""Times models in the FAST seat on real game states saved from a live life. panel.py MODEL N. At most 30 calls each."""
import asyncio, json, os, re, subprocess, sys, time, statistics as st
import httpx
import models, prompts
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'panel_results.jsonl'), 'a', buffering=1)
rows = [json.loads(l) for l in open('state_samples.jsonl')]
step = max(1, len(rows) // 30)
rows = [r for r in rows if len(r['legal']) > 1][::step]
def parse(text, legal):
    w = re.sub(r'[^a-z]', '', (text or '').strip().lower().split()[0]) if (text or '').strip() else ''
    return w if w in legal else None
def record(model, i, ms, choice, ok, usd=0.0, note=None, legal=None):
    OUT.write(json.dumps(dict(model=model, i=i, ms=round(ms, 1), choice=choice, ok=ok, usd=usd, note=note, legal=legal)) + '\n')
async def jev(n):
    j = models.Jev('panel')
    for i, r in enumerate(rows[:n]):
        ans, ms, tk = await j.ask(r['state'], prompts.tactic_question(r['legal']))
        record('jev', i, ms, ans['tactic']['choice'], True, tk * models.USD_PER_TOKEN, j.version, r['legal'])
async def haiku(n, model='claude-haiku-5-5'):
    for i, r in enumerate(rows[:n]):
        text, ms, cost, err = await models.claude(prompts.slow_prompt(r['state'], r['legal']), model)
        c = parse(text, r['legal']); record(model, i, ms, c, c is not None, cost, err or (None if c else (text or '')[:60]), r['legal'])
async def qwen(n, port=18082):
    async with httpx.AsyncClient(timeout=60) as c:
        for i, r in enumerate(rows[:n]):
            t0 = time.perf_counter()
            x = await c.post(f'http://127.0.0.1:{port}/v1/chat/completions', json=dict(model='qwen3-coder-30b', messages=[dict(role='user', content=prompts.slow_prompt(r['state'], r['legal']))], max_tokens=8, temperature=0))
            ms = (time.perf_counter() - t0) * 1000
            d = x.json(); text = d['choices'][0]['message']['content']; ch = parse(text, r['legal'])
            record('qwen3-coder-30b@local-gpu', i, ms, ch, ch is not None, 0.0, json.dumps(d.get('timings', {}).get('prompt_ms')) if not ch else text[:40], r['legal'])
            await asyncio.sleep(0.3)
def codex(n):
    for i, r in enumerate(rows[:n]):
        t0 = time.perf_counter()
        p = subprocess.run(['codex', 'exec', '--skip-git-repo-check', '--sandbox', 'read-only', '--ephemeral', '-c', 'model_reasoning_effort="low"', '-c', 'service_tier="priority"', '-'], input=prompts.slow_prompt(r['state'], r['legal']), capture_output=True, text=True, timeout=180, cwd='/tmp/oszplan')
        ms = (time.perf_counter() - t0) * 1000
        lines = [l for l in p.stdout.strip().splitlines() if l.strip()]; ch = parse(lines[-1] if lines else '', r['legal'])
        record('codex-low-priority', i, ms, ch, ch is not None, None, (p.stderr[-160:] if not ch else None), r['legal'])
if __name__ == '__main__':
    m, n = sys.argv[1], int(sys.argv[2])
    if m == 'codex':codex(n)
    else:asyncio.run({'jev': jev, 'haiku': haiku, 'qwen': qwen}[m](n))
