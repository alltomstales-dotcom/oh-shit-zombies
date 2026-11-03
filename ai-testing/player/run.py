#!/usr/bin/env python3
"""One life. run.py ARM TAG [limit_s]. Arms: a floor, b scripts, c scripts+Jev, d scripts+slow seat, e scripts+goals, f full stack, g full stack with Sonnet goals."""
import asyncio, json, os, statistics as st, sys, time
import httpx
from core import Client, Log
from brain import Agent
import models

ARMS = {'a': dict(seat='random'), 'b': dict(seat='rule'), 'c': dict(seat='jev'), 'd': dict(seat='slow'),
        'e': dict(seat='rule', planner='claude-haiku-5-5'), 'f': dict(seat='jev', planner='claude-haiku-5-5'), 'g': dict(seat='jev', planner='claude-sonnet-5-5')}


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p))], 1) if xs else None


async def life(arm, tag, limit, out=None, start='chicago', transport=None, loud=False):
    cfg = ARMS[arm]
    d = out or os.path.join(os.environ.get('OSZ_RUNS') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runs'), tag)
    log = Log(d); c = Client(log, start=start, limit=limit, transport=transport)
    a = Agent(c, arm, log, planner_model=cfg.get('planner'), seat=cfg['seat'], loud=loud)
    if cfg['seat'] == 'jev':
        a.jev = models.Jev(tag)
    if cfg['seat'] == 'slow':
        a.slow_model = 'claude-haiku-5-5'
    log('life_start', arm=arm, tag=tag, limit=limit, start=start, reflex_delay_s=0.25, loud=loud)
    async with httpx.AsyncClient(timeout=30) as http:
        await c.join(http)
        for _ in range(600):
            if c.placed_at or c.ended:
                break
            await asyncio.sleep(0.05)
        run = asyncio.create_task(a.run())
        await run
        await asyncio.sleep(0.2)
        m = c.m; f = a.decisions
        lived = (m.get('died_at') or time.time()) - (c.placed_at or time.time())
        fast_decisions = f['fast']
        s = dict(arm=arm, tag=tag, limit=limit, wall_start=c.placed_at, lived_s=round(lived, 1), died=c.dead, cause=(c.death or {}).get('cause'), by=(c.death or {}).get('by'), infected=(c.death or {}).get('infected'),
                 loud=loud, hit_dmg=round(m['hit_dmg'], 1), hp_lost=round(m['hp_lost'], 1), min_hp=m['min_hp'], met=len(m['met']), kills=m['kills'], containers=len(set(m['containers'])), items=m['items'],
                 hits=m['hits'], bites=m['bites'], near_misses=m['near_misses'], armor=m['armor'], level_ups=m['level_ups'], mission=(not c.dead and len(set(m['containers'])) >= 3),
                 reflex_actions=m['reflex'], acts=m['acts'], act_fail=dict(m['act_fail'].most_common(8)),
                 fast_calls=len(fast_decisions), fast_per_s=round(len(fast_decisions) / max(1, lived), 2), fast_p50=pct(fast_decisions, .5), fast_p95=pct(fast_decisions, .95),
                 fast_fresh=f['fresh'], fast_stale=f['stale'], fast_low_conf=f['low_conf'], fast_errors=f['errors'], tactic_changes=f['changes'], skipped_same=f['skipped_same'],
                 jev_tokens=a.jev.tokens if cfg['seat'] == 'jev' else 0, jev_usd=round(a.jev.spent, 5) if cfg['seat'] == 'jev' else 0, jev_version=a.jev.version if cfg['seat'] == 'jev' else None,
                 plan_calls=len(a.plan['calls']), plan_p50=pct(a.plan['calls'], .5), plan_cost=round(a.plan['cost'], 5), plan_goals=a.plan['goals'], plan_reached=a.plan['reached'], plan_failed=a.plan['failed'], plan_bad=a.plan['bad'], rule_goals=a.plan['rule_goals'],
                 sight_s=round(f.get('sight_s', 0.0), 1), sight_calls=f.get('sight_calls', 0), frames=m['frames'], kb=round(m['bytes'] / 1024), sight=c.sight, black=list(a.black.values())[:8])
        log('life_end', **{k: v for k, v in s.items() if k in ('lived_s', 'died', 'cause', 'hp_lost', 'kills', 'met', 'containers', 'mission')})
        json.dump(s, open(f'{d}/summary.json', 'w'), indent=0)
        await c.leave(http)
    return s

if __name__ == '__main__':
    s = asyncio.run(life(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 300.0, loud='loud' in sys.argv))
    print(json.dumps({k: v for k, v in s.items() if k not in ('items',)}))
