"""C6: things that finish later. A day-long plot, an hour at the fire, an hour with a manual.

All three run on the world clock, which is wall time, so they finish while the game is closed
and across a server restart, and each reward can be taken exactly once.
"""
import copy

from app.game import home, study, survival
from app.game.content import ITEMS, STASH_LOOT, TUNE
from app.game.progression import award
from app.game.sim import Zed
from tests.test_equipment_home import shelter
from tests.test_survival_work import complete

HOUR, DAY = 3600.0, 86400.0


def put(w, a, ll):
    a.lat, a.lng = ll
    w.set_position(a.id, ll[0], ll[1], 1.0)          # where the player is, so a step does not walk them back


def outdoors(w, a, b):
    put(w, a, b.ll((-10, -10)))
    return survival.shift(a.lat, a.lng, 4, 0)


def fire(w, a):
    survival.defaults(a)
    o = dict(id='built:1:90', kind='campfire', lat=a.lat, lng=a.lng, rotation=0, hp=20, items=[], next_item=1, capacity=0)
    a.home['objects'].append(o)
    return o


# ---------------------------------------------------------------- the vegetable plot
def test_plot_takes_a_real_day_and_gives_a_larger_harvest_once():
    w, a, b = shelter()
    ll = outdoors(w, a, b)
    a.add('seeds', 3); a.add('branch', 2)
    complete(w, a, op='craft', recipe='plot', lat=ll[0], lng=ll[1])
    plot = a.home['objects'][0]
    assert plot['kind'] == 'plot' and plot['ready'] == w.now + DAY and a.count('seeds') == 0
    a.lat, a.lng = plot['lat'], plot['lng']
    early = w.act(a.id, 'work', op='harvest', object=plot['id'])
    assert not early['ok'] and '24 hours' in early['why']
    w.now += DAY - 60
    assert not w.act(a.id, 'work', op='harvest', object=plot['id'])['ok']
    w.now += 61
    complete(w, a, op='harvest', object=plot['id'])
    assert a.count('rawfood') == 10 and a.count('seeds') == 3
    again = w.act(a.id, 'work', op='harvest', object=plot['id'])
    assert not again['ok'] and a.count('rawfood') == 10          # replanted: another day, not another harvest
    assert a.home['objects'][0]['ready'] == w.now + DAY


def test_the_quick_garden_and_a_bed_already_planted_keep_their_five_minutes():
    w, a, b = shelter()
    ll = outdoors(w, a, b)
    a.add('seeds', 1); a.add('branch', 2)
    complete(w, a, op='craft', recipe='garden', lat=ll[0], lng=ll[1])
    bed = a.home['objects'][0]
    assert bed['ready'] == w.now + 300
    old = dict(id='old', kind='garden', lat=bed['lat'], lng=bed['lng'], hp=20, items=[], ready=w.now + 120)   # planted before this release
    a.home['objects'].append(old)
    a.lat, a.lng = bed['lat'], bed['lng']
    w.now += 121
    complete(w, a, op='harvest', object='old')
    assert a.count('rawfood') == 3 and a.count('seeds') == 1
    assert next(o for o in a.home['objects'] if o['id'] == 'old')['ready'] == w.now + 300


