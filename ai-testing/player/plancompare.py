#!/usr/bin/env python3
"""Haiku against Sonnet on the same saved planner states from scored lives. plancompare.py N. Saves raw text, never rewritten."""
import asyncio, glob, json, os, random, re, statistics as st, sys
import models, prompts
OUT = 'plan_compare.jsonl'
def legal(state, text):
    try:
        j = json.loads(re.search(r'\{.*\}', text or '', re.S).group(0))
    except Exception:
        return False, None
    if j.get('goal') == 'loot':
        return any(c['id'] == j.get('target') for c in state['containers']), j
    return j.get('goal') in ('explore', 'hide', 'treat'), j
async def main(n):
    rows = []
    for f in glob.glob('runs/[SL]_[efg]_*/plan_raw.jsonl'):
        rows += [json.loads(l) for l in open(f)]
    random.Random(5).shuffle(rows); rows = rows[:n]
    with open(OUT, 'a', buffering=1) as out:
        for i, r in enumerate(rows):
            for model in ('claude-haiku-5-5', 'claude-sonnet-5-5'):
                text, ms, cost, err = await models.claude(prompts.PLAN.format(state=json.dumps(r['state'])), model)
                ok, j = legal(r['state'], text)
                out.write(json.dumps(dict(i=i, model=model, ms=round(ms), cost=cost, raw=text, err=err, legal=ok, state=r['state'])) + '\n')
asyncio.run(main(int(sys.argv[1])))
