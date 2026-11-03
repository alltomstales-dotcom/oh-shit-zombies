"""Three layers. PLAN sets an errand now and then. FAST judges fight, flee, indoors, errand or treat. REFLEX is code:
walking, doors, looting, swinging, shoving. Arms remove layers; they never change the layer that remains."""
import asyncio, json, math, os, random, re, statistics as st, time
from core import dist, shift
import models, prompts

BANDAGE_WOUNDS = ('bite', 'laceration', 'scratch')
WEAPON_RANK = {'axe': 4, 'crowbar': 3, 'bat': 2, 'knife': 1}
TAKE = {'bandage', 'disinfectant', 'water', 'snack', 'axe', 'crowbar', 'bat', 'knife', 'leather', 'fire_jacket', 'fire_pants', 'boots', 'gloves', 'helmet', 'pants', 'shirt', 'rucksack', 'schoolbag'}


class Z:
    __slots__ = ('id', 'lat', 'lng', 'state', 'kind', 'mine', 'bite_in', 'hpf', 'd')

    def __init__(self, r, me):
        self.id, self.lat, self.lng, self.state, self.kind, _, self.mine, self.bite_in, self.hpf = r
        self.d = dist(me, (self.lat, self.lng))


class Scan:
    def __init__(self, v):
        y = v['you']; self.y = y; self.me = (y['lat'], y['lng'])
        self.zs = sorted((Z(r, self.me) for r in v['z']), key=lambda z: z.d)
        self.engaged = [z for z in self.zs if z.mine and z.state == 'engaged']
        self.hunters = [z for z in self.zs if z.mine and z.state in ('chase', 'alert', 'engaged', 'down', 'rising', 'stagger')]
        self.near4 = [z for z in self.zs if z.d <= 4]
        self.near10 = [z for z in self.zs if z.d <= 10]
        self.near15h = [z for z in self.hunters if z.d <= 15]
        self.nearest = self.zs[0].d if self.zs else None
        self.inside = v.get('inside')