# ---------------------------------------------------------------- the fire
def test_smoking_takes_an_hour_whether_or_not_anyone_waits_and_is_collected_once():
    w, a, b = shelter()
    outdoors(w, a, b)
    o = fire(w, a)
    a.add('rawfood', 3); a.add('branch', 4)
    complete(w, a, op='slow', recipe='smoke', object=o['id'])
    job = a.home['objects'][0]['job']
    assert a.count('rawfood') == 0 and a.count('branch') == 0 and a.count('smoked') == 0
    assert job['ready'] == w.now + HOUR and job['out'] == {'smoked': 3}
    a.add('rawfood', 3); a.add('branch', 4)
    busy = w.act(a.id, 'work', op='slow', recipe='smoke', object=o['id'])
    assert not busy['ok'] and 'already' in busy['why']
    early = w.act(a.id, 'work', op='take', object=o['id'])
    assert not early['ok'] and '60 minutes' in early['why']
    assert not w.act(a.id, 'work', op='salvage', object=o['id'])['ok']      # never lose what is on it
    xp = a.skill_xp.get('cooking', 0)
    w.now += HOUR + 1                                                       # nobody stood there
    complete(w, a, op='take', object=o['id'])
    assert a.count('smoked') == 3 and 'job' not in a.home['objects'][0]
    assert a.skill_xp['cooking'] == xp + 30
    assert not w.act(a.id, 'work', op='take', object=o['id'])['ok'] and a.count('smoked') == 3
    assert not ITEMS['smoked'].get('perishable') and ITEMS['smoked']['hunger'] > ITEMS['meal']['hunger']


def test_a_job_keeps_the_rules_it_was_started_under_and_an_interrupted_start_costs_nothing():
    w, a, b = shelter()
    outdoors(w, a, b)
    o = fire(w, a)
    a.add('rawfood', 3); a.add('branch', 4)
    assert w.act(a.id, 'work', op='slow', recipe='smoke', object=o['id'])['ok']
    pending = copy.deepcopy(a.channel); a.channel = None
    a.lat += 5 / 111320
    survival.finish(w, a, pending)                                          # walked off mid-setup
    assert a.count('rawfood') == 3 and 'job' not in a.home['objects'][0]
    a.lat, a.lng = o['lat'], o['lng']
    complete(w, a, op='slow', recipe='smoke', object=o['id'])
    before = copy.deepcopy(survival.SLOW['smoke'])
    try:
        survival.SLOW['smoke'].update(out={'smoked': 1}, seconds=9 * HOUR)  # a later release retunes it
        w.now += HOUR + 1
        complete(w, a, op='take', object=o['id'])
    finally:
        survival.SLOW['smoke'].update(before)
    assert a.count('smoked') == 3
    wrong = w.act(a.id, 'work', op='slow', recipe='smoke', object='nowhere')
    assert not wrong['ok']


# ---------------------------------------------------------------- the manual
def test_reading_at_home_for_an_hour_doubles_one_skill_for_this_life():
    w, a, b = shelter()
    book = a.add('manual_carpentry')
    started = w.act(a.id, 'study', item=book['id'])
    assert started['ok'] and a.count('manual_carpentry') == 0
    assert a.study['skill'] == 'carpentry' and a.study['since'] == w.now
    w.step(w.now + HOUR - 30)
    assert a.study and not a.studied
    w.step(w.now + 31)
    assert a.study is None and a.studied == ['carpentry']
    assert any(e.get('e') == 'work' and 'finished' in e.get('message', '') for e in a.events)
    award(a, 'carpentry', 12); award(a, 'cooking', 12)
    assert a.skill_xp['carpentry'] == 24 and a.skill_xp['cooking'] == 12
    again = a.add('manual_carpentry')
    refused = w.act(a.id, 'study', item=again['id'])
    assert not refused['ok'] and a.count('manual_carpentry') == 1           # no second book wasted


