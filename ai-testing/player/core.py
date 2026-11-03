"""The AI's hands and eyes for Oh shit, Zombies. Only the public client protocol: the session route,
the websocket, and what the server sends a player. Nothing here reads the database or the server's
memory. Everything the brain sees arrives REFLEX_S late, on purpose, so nobody can say it is faster
than a quick human. Logging is in the format the studio asked for."""
import asyncio, collections, json, math, os, time
from datetime import datetime, timezone
import httpx, websockets

REFLEX_S = 0.25
BASE = os.environ.get('BASE', '127.0.0.1:8120')
M = 111320.0


def dist(a, b):
    return math.hypot((a[0] - b[0]) * M, (a[1] - b[1]) * M * math.cos(math.radians(a[0])))


def shift(p, east, north):
    return [p[0] + north / M, p[1] + east / (M * math.cos(math.radians(p[0])))]


class Log:
    """Every line has wall clock and game time. Decisions name the layer that acted: REFLEX, FAST, PLAN."""
    def __init__(self, d):
        os.makedirs(d, exist_ok=True)
        self.dir = d
        self.f = open(f'{d}/events.jsonl', 'a', buffering=1)
        self.game_t = None; self.t0 = None; self.limit = None

    def __call__(self, type, **kw):
        now = time.time()
        row = {'wall': datetime.now(timezone.utc).isoformat(timespec='milliseconds'), 'wall_ts': round(now, 3),
               'game_t': self.game_t, 'life_s': round(now - self.t0, 3) if self.t0 else None, 'type': type, **kw}
        self.f.write(json.dumps(row) + '\n')
        return row

    def decision(self, layer, latency_ms, action, **kw):
        return self('decision', layer=layer, latency_ms=round(latency_ms, 1), action=action, **kw)

    def marker(self, marker, **kw):
        return self('marker', marker=marker, **kw)