class Agent:
    def __init__(self, c, arm, log, planner_model=None, seat=None, loud=False):
        self.c, self.arm, self.log = c, arm, log
        self.loud = loud; self.next_scream = 0
        self.seat, self.planner_model = seat, planner_model
        self.tactic = 'goal'; c.tactic = 'goal'; self.tactic_since = 0; self.hide = None
        self.goal = None; self.black = {}; self.searching = None; self.search_since = 0
        self.taken = set(); self.next_act = 0
        self.route = []; self.target = None; self.within = 1.5; self.route_wait = False; self.next_route = 0
        self.route_fails = 0; self.last_pos = 0; self.stuck_at = 0; self.stuck_ref = None; self.door = None; self.door_tries = 0; self.tried_doors = set()
        self.flee_heading = None; self.sprinting = False
        self.decisions = dict(fast=[], stale=0, applied=0, fresh=0, low_conf=0, errors=0, skipped_same=0, changes=0)
        self.plan = dict(calls=[], cost=0.0, goals=0, reached=0, failed=0, bad=0, rule_goals=0)
        self.pending = None; self.plan_task = None; self.next_plan = 0; self.plan_needed = True
        self.hits10 = []; self.hp_prev = None; self.last_goal_done = 0; self.last_fast = 0; self.last_sig = None; self.goal_label_set(None)
        self.plan_raw = open(f'{log.dir}/plan_raw.jsonl', 'a', buffering=1)

    def goal_label_set(self, s):
        self.c.goal_label = s

    # ------------------------------------------------------------------ logging helpers
    def reflex(self, action, **kw):
        at = self.c.v.get('_at', time.time()); self.c.m['reflex'] += 1
        self.log.decision('REFLEX', (time.time() - at) * 1000, action, **kw)

    async def act(self, a, log=True, **args):
        if log:
            self.reflex(a, **{k: v for k, v in args.items() if k in ('target', 'stash', 'opening', 'op', 'code', 'wound', 'item')})
        await self.c.act(a, **args)

    # ------------------------------------------------------------------ main loop
    async def run(self):
        c = self.c
        while not c.ended and not c.dead:
            await asyncio.sleep(0.05)
            now = time.time()
            if c.placed_at and now - c.placed_at >= c.limit:
                break
            if not c.perceive() and c.v is None:
                continue
            if not c.v or not c.placed_at:
                continue
            await self.replies()
            self.events()
            s = Scan(c.v)
            if s.y.get('dead'):
                continue
            if s.zs:
                self.decisions['sight_s'] = self.decisions.get('sight_s', 0.0) + (now - getattr(self, 'prev_loop', now))
            self.prev_loop = now
            if self.loud and now - c.placed_at > 40 and now >= self.next_scream and s.y['scream'] <= 0:
                self.next_scream = now + 15; self.log.marker('deliberate_scream')
                await c.act('scream')
            await self.housekeeping(s, now)
            await self.decide_tactic(s, now)
            await self.perform(s, now)
        self.end()

    def end(self):
        if self.plan_task and not self.plan_task.done():
            self.plan_task.cancel()

    async def replies(self):
        c = self.c
        while c.replies:
            r = c.replies.popleft(); a = r.get('a')
            if a == 'route':
                self.route_wait = False
                if r.get('ok') and r.get('route'):
                    self.route = [list(p) for p in r['route']]; self.route_fails = 0
                else:
                    self.route = []; self.route_fails += 1; self.next_route = time.time() + 0.5
                    self.need_door = True
                    self.log('nav', what='route_failed', why=r.get('why'), inside=(self.c.v or {}).get('inside'), goal=(self.goal or {}).get('stash'), fails=self.route_fails)
            elif a == 'exit_route':
                self.route_wait = False
                self.log('nav', what='exit_route', ok=r.get('ok'), why=r.get('why'), opening=r.get('opening'), legs=len(r.get('route') or []))
                if r.get('ok'):
                    self.route = [list(p) for p in r['route']]
                    if r.get('opening'):
                        self.door = dict(id=r['opening'], exit=True)
                else:
                    self.route_fails += 1; self.next_route = time.time() + 0.5
            elif a == 'opening':
                self.log('nav', what='opening', ok=r.get('ok'), why=r.get('why'), opening=r.get('opening'))
                if self.door and r.get('opening') == self.door.get('id') or (self.door and not r.get('ok')):
                    if not r.get('ok'):
                        self.tried_doors.add(self.door.get('id')); self.door_tries += 1
                    self.door = None; self.route = []; self.next_route = time.time() + 0.2; self.need_door = False
                if self.hide and r.get('ok'):
                    self.hide['opened'] = True
            elif a == 'search' and not r.get('ok') and self.searching:
                self.searching = None; self.search_since = 0
                if self.goal and self.goal.get('type') == 'loot':
                    self.fail_goal(f"search: {r.get('why')}")

    def events(self):
        c = self.c
        while c.events_in:
            e = c.events_in.popleft(); k = e.get('e')
            if k == 'hit_you':
                self.hits10.append(time.time())
            elif k == 'found':
                self.searching = None
                if self.goal and self.goal.get('type') == 'loot' and self.goal.get('stash') == e.get('stash'):
                    self.goal['looting'] = True; self.goal['found_at'] = time.time()
            elif k == 'interrupted' and e.get('what') == 'search':
                self.searching = None

    # ------------------------------------------------------------------ small chores any survivor does
    async def housekeeping(self, s, now):
        c, y = self.c, s.y
        if now < self.next_act or now < c.ready_at or y['busy'] > 0.05 or y['channel']:
            return
        if s.engaged:
            return
        body = c.body; items = body.get('items', [])
        hands = body.get('hands')
        held = next((i for i in items if i['id'] == hands), None)
        best = max((i for i in items if i['code'] in WEAPON_RANK and i.get('cond', 1)), key=lambda i: WEAPON_RANK[i['code']], default=None)
        if best and (held is None or WEAPON_RANK.get(held['code'], 0) < WEAPON_RANK[best['code']]) and not s.near10:
            self.next_act = now + 1.0
            return await self.act('equip', item=best['id'])
        worn = body.get('worn', {}) or {}
        wearing = set(worn.values()) if isinstance(worn, dict) else set()
        for i in items:
            if i['code'] in ('leather', 'fire_jacket', 'fire_pants', 'boots', 'gloves', 'helmet', 'pants', 'shirt', 'rucksack', 'schoolbag') and i['id'] not in wearing and i['id'] not in self.taken and not s.near10:
                self.taken.add(i['id']); self.next_act = now + 0.5
                return await self.act('wear', item=i['id'])
        if y['end'] < 30 and any(i['code'] == 'water' for i in items) and not s.near4:
            self.next_act = now + 1.2
            return await self.act('use', code='water')

    # ------------------------------------------------------------------ the FAST seat
    def legal(self, s):
        out = ['goal']
        if s.zs:
            out = ['fight', 'flee'] + out
            if not s.inside and self.nearest_door(s) is not None:
                out.insert(2, 'indoors')
        bleeding = [w for w in self.c.body.get('wounds', []) if w['bleeding']]
        if bleeding and not s.engaged and any(i['code'] == 'bandage' for i in self.c.body.get('items', [])):
            out.append('treat')
        return out

    def rule_tactic(self, s):
        """The hand-written answer, used by the rules arms and as the fallback when a model is down."""
        legal = self.legal(s)
        if s.engaged or (s.nearest is not None and s.nearest < 6 and s.near15h):
            many = len(s.near15h) > 3
            if (many or s.y['hp'] < 30) and 'flee' in legal:
                return 'flee'
            return 'fight'
        if 'treat' in legal and not any(z.d < 12 for z in s.hunters):
            return 'treat'
        return 'goal'

    def state_for_model(self, s):
        y = s.y; body = self.c.body
        wounds = body.get('wounds', [])
        now = time.time(); self.hits10 = [t for t in self.hits10 if now - t < 10]
        dr = self.nearest_door(s)
        g = self.goal or {}
        goal_d = round(dist(s.me, (g['lat'], g['lng']))) if g.get('lat') else None
        return {'rules': prompts.RULES,
                'you': {'health': round(y['hp']), 'endurance': round(y['end']), 'panic': y['panic'], 'bleeding_wounds': sum(1 for w in wounds if w['bleeding']),
                        'bandages': sum(i['qty'] for i in body.get('items', []) if i['code'] == 'bandage'),
                        'weapon': (y.get('hands') or {}).get('code', 'bare hands'), 'hits_taken_last_10s': len(self.hits10),
                        'inside_a_building': bool(s.inside), 'nearest_door_m': round(dist(s.me, dr)) if dr else None},
                'zombies': {'holding_you': len(s.engaged), 'within_4m': len(s.near4), 'within_10m': len(s.near10), 'hunting_you_within_15m': len(s.near15h), 'in_sight': len(s.zs),
                            'nearest_m': round(s.nearest, 1) if s.nearest is not None else None,
                            'next_bite_in_s': min((z.bite_in for z in s.engaged if z.bite_in >= 0), default=None),
                            'closest': [{'m': round(z.d, 1), 'state': z.state, 'kind': z.kind, 'after_you': bool(z.mine), 'health_share': z.hpf} for z in s.zs[:5]]},
                'errand': {'what': self.c.goal_label, 'distance_m': goal_d}, 'doing_now': self.tactic}

    def sig(self, s):
        return (len(s.engaged), len(s.near10), round((s.nearest if s.nearest is not None else 99) / 2), round(s.y['hp'] / 5), len(self.legal(s)), self.tactic)

    def still_fresh(self, d, s):
        """A decision is stale if the fight it judged has changed, however fast it came back."""
        was = d['snap']
        if len(s.engaged) != was['engaged']: return False
        if abs((s.nearest if s.nearest is not None else 60) - was['nearest']) > 3 and min((s.nearest if s.nearest is not None else 60), was['nearest']) < 25: return False
        if was['hp'] - s.y['hp'] > 8: return False
        return d['choice'] in self.legal(s)

    async def decide_tactic(self, s, now):
        if self.seat == 'random':
            return
        if self.seat == 'rule' or self.seat is None:
            t = self.rule_tactic(s)
            if t != self.tactic:
                self.set_tactic(t, 'REFLEX', 0, s, why='rule')
            return
        # model seats: apply what has come back, ask again when due
        if self.pending:
            d, self.pending = self.pending, None
            if self.still_fresh(d, s):
                self.decisions['fresh'] += 1
                if d['p'] < 0.45:
                    self.decisions['low_conf'] += 1
                    self.log.decision('FAST', d['ms'], 'keep', wanted=d['choice'], p=d['p'], model=d['model'])
                else:
                    self.set_tactic(d['choice'], 'FAST', d['ms'], s, p=d['p'], model=d['model'], probs=d.get('probs'))
                self.decisions['applied'] += 1
            else:
                self.decisions['stale'] += 1
                self.log('stale_decision', layer='FAST', wanted=d['choice'], age_ms=round((time.time() - d['t']) * 1000), latency_ms=round(d['ms'], 1), model=d['model'], was=d['snap'], now=dict(engaged=len(s.engaged), nearest=s.nearest, hp=s.y['hp']))
        if not self.fast_busy() and self.seat in ('jev', 'slow'):
            active = bool(s.zs) or now - (self.hits10[-1] if self.hits10 else 0) < 5 or self.y_bleeding()
            gap = 0.25 if active else 1.0
            if now - self.last_fast >= gap:
                legal = self.legal(s)
                sg = self.sig(s)
                if len(legal) > 1 and (bool(s.zs) or not (sg == self.last_sig and now - self.last_fast < 2.5)):
                    self.last_fast = now; self.last_sig = sg
                    self.fast_task = asyncio.create_task(self.ask_fast(s, legal))
                else:
                    if len(legal) == 1 and self.tactic != legal[0]:
                        self.set_tactic(legal[0], 'REFLEX', 0, s, why='only legal option')
                    self.decisions['skipped_same'] += 1; self.last_fast = now

    def fast_busy(self):
        return getattr(self, 'fast_task', None) is not None and not self.fast_task.done()

    def y_bleeding(self):
        return any(w['bleeding'] for w in self.c.body.get('wounds', []))

    async def ask_fast(self, s, legal):
        snap = dict(engaged=len(s.engaged), nearest=s.nearest if s.nearest is not None else 60, hp=s.y['hp'])
        state = self.state_for_model(s); t0 = time.time()
        if s.zs:
            self.decisions['sight_calls'] = self.decisions.get('sight_calls', 0) + 1
        try:
            if self.seat == 'jev':
                if self.jev.over_cap:
                    self.log('jev_cap_reached'); self.seat = 'rule'; return
                ans, ms, tk = await self.jev.ask(state, prompts.tactic_question(legal))
                a = ans['tactic']; choice = a['choice']; p = a['probabilities'][choice]; probs = a['probabilities']
                self.decisions['fast'].append(ms)
                self.pending = dict(choice=choice, p=p, ms=ms, t=t0, snap=snap, model=self.jev.version, probs=probs)
            else:
                text, ms, cost, err = await models.claude(prompts.slow_prompt(state, legal), self.slow_model)
                self.decisions['fast'].append(ms); self.plan['cost'] += cost
                word = re.sub(r'[^a-z]', '', (text or '').lower().split()[0]) if text else ''
                if word in legal:
                    self.pending = dict(choice=word, p=1.0, ms=ms, t=t0, snap=snap, model=self.slow_model)
                else:
                    self.decisions['errors'] += 1; self.log('fast_error', raw=(text or '')[:100], err=err)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.decisions['errors'] += 1; self.log('fast_error', err=repr(e)[:200])
            t = self.rule_tactic(s)           # never leave the survivor without an answer
            if t != self.tactic:
                self.set_tactic(t, 'REFLEX', 0, s, why='fallback: model error')

    def set_tactic(self, t, layer, ms, s, **kw):
        if t == self.tactic:
            self.log.decision(layer, ms, 'keep:' + t, **kw) if layer == 'FAST' else None
            return
        self.decisions['changes'] += 1
        self.log.decision(layer, ms, t, was=self.tactic, hp=s.y['hp'], holding=len(s.engaged), near10=len(s.near10), **kw)
        self.tactic = t; self.c.tactic = t; self.tactic_since = time.time()
        if t != 'indoors':
            self.hide = None
        self.flee_heading = None

    # ------------------------------------------------------------------ doing it
    async def perform(self, s, now):
        if self.seat == 'random':
            return await self.random_play(s, now)
        await self.stop_sprint_if_calm(s)
        if s.y['channel'] and s.y['channel']['kind'] == 'bandage' and self.tactic == 'treat':
            return
        if self.tactic == 'flee':
            return await self.flee(s, now)
        if await self.combat(s, now):
            return
        if self.tactic == 'fight':
            if s.near10 or s.near15h:
                return await self.halt(s, now)         # let it come, swing when it arrives
            return await self.errand(s, now)
        if self.tactic == 'treat':
            return await self.treat(s, now)
        if self.tactic == 'indoors':
            return await self.indoors(s, now)
        await self.errand(s, now)

    async def combat(self, s, now):
        """Press only when there is something to hit: a burst at empty air cost the first survivor 30 endurance."""
        c, y = self.c, s.y; cb = y['combat']
        if not (cb['swing'] or cb['shove']):
            return False
        relevant = s.engaged or any(z.d <= 3.4 and z.state != 'idle' for z in s.zs) or self.tactic == 'fight'
        if not relevant:
            return False
        if now < c.ready_at or y['busy'] > 0.05 or (y['channel'] and y['channel']['kind'] == 'back'):
            return True
        by = {z.id: z for z in s.zs}
        sw, sh = by.get(cb['swing']), by.get(cb['shove'])
        if sw and sw.state in ('down', 'rising'):
            await self.act('swing', target=sw.id, log=True)
        elif sh and sh.state == 'stagger':
            await self.act('swing', target=sh.id)
        elif sh and y['end'] >= 8:
            await self.act('shove', target=sh.id)
        elif sw:
            await self.act('swing', target=sw.id)
        else:
            return False
        c.ready_at = max(c.ready_at, now + 0.3)
        return True

    async def halt(self, s, now):
        if s.y['speed'] > 0.3 and now - self.last_pos > 0.4:
            self.last_pos = now
            await self.c.pos(list(s.me))

    async def stop_sprint_if_calm(self, s):
        if self.sprinting and (self.tactic != 'flee' or not s.near10):
            self.sprinting = False
            await self.c.act('sprint', op='stop')

    async def treat(self, s, now):
        y = s.y
        if y['channel'] or now < self.next_act or now < self.c.ready_at or y['busy'] > 0.05:
            return
        await self.halt(s, now)
        if y['speed'] > 0.3:
            return
        self.next_act = now + 1.0
        await self.act('bandage')

    async def flee(self, s, now):
        c, y = self.c, s.y
        if s.engaged:
            if now >= c.ready_at and y['busy'] <= 0.05 and y['back'] <= 0 and y['end'] >= 15:
                c.ready_at = now + 0.4
                return await self.act('back')
            if await self.combat(s, now):
                return
        threats = s.hunters or s.zs
        if not threats:
            return await self.errand(s, now)
        ex = sum((z.lng - s.me[1]) for z in threats[:4]); ny = sum((z.lat - s.me[0]) for z in threats[:4])
        away = math.atan2(-ny, -ex)
        moved = self.stuck_ref is not None and dist(s.me, self.stuck_ref) > 0.4
        if self.flee_heading is None:
            self.flee_heading = away
        if now - self.stuck_at > 0.8:
            if not moved and self.stuck_ref is not None:
                self.flee_heading += random.choice((-1, 1)) * 1.0
            elif moved:
                self.flee_heading = away
            self.stuck_ref = s.me; self.stuck_at = now
        if s.nearest is not None and s.nearest < 7 and y['end'] > 25 and not self.sprinting:
            self.sprinting = True
            await self.c.act('sprint', op='start')
        if now - self.last_pos >= 0.2:
            self.last_pos = now
            await c.pos(shift(list(s.me), math.cos(self.flee_heading) * 5, math.sin(self.flee_heading) * 5))

    # ------------------------------------------------------------------ doors
    def nearest_door(self, s, within=40):
        best = None; bd = within
        for b in self.c.buildings:
            for o in b.get('openings', []):
                if o.get('kind') == 'window' or o.get('barricaded') or o['id'] in self.tried_doors:
                    continue
                mid = [(o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2]
                d = dist(s.me, mid)
                if d < bd:
                    bd = d; best = mid
        return best

    def door_near(self, s, within=40, building=None):
        best = None; bd = within
        for b in self.c.buildings:
            if building and b['id'] != building:
                continue
            for o in b.get('openings', []):
                if o.get('kind') == 'window' or o.get('barricaded') or o['id'] in self.tried_doors:
                    continue
                mid = [(o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2]
                d = dist(s.me, mid)
                if d < bd:
                    bd = d; best = dict(id=o['id'], mid=mid, open=o.get('open') or o.get('broken'), a=o['a'], b=o['b'], building=b['id'], label=o.get('label'))
        return best

    def approach(self, door, side_of):
        a, b = door['a'], door['b']; mid = door['mid']
        de = (b[1] - a[1]) * 111320 * math.cos(math.radians(a[0])); dn = (b[0] - a[0]) * 111320
        n = math.hypot(de, dn) or 1
        options = [shift(list(mid), -dn / n * t, de / n * t) for t in (-1.8, 1.8)]
        outline = next((b.get('outline') for b in self.c.buildings if b['id'] == door.get('building')), None)
        if outline and not self.inside_outline(side_of, outline):
            outside = [p for p in options if not self.inside_outline(p, outline)]
            if outside:
                return outside[0]
        return min(options, key=lambda p: dist(p, side_of))

    @staticmethod
    def inside_outline(p, poly):
        y, x = p; hit = False
        for (y0, x0), (y1, x1) in zip(poly, poly[1:] + poly[:1]):
            if (y0 > y) != (y1 > y) and x < x0 + (y - y0) / (y1 - y0) * (x1 - x0):
                hit = not hit
        return hit

    async def indoors(self, s, now):
        c, y = self.c, s.y
        h = self.hide
        if h is None:
            d = self.door_near(s)
            if not d:
                self.set_tactic('goal', 'REFLEX', 0, s, why='no door')
                return
            h = self.hide = dict(door=d, phase='to', at=now)
            self.reflex('go_indoors', opening=d['id'])
            self.walk(self.approach(d, s.me), 1.2)
        d = h['door']
        if now - h['at'] > 30:
            self.tried_doors.add(d['id']); self.hide = None
            return
        if h['phase'] == 'to':
            near = dist(s.me, d['mid']) < 2.5
            if near:
                if d['open'] or h.get('opened'):
                    h['phase'] = 'in'
                    far = max([shift(list(d['mid']), -(d['mid'][1] - s.me[1]) * -111320 * math.cos(math.radians(s.me[0])) / 2, (d['mid'][0] - s.me[0]) * 111320 / 2)], key=lambda p: 0)
                    inward = [d['mid'][0] + (d['mid'][0] - s.me[0]) * 1.2, d['mid'][1] + (d['mid'][1] - s.me[1]) * 1.2]
                    self.walk(inward, 0.6)
                elif now >= c.ready_at and y['busy'] <= 0.05 and now > self.next_act:
                    self.next_act = now + 0.7
                    await self.act('opening', opening=d['id'], op='open')
                    h['tries'] = h.get('tries', 0) + 1
                    if h['tries'] > 3:
                        self.tried_doors.add(d['id']); self.hide = None
                return
            await self.walk_step(s, now)
        elif h['phase'] == 'in':
            st_ = await self.walk_step(s, now)
            if s.inside or st_ != 'walking':
                h['phase'] = 'close'
        elif h['phase'] == 'close':
            if dist(s.me, d['mid']) < 2.6 and now > self.next_act and y['busy'] <= 0.05:
                self.next_act = now + 1.0; h['closes'] = h.get('closes', 0) + 1
                await self.act('opening', opening=d['id'], op='close')
                if h['closes'] >= 2:
                    h['phase'] = 'hold'
            elif dist(s.me, d['mid']) >= 2.6:
                h['phase'] = 'hold'
        # hold: stay put; the seat decides when to come out

    # ------------------------------------------------------------------ walking
    def walk(self, target, within=1.5):
        self.target = list(target); self.within = within; self.route = []; self.route_wait = False; self.next_route = 0; self.route_fails = 0
        self.stuck_ref = None; self.door = None; self.door_tries = 0; self.need_door = False; self.direct = False

    async def walk_step(self, s, now):
        c = self.c
        if self.target is None:
            return 'arrived'
        if now < getattr(self, 'wiggle_until', 0):
            await self.steer(s, self.wiggle, now)
            return 'walking'
        if dist(s.me, self.target) <= self.within:
            await self.halt(s, now); self.target = None
            return 'arrived'
        if self.door:
            return await self.door_step(s, now)
        if getattr(self, 'need_door', False):
            self.need_door = False
            if self.route_fails >= 5 or self.door_tries >= 5:
                self.target = None
                return 'failed'
            bld = (self.goal or {}).get('building')
            if s.inside and s.inside != bld:
                self.route_wait = True; await c.act('exit_route')
                return 'walking'
            if not s.inside and self.route_fails >= 2 and now >= getattr(self, 'wiggle_until', 0):
                # Tucked against a wall or into a gap, the path search can't start. Step off and ask again.
                a = random.random() * 6.28
                self.wiggle = shift(list(s.me), math.cos(a) * 3, math.sin(a) * 3); self.wiggle_until = now + 0.8; self.next_route = now + 0.9
                self.log('nav', what='step_off', fails=self.route_fails)
                return 'walking'
            scope = s.inside or bld
            d = self.closed_door(s, scope, 30 if s.inside else 90) if scope else None
            if d:
                self.door = dict(d, exit=False, goto=self.approach(d, s.me)); self.route = []; self.next_route = now
                self.log('nav', what='door', opening=d['id'], label=d.get('label'), m=round(dist(s.me, d['mid'])))
                return await self.door_step(s, now)
            self.next_route = now + 1.0
        if not self.route and not self.route_wait and now >= self.next_route:
            self.route_wait = True; self.next_route = now + 1.0
            await c.act('route', lat=self.target[0], lng=self.target[1])
        if not self.route:
            return 'walking'
        while self.route and dist(s.me, self.route[0]) < 1.0:
            self.route.pop(0)
        if not self.route:
            self.next_route = 0
            if dist(s.me, self.target) > self.within + 1:
                self.route_fails += 1
                if self.route_fails >= 4:
                    self.target = None
                    return 'failed'
            return 'walking'
        await self.steer(s, self.route[0], now)
        if now - self.stuck_at > 2.5:
            if self.stuck_ref is not None and dist(s.me, self.stuck_ref) < 0.6 and s.y['busy'] <= 0.05 and not s.y['channel']:
                self.route = []; self.route_fails += 1; self.next_route = now
                self.need_door = True
                if self.route_fails >= 4:
                    self.target = None
                    return 'failed'
            self.stuck_ref = s.me; self.stuck_at = now
        return 'walking'

    def goal_in_building(self, bid):
        return (self.goal or {}).get('building') == bid

    async def steer(self, s, wp, now):
        if now - self.last_pos < 0.2:
            return
        self.last_pos = now
        d = dist(s.me, wp)
        if d <= 4:
            p = wp
        else:
            f = 4 / d
            p = [s.me[0] + (wp[0] - s.me[0]) * f, s.me[1] + (wp[1] - s.me[1]) * f]
        await self.c.pos(list(p))

    def closed_door(self, s, building, within):
        best = None; bd = within
        for b in self.c.buildings:
            if b['id'] != building:
                continue
            for o in sorted(b.get('openings', []), key=lambda o: o.get('label') != 'Entrance'):
                if o.get('kind') == 'window' or o.get('barricaded') or o.get('open') or o.get('broken') or o['id'] in self.tried_doors:
                    continue
                mid = [(o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2]
                d = dist(s.me, mid) - (20 if o.get('label') == 'Entrance' and not s.inside else 0)
                if d < bd:
                    bd = d; best = dict(id=o['id'], mid=mid, a=o['a'], b=o['b'], building=b['id'], label=o.get('label'))
        return best

    async def door_step(self, s, now):
        c, y, d = self.c, s.y, self.door
        if d.get('exit') and 'mid' not in d:
            for b in c.buildings:
                for o in b.get('openings', []):
                    if o['id'] == d['id']:
                        d['mid'] = [(o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2]
            if 'mid' not in d:
                self.door = None
                return 'walking'
        if dist(s.me, d['mid']) <= 2.4:
            if now >= c.ready_at and y['busy'] <= 0.05 and now > self.next_act:
                self.next_act = now + 0.7; self.door_tries += 1
                await self.act('opening', opening=d['id'], op='open')
            return 'walking'
        if getattr(self, 'need_door', False):                 # no way to this door either
            self.need_door = False; self.tried_doors.add(d['id']); self.door = None; self.route = []
            self.need_door = True
            return 'walking'
        if not self.route and not d.get('exit') and not self.route_wait and now >= self.next_route:
            self.route_wait = True; self.next_route = now + 1.0
            await c.act('route', lat=d['goto'][0], lng=d['goto'][1])
            return 'walking'
        while self.route and dist(s.me, self.route[0]) < 1.0:
            self.route.pop(0)
        if self.route:
            await self.steer(s, self.route[0], now)
        elif d.get('exit'):
            await self.steer(s, d['mid'], now)
        if now - self.stuck_at > 3:
            if self.stuck_ref is not None and dist(s.me, self.stuck_ref) < 0.5:
                self.tried_doors.add(d['id']); self.door = None; self.route = []; self.route_fails += 1; self.need_door = True
            self.stuck_ref = s.me; self.stuck_at = now
        return 'walking'

    # ------------------------------------------------------------------ the errand
    def rule_goal(self, s):
        """Nearest unsearched container, street ones first. No containers near: walk on."""
        best = None; bd = 1e9
        for r in self.c.stashes:
            sid, lat, lng, kind, claimed, bld = r[0], r[1], r[2], r[3], r[4], r[5]
            if claimed or sid in self.black:
                continue
            d = dist(s.me, (lat, lng)) + (0 if not bld or bld == s.inside else 35)
            if d < bd:
                bd = d; best = r
        if best:
            return dict(type='loot', stash=best[0], lat=best[1], lng=best[2], kind=best[3], building=best[5], source='rule')
        a = random.random() * 6.28
        p = shift(list(s.me), math.cos(a) * 80, math.sin(a) * 80)
        return dict(type='explore', lat=p[0], lng=p[1], source='rule')

    def set_goal(self, g, s, layer='REFLEX', ms=0, **kw):
        g['since'] = time.time(); self.goal = g
        label = {'loot': f"search the {g.get('kind')} ", 'explore': 'walk on', 'hide': 'hide indoors', 'treat': 'bandage'}.get(g['type'], g['type'])
        self.goal_label_set(label.strip())
        self.log.marker('goal_set', layer=layer, goal=g['type'], target=g.get('stash') or g.get('bearing'), kind=g.get('kind'), source=g.get('source'), **kw)
        if g.get('lat'):
            self.walk((g['lat'], g['lng']), 1.8 if g.get('building') else 6 if g['type'] == 'loot' else 4)
        self.searching = None
        if g['type'] == 'hide':
            self.hide = None
        self.plan['goals'] += 1 if g.get('source') == 'plan' else 0
        self.plan['rule_goals'] += 1 if g.get('source') == 'rule' else 0

    def done_goal(self, why):
        g = self.goal
        self.log.marker('goal_done', goal=g['type'], target=g.get('stash'), why=why, secs=round(time.time() - g['since'], 1), source=g.get('source'))
        if g.get('source') == 'plan':
            self.plan['reached'] += 1
        self.goal = None; self.goal_label_set(None); self.plan_needed = True; self.target = None

    def fail_goal(self, why):
        g = self.goal
        if g.get('stash'):
            self.black[g['stash']] = why
        self.log.marker('goal_failed', goal=g['type'], target=g.get('stash'), why=why, secs=round(time.time() - g['since'], 1), source=g.get('source'))
        if g.get('source') == 'plan':
            self.plan['failed'] += 1
        self.goal = None; self.goal_label_set(None); self.plan_needed = True; self.target = None

    async def errand(self, s, now):
        c, y = self.c, s.y
        if self.planner_model:
            self.maybe_plan(s, now)
        if self.goal is None and (c.v.get('mapping') or not c.buildings) and now - c.placed_at < 25:
            return
        if self.goal is None:
            if self.planner_model and now - c.placed_at < 25 and (not getattr(self, 'last_plan', 0) or (self.plan_task and not self.plan_task.done())):
                return                                    # first look around: wait for the first plan
            self.set_goal(self.rule_goal(s), s)
        g = self.goal
        if now - g['since'] > 50 and g['type'] != 'hide':
            return self.fail_goal('took too long')
        if g['type'] == 'treat':
            if not self.y_bleeding():
                return self.done_goal('nothing bleeding')
            return await self.treat(s, now)
        if g['type'] == 'hide':
            return await self.indoors(s, now)
        if g['type'] == 'explore':
            r = await self.walk_step(s, now)
            if r == 'arrived':
                self.done_goal('arrived')
            elif r == 'failed':
                self.fail_goal('no way there')
            return
        row = next((r for r in c.stashes if r[0] == g['stash']), None)
        if g.get('looting'):
            return await self.take_loot(s, now, g)
        if row is None or row[4]:
            # The claim shows in the stash list a moment before the delayed eyes see the shelf.
            if row and any(x['id'] == g['stash'] for x in c.v.get('loot') or []):
                g['looting'] = True; g['found_at'] = now
                return await self.take_loot(s, now, g)
            if row and now - g.setdefault('claimed_at', now) < 1.5:
                return
            return self.done_goal('searched, nothing to take') if row else self.fail_goal('gone')
        if self.searching:
            if not y['channel'] and now - self.search_since > 1.5:
                self.searching = None
            return
        if row[7] and not s.engaged and y['busy'] <= 0.05 and now >= c.ready_at and now > self.next_act:
            await self.halt(s, now)
            self.searching = g['stash']; self.search_since = now; self.next_act = now + 0.6
            return await self.act('search', stash=g['stash'])
        r = await self.walk_step(s, now)
        if r == 'failed':
            self.fail_goal('no way there')
        elif r == 'arrived' and not row[7]:
            self.walk((g['lat'], g['lng']), 1.2); g['close'] = g.get('close', 0) + 1
            if g['close'] > 2:
                self.fail_goal('cannot reach it')

    async def take_loot(self, s, now, g):
        c, y = self.c, s.y
        if now < self.next_act or y['busy'] > 0.05 or y['channel']:
            return
        shelf = next((x for x in c.v.get('loot') or [] if x['id'] == g['stash']), None)
        if shelf is None:
            if now - g.get('found_at', now) > 2:
                self.done_goal('searched')
            return
        want = [i for i in shelf['items'] if i['code'] in TAKE and (i['id'], g['stash']) not in self.taken]
        if not want:
            return self.done_goal('searched')
        i = want[0]; self.taken.add((i['id'], g['stash'])); self.next_act = now + 0.3
        c.m['items'].append(i['code'])
        await self.act('loot', stash=g['stash'], item=i['id'], qty=i['qty'], revision=shelf['revision'], request=os.urandom(8).hex())

    # ------------------------------------------------------------------ the PLAN layer
    def maybe_plan(self, s, now):
        if self.plan_task and not self.plan_task.done():
            return
        if not self.c.stashes and now - self.c.placed_at < 15:
            return                                    # let the map arrive before asking what to do on it
        if now - getattr(self, 'last_plan', 0) < 20:  # every so often, not per move; the nearest-container rule fills gaps
            return
        if self.plan_needed or now >= self.next_plan:
            self.plan_needed = False; self.next_plan = now + 60; self.last_plan = now
            self.plan_task = asyncio.create_task(self.ask_plan(s))

    def plan_state(self, s):
        c, y = self.c, s.y; body = c.body
        rows = sorted((r for r in c.stashes if not r[4] and r[0] not in self.black), key=lambda r: dist(s.me, (r[1], r[2])))[:12]
        names = {b['id']: b.get('name') for b in c.buildings}
        return dict(seconds_left=round(c.limit - (time.time() - c.placed_at)), containers_searched=len(c.m['containers']),
                    you=dict(health=round(y['hp']), endurance=round(y['end']), bleeding_wounds=sum(1 for w in body.get('wounds', []) if w['bleeding']),
                             weapon=(y.get('hands') or {}).get('code', 'bare hands'), inside=names.get(s.inside) if s.inside else None,
                             items={i['code']: i['qty'] for i in body.get('items', [])}, wearing=list((body.get('worn') or {}).keys())),
                    zombies=dict(in_sight=len(s.zs), hunting_you=len(s.hunters), nearest_m=round(s.nearest) if s.nearest is not None else None, sight_m=c.sight),
                    containers=[dict(id=r[0], kind=r[3], distance_m=round(dist(s.me, (r[1], r[2]))), where='street' if not r[5] else ('this building' if r[5] == s.inside else 'inside ' + str(names.get(r[5], 'another building')))) for r in rows],
                    current_errand=c.goal_label, recent=[{'hp_lost_so_far': round(c.m['hp_lost'], 1), 'kills': c.m['kills']}])

    async def ask_plan(self, s):
        st8 = self.plan_state(s)
        prompt = prompts.PLAN.format(state=json.dumps(st8))
        t0 = time.time()
        text, ms, cost, err = await models.claude(prompt, self.planner_model)
        self.plan['calls'].append(ms); self.plan['cost'] += cost
        self.plan_raw.write(json.dumps({'wall_ts': round(time.time(), 3), 'game_t': self.log.game_t, 'life_s': round(time.time() - self.c.placed_at, 2), 'model': self.planner_model, 'latency_ms': round(ms), 'cost_usd': cost, 'state': st8, 'raw': text, 'err': err}) + '\n')
        self.log.decision('PLAN', ms, 'raw', model=self.planner_model, cost_usd=cost, raw=text)
        if self.c.ended:
            return
        try:
            m = re.search(r'\{.*\}', text or '', re.S); j = json.loads(m.group(0))
            sc = Scan(self.c.v)
            g = None
            if j.get('goal') == 'loot':
                r = next((r for r in self.c.stashes if r[0] == j.get('target') and not r[4]), None)
                if r:
                    g = dict(type='loot', stash=r[0], lat=r[1], lng=r[2], kind=r[3], building=r[5], source='plan')
            elif j.get('goal') == 'explore':
                b = {'N': 90, 'NE': 45, 'E': 0, 'SE': -45, 'S': -90, 'SW': -135, 'W': 180, 'NW': 135}.get(j.get('bearing'))
                if b is not None:
                    p = shift(list(sc.me), math.cos(math.radians(b)) * 80, math.sin(math.radians(b)) * 80)
                    g = dict(type='explore', bearing=j['bearing'], lat=p[0], lng=p[1], source='plan')
            elif j.get('goal') == 'hide':
                g = dict(type='hide', source='plan')
            elif j.get('goal') == 'treat':
                g = dict(type='treat', source='plan')
            if g is None:
                raise ValueError('illegal goal')
            self.set_goal(g, sc, layer='PLAN', ms=ms, why=j.get('why'))
        except Exception as e:
            self.plan['bad'] += 1
            self.log('plan_bad', raw=(text or '')[:300], err=repr(e)[:100])

    # ------------------------------------------------------------------ the floor
    async def random_play(self, s, now):
        c, y = self.c, s.y
        if now < getattr(self, 'rnd_next', 0):
            return
        self.rnd_next = now + 0.7
        opts = ['walk', 'walk', 'walk', 'idle']
        if y['combat']['swing']: opts += ['swing']
        if y['combat']['shove']: opts += ['shove']
        if s.engaged and y['back'] <= 0 and y['end'] >= 15: opts += ['back']
        if any(w['bleeding'] for w in c.body.get('wounds', [])) and any(i['code'] == 'bandage' for i in c.body.get('items', [])): opts += ['bandage']
        ready = [r for r in c.stashes if r[7] and not r[4]]
        if ready and not s.engaged: opts += ['search', 'search']
        for r in c.v.get('loot') or []:
            if r.get('items') and not s.engaged: opts += ['take']; break
        o = random.choice(opts)
        if o == 'walk':
            self.rnd_h = getattr(self, 'rnd_h', random.random() * 6.28) + random.uniform(-1.2, 1.2)
            self.rnd_goal = shift(list(s.me), math.cos(self.rnd_h) * 5, math.sin(self.rnd_h) * 5)
            await c.pos(self.rnd_goal)
        elif o == 'search':
            await self.act('search', stash=random.choice(ready)[0])
        elif o == 'take':
            shelf = next(r for r in c.v['loot'] if r.get('items')); i = shelf['items'][0]
            c.m['items'].append(i['code'])
            await self.act('loot', stash=shelf['id'], item=i['id'], qty=i['qty'], revision=shelf['revision'], request=os.urandom(8).hex())
        elif o != 'idle':
            await self.act(o)