def test_leaving_pauses_reading_and_asking_twice_never_counts_twice():
    w, a, b = shelter()
    book = a.add('manual_cooking')
    t0 = w.now
    assert w.act(a.id, 'study', item=book['id'])['ok']
    w.step(t0 + 600)
    assert w.act(a.id, 'study')['ok'] and w.act(a.id, 'study')['ok']        # tapping Read again changes nothing
    assert abs(study.progress(w, a) - 600) < 1e-6
    for _ in range(5):
        assert abs(study.view(w, a)['ready'] - (t0 + HOUR)) <= 1            # the same answer however often it is asked
    here = [a.lat, a.lng]
    put(w, a, survival.shift(a.lat, a.lng, 3, 0))                           # got up and walked across the room
    w.step(t0 + 601)
    assert a.study['since'] is None and abs(a.study['done_s'] - 601) < 1e-6
    assert any('keeps your place' in e.get('message', '') for e in a.events)
    w.step(t0 + 5000)                                                       # a long walk: no reading happens
    assert abs(study.progress(w, a) - 601) < 1e-6 and study.view(w, a)['left_s'] == 2999
    put(w, a, b.ll((-10, -10)))
    outside = w.act(a.id, 'study')
    assert not outside['ok'] and 'home' in outside['why']
    put(w, a, here)
    assert w.act(a.id, 'study')['ok']
    w.step(w.now + 2998)
    assert a.study is not None
    w.step(w.now + 2)
    assert a.studied == ['cooking']


def test_one_book_at_a_time_and_a_grab_puts_it_down():
    w, a, b = shelter()
    first, second = a.add('manual_melee'), a.add('manual_fitness')
    assert w.act(a.id, 'study', item=first['id'])['ok']
    other = w.act(a.id, 'study', item=second['id'])
    assert not other['ok'] and 'finish' in other['why'] and a.count('manual_fitness') == 1
    assert not w.act(a.id, 'study', item=a.add('bandage')['id'])['ok']
    z = Zed(id='z1', kind='walker', lat=a.lat, lng=a.lng, hp=30)
    z.state, z.target = 'engaged', a.id
    w.zeds[z.id] = z
    told = study.update(w, a)
    assert told and a.study['since'] is None
    assert not w.act(a.id, 'study')['ok']
    w.zeds.clear()
    assert w.act(a.id, 'study', op='stop')['ok'] is False                    # already closed
    assert w.act(a.id, 'study')['ok'] and w.act(a.id, 'study', op='stop')['ok']


def test_manuals_are_findable_and_every_skill_has_one():
    from app.game.progression import SKILLS
    taught = {v['teaches'] for v in ITEMS.values() if v.get('teaches')}
    assert taught == set(SKILLS)
    in_tables = {code for table in STASH_LOOT.values() for code, *_ in table if code.startswith('manual_')}
    assert {'manual_' + s for s in SKILLS} == in_tables
    for theme in ('kitchen', 'bathroom', 'bedroom', 'garage'):               # a rare find, never the main contents
        total = sum(w for _, w, _ in STASH_LOOT[theme])
        assert sum(w for c, w, _ in STASH_LOOT[theme] if c.startswith('manual_')) / total < 0.12


# ---------------------------------------------------------------- the home card and coming back
def test_home_card_lists_what_is_running_with_fixed_finish_times():
    w, a, b = shelter()
    outdoors(w, a, b)
    o = fire(w, a)
    a.home['objects'].append(dict(id='p', kind='plot', lat=a.lat, lng=a.lng, hp=20, items=[], ready=w.now + DAY))
    a.add('rawfood', 3); a.add('branch', 4)
    complete(w, a, op='slow', recipe='smoke', object=o['id'])
    put(w, a, b.ll(b.rooms[0]['pos']))
    assert w.act(a.id, 'study', item=a.add('manual_foraging')['id'])['ok']
    jobs = {j['kind']: j for j in home.summary(w, a)['jobs']}
    assert jobs['crop']['name'] == 'Vegetable plot' and jobs['station']['name'] == 'Smoke rations'
    assert jobs['study']['name'] == 'Reading the Foraging Field Guide' and jobs['study']['ready'] == round(w.now + HOUR)
    first = home.summary(w, a)['jobs']
    w.step(w.now + 30)
    assert home.summary(w, a)['jobs'] == first                               # nothing to resend each second
    assert home.returning(w, a) == []                                        # nothing is ready yet
    w.now += DAY
    lines = home.returning(w, a)
    assert lines[0].startswith('You finished the Foraging Field Guide')
    assert lines[1] == 'Ready at home: Smoke rations, Vegetable plot.'
    assert a.studied == ['foraging'] and home.returning(w, a) == [lines[1]]  # the book is told once