class Client:
    """Holds the socket, delays what the brain can see, and keeps the score."""
    def __init__(self, log, start='chicago', limit=300.0, transport=None):
        self.log, self.start, self.limit = log, start, limit
        self.transport = transport                 # None: a plain socket. Otherwise the recording browser.
        self.ws = None; self.token = None; self.hdr = {'cf-connecting-ip': '198.18.77.%d' % (os.getpid() % 250 + 1)}
        self.queue = collections.deque(); self.v = None; self.latest = None
        self.buildings = []; self.stashes = []; self.body = {}; self.corpses = []
        self.replies = collections.deque(); self.mid = 10
        self.placed_at = None; self.dead = False; self.death = None; self.ended = False
        self.ticket = None; self.life_id = None
        self.replay = collections.deque()          # the last 10 s, for the edit
        self.events_in = collections.deque()
        self.m = dict(hp_lost=0.0, met=set(), kills=0, containers=[], items=[], hits=0, hit_dmg=0.0, bites=0, near_misses=0, armor=0,
                      frames=0, bytes=0, acts=0, act_fail=collections.Counter(), reflex=0, level_ups=0, walked=0.0, min_hp=100.0)
        self.last_hp = None; self.last_tick = 0; self.frame_at = 0.0; self.game_now = None
        self.ready_at = 0.0; self.sight = None; self.seen_start = None

    # ------------------------------------------------------------ joining
    async def join(self, http):
        if self.transport:
            return await self.transport.join(self)
        r = await http.post(f'http://{BASE}/api/session', json={'device_id': os.urandom(16).hex(), 'name': 'x'}, headers=self.hdr)
        r.raise_for_status(); self.token = r.json()['token']
        self.ws = await websockets.connect(f'ws://{BASE}/ws?token={self.token}', additional_headers=self.hdr, max_size=None)
        self.rx = asyncio.create_task(self._rx())

    async def _rx(self):
        try:
            async for m in self.ws:
                await self.incoming(m)
        except Exception as e:
            if not self.ended:self.log('socket_closed', why=repr(e)[:160])
        self.ended = True

    async def incoming(self, raw):
        d = json.loads(raw); t = d.get('t')
        if t == 'hello':
            self.ticket = d['placement_ticket']; self.life_id = d.get('life_id')
            if not self.transport and self.placed_at is None:
                await self.act('background', occupation='generalist', trait='balanced', life_id=self.life_id)
                await self.act('place', start=self.start, reason='launch', source='manual', lat=0.0, lng=0.0, accuracy=1.0,
                               timestamp=time.time() * 1000, ticket=self.ticket, request=os.urandom(8).hex())
        elif t == 's':
            self.frame(d, raw)
        elif t == 'r':
            self.replies.append(d)
            if not d.get('ok') and d.get('why'):
                self.m['act_fail'][f"{d.get('a')}: {d.get('why')}"] += 1
            if d.get('rec'):
                self.ready_at = time.time() + d['rec'] - 0.02
            if d.get('a') == 'place' and d.get('ok'):
                self.placed_at = time.time(); self.log.t0 = self.placed_at
                self.log('placed', lat=d.get('lat'), lng=d.get('lng'))
        elif t == 'full':
            self.log('server_full'); self.ended = True

    def frame(self, d, raw):
        now = time.time(); y = d['you']
        self.game_now = d.get('now'); self.log.game_t = self.game_now; self.frame_at = now
        self.m['frames'] += 1; self.m['bytes'] += len(raw)
        if 'buildings' in d: self.buildings = d['buildings']
        if 'stashes' in d: self.stashes = d['stashes']
        if 'corpses' in d: self.corpses = d['corpses']
        if 'body' in d: self.body = d['body']
        d['_at'] = now; self.queue.append(d); self.latest = d; self.sight = d.get('sight', self.sight)
        self.replay.append({'t': round(now, 3), 'game_t': self.game_now, 'you': y, 'z': d['z'], 'ev': d.get('ev'), 'sight': d.get('sight')})
        while self.replay and now - self.replay[0]['t'] > 10.0:
            self.replay.popleft()
        self._score(d, y, now)

    def _score(self, d, y, now):
        m = self.m; hp = y['hp']
        if self.placed_at is None or not (y['lat'] or y['lng']):return
        if self.last_hp is not None and hp < self.last_hp:
            m['hp_lost'] += self.last_hp - hp
        self.last_hp = hp; m['min_hp'] = min(m['min_hp'], hp); m['kills'] = y['kills']
        me = (y['lat'], y['lng'])
        for z in d['z']:
            if (z[6] and z[3] == 'engaged') or (dist(me, (z[1], z[2])) <= 3.4 and z[3] != 'idle'):
                if z[0] not in m['met']:
                    m['met'].add(z[0]); self.log.marker('zombie_met', z=z[0], kind=z[4], state=z[3], hp=hp)
        for e in d.get('ev') or []:
            k = e.get('e')
            if k == 'hit_you':
                m['hits'] += 1; m['hit_dmg'] += e.get('dmg') or 0; bite = e.get('wound') == 'bite'; m['bites'] += bite
                self.log.marker('bite' if bite else 'hit', wound=e.get('wound'), part=e.get('part'), dmg=e.get('dmg'), hp=hp)
            elif k == 'miss_you':
                m['near_misses'] += 1; self.log.marker('near_miss', z=e.get('z'), hp=hp)
            elif k == 'armor':
                m['armor'] += 1; self.log.marker('armor_saved', code=e.get('code'), part=e.get('part'), hp=hp)
            elif k == 'found':
                row = next((s for s in self.stashes if s[0] == e.get('stash')), None); kind = row[3] if row else None
                m['containers'].append(e.get('stash'))
                self.log.marker('chest' if kind == 'chest' else 'container', stash=e.get('stash'), kind=kind, items=[i['code'] for i in e.get('items', [])])
            elif k == 'xp' and (e.get('level_up') or e.get('skill_up')):
                m['level_ups'] += 1; self.log.marker('level_up', skill=e.get('skill'), level=e.get('level'), skill_level=e.get('skill_level'))
            elif k == 'died':
                self.death = e.get('card'); self.log.marker('death', card={a: self.death.get(a) for a in ('cause', 'part', 'by', 'wound', 'kills', 'walked_m', 'lived_s', 'infected')} if self.death else None)
            elif k in ('interrupted', 'broke', 'broke_free', 'dropped', 'bandaged', 'scream', 'alarm', 'grabbed', 'pried', 'opening', 'groan'):
                if k != 'groan':self.log('event', e=k, **{a: b for a, b in e.items() if a in ('what', 'part', 'code', 'name', 'op', 'involuntary')})
        if y.get('dead') and not self.dead:
            self.dead = True; self.m['died_at'] = now
            if not self.replay_saved():pass
        if now - self.last_tick >= 1.0:
            self.last_tick = now
            self.log('tick', hp=hp, end=y['end'], panic=y['panic'], kills=y['kills'], speed=y['speed'],
                     timer_left=round(self.limit - (now - self.placed_at), 1),
                     zeds=len(d['z']), engaged=sum(1 for z in d['z'] if z[6] and z[3] == 'engaged'), tactic=getattr(self, 'tactic', None), goal=getattr(self, 'goal_label', None), sight=d.get('sight'), lat=y['lat'], lng=y['lng'])

    def replay_saved(self):
        """The last 10 s before a death, frame by frame, with the outlines of what was around."""
        with open(f'{self.log.dir}/death_replay.json', 'w') as f:
            json.dump({'note': 'Every server frame in the last 10 s before death, at the time this client received it. Replay against buildings for a top-down cut.',
                       'frames': list(self.replay), 'buildings': [{k: b.get(k) for k in ('id', 'name', 'outline', 'openings')} for b in self.buildings], 'stashes': self.stashes}, f)
        return True

    # ------------------------------------------------------------ what the brain may see
    def perceive(self):
        """Advance to the newest frame at least REFLEX_S old."""
        cut = time.time() - REFLEX_S; advanced = False
        while self.queue and self.queue[0]['_at'] <= cut:
            f = self.queue.popleft(); self.v = f; advanced = True
            for e in f.get('ev') or []:
                self.events_in.append(e)
        return advanced

    # ------------------------------------------------------------ hands
    async def send(self, msg):
        if self.transport:
            return await self.transport.send(msg)
        try:
            await self.ws.send(json.dumps(msg))
        except Exception:
            self.ended = True

    async def act(self, a, **args):
        self.mid += 1; self.m['acts'] += 1
        await self.send({'t': 'act', 'id': self.mid, 'a': a, **args})

    async def pos(self, p):
        y = self.v['you'] if self.v else None
        await self.send({'t': 'pos', 'lat': p[0], 'lng': p[1], 'acc': 1, 'mode': 'desk', 'placement_epoch': y['placement_epoch'] if y else 1, 'floor_epoch': y['floor_epoch'] if y else 0})

    async def leave(self, http):
        self.ended = True
        if self.transport:
            return await self.transport.leave(self)
        try:
            await self.ws.close()
        except Exception:
            pass
        for _ in range(3):
            try:
                await http.delete(f'http://{BASE}/api/me', headers={'authorization': 'Bearer ' + self.token, **self.hdr}); return
            except Exception as e:
                self.log('delete_failed', why=repr(e)[:100]); await asyncio.sleep(2)