async def test_everything_finishes_while_the_game_is_closed_and_the_server_restarts(maker):
    from app.auth import create_anonymous_player
    from app.game.hub import Hub
    from app.models import PlayerHome
    from sqlalchemy import select

    async with maker() as s:
        player = (await create_anonymous_player(s, "s" * 20, "Returner"))["player"]

    async def send(_):
        pass

    async def fresh_hub(now):
        hub = Hub()
        hub.world.spawner = None
        hub.director.policy = lambda *a: "quiet"
        hub.clock = lambda: now[0]
        async with maker() as s:                           # what Hub.start() loads before anyone joins
            hub.world.homes = {r.player_id: copy.deepcopy(r.state) for r in (await s.execute(select(PlayerHome))).scalars()}
        return hub

    def work(hub, actor, now, **args):
        res = hub.world.act(actor.id, 'work', **args)
        if res['ok']:
            now[0] = actor.channel['ends'] + 0.01
            hub.world.step(now[0])
        return res

    LAT, LNG = 44.9778, -93.265
    now = [3_000_000.0]
    hub = await fresh_hub(now)
    conn, actor, _ = await hub.join(player, send)
    actor.lat, actor.lng = LAT, LNG
    hub.world.set_position(player.id, LAT, LNG, 1.0)
    t0 = now[0]
    actor.home = {"name": "Den", "lat": LAT, "lng": LNG, "building": "none", "capacity": 40.0, "revision": 1,
                  "items": [], "next_item": 1, "receipts": []}
    survival.defaults(actor)
    actor.home['objects'] += [
        dict(id='plot', kind='plot', lat=LAT, lng=LNG, hp=20, items=[], next_item=1, capacity=0, ready=t0 + DAY),
        dict(id='fire', kind='campfire', lat=LAT, lng=LNG, hp=20, items=[], next_item=1, capacity=0),
    ]
    hub.world.homes[player.id] = actor.home
    actor.add('rawfood', 3); actor.add('branch', 4)
    assert work(hub, actor, now, op='slow', recipe='smoke', object='fire')['ok']
    actor.study = {"skill": "melee", "code": "manual_melee", "need_s": TUNE["study_s"], "done_s": 0.0,
                   "since": now[0], "at": [LAT, LNG]}
    actor.dirty = True
    await hub._drop(player.id, conn, actor)                                  # the player closes the game at home

    # a day passes; a new process starts with nothing in memory
    now[0] = t0 + DAY + 600
    hub2 = await fresh_hub(now)
    conn2, back, report = await hub2.join(player, send)
    assert report['home'][0].startswith('You finished the Self-Defence Manual')
    assert report['home'][1] == 'Ready at home: Smoke rations, Vegetable plot.'
    assert back.studied == ['melee'] and back.study is None
    assert work(hub2, back, now, op='take', object='fire')['ok'] and back.count('smoked') == 3
    back.end = 100
    assert work(hub2, back, now, op='harvest', object='plot')['ok'] and back.count('rawfood') == 10
    assert not hub2.world.act(back.id, 'work', op='take', object='fire')['ok']
    assert not hub2.world.act(back.id, 'work', op='harvest', object='plot')['ok']
    await hub2._drop(player.id, conn2, back)

    # and again after another restart a minute later: nothing is offered a second time
    now[0] += 60
    hub3 = await fresh_hub(now)
    conn3, third, report3 = await hub3.join(player, send)
    assert report3['home'] == []
    assert third.studied == ['melee'] and third.count('smoked') == 3 and third.count('rawfood') == 10
    assert not hub3.world.act(third.id, 'work', op='take', object='fire')['ok']
    assert not hub3.world.act(third.id, 'work', op='harvest', object='plot')['ok']
