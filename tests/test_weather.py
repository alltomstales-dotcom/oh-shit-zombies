"""C7: a calendar for each life, and weather and a helicopter that a whole area shares."""
import random

from app.game import store, survival, weather
from app.game.content import TUNE
from app.game.sim import Actor, World, Zed
from tests.test_equipment_home import shelter

LAT, LNG = 44.9778, -93.265
DAY = 86400.0


def shift(lat, lng, east, north):
    return survival.shift(lat, lng, east, north)


def a_pass(lat=LAT, lng=LNG, after=2_000_000.0):
    return weather.next_helicopter(lat, lng, after)


def rain_time(lat, lng, want, after=2_000_000.0):
    size = TUNE["rain_block_s"]
    for block in range(int(after // size), int(after // size) + 400):
        t = block * size + 10
        if bool(weather.rain(lat, lng, t)) == want:
            return t
    raise AssertionError("no such weather in 400 blocks")


# ---------------------------------------------------------------- the calendar
def test_a_life_counts_real_days_from_one_and_a_new_life_starts_again():
    now = 5_000_000.0
    old = Actor(id=1, born=now - 3.5 * DAY)
    assert weather.life_day(old, now) == 4
    assert weather.life_day(old, old.born) == 1 and weather.life_day(old, old.born + DAY - 1) == 1
    assert weather.life_day(old, old.born + DAY) == 2
    fresh = store.starter(1, "Next", now)                   # what the hub makes after a death
    assert weather.life_day(fresh, now) == 1
    w = World(rng=random.Random(1))
    old.lat, old.lng = LAT, LNG
    w.add_actor(old, now)
    w.step(now + 1)
    assert w.body(old)["day"] == 4


def test_the_day_number_changes_nothing_about_the_weather_or_the_helicopter():
    heard, overhead, gone = a_pass()
    t = overhead + 5
    young, old = Actor(id=1, born=t - 2 * 3600), Actor(id=2, born=t - 40 * DAY)
    for a in (young, old):
        a.lat, a.lng = LAT, LNG
    assert weather.helicopter(young.lat, young.lng, t) == weather.helicopter(old.lat, old.lng, t)
    assert weather.rain(LAT, LNG, t) == weather.rain(LAT, LNG, t)


# ---------------------------------------------------------------- rain
def test_rain_is_shared_by_an_area_decided_in_blocks_and_about_a_quarter_of_the_time():
    wet = rain_time(LAT, LNG, True)
    near = shift(LAT, LNG, 600, -400)
    assert weather.area_of(*near) == weather.area_of(LAT, LNG)
    assert weather.rain(*near, wet) == weather.rain(LAT, LNG, wet)
    size = TUNE["rain_block_s"]
    assert weather.rain(LAT, LNG, wet)["until"] == (int(wet // size) + 1) * size
    assert weather.rain(LAT, LNG, wet + size - 20)           # the whole block
    far = [bool(weather.rain(LAT + 3, LNG + 3, (int(wet // size) + i) * size + 10)) for i in range(60)]
    here = [bool(weather.rain(LAT, LNG, (int(wet // size) + i) * size + 10)) for i in range(60)]
    assert far != here                                       # another town has its own sky
    share = sum(bool(weather.rain(LAT, LNG, i * size + 10)) for i in range(3000)) / 3000
    assert 0.2 < share < 0.3


def test_rain_fills_barrels_three_times_as_fast_and_muffles_work():
    w, a, b = shelter(); survival.defaults(a)
    lat, lng = a.home["lat"], a.home["lng"]
    for want, water in ((False, 2), (True, 5)):
        w.now = rain_time(lat, lng, want)
        barrel = dict(id='barrel', kind='rainbarrel', lat=a.lat, lng=a.lng, hp=35, items=[], water=0, fill_at=w.now - 60)
        a.home['objects'] = [barrel]
        survival.update(w, a, .2)
        assert barrel['water'] == water, (want, barrel)
    heard = []
    w.noise = lambda lat, lng, radius, src=None, certain=False: heard.append(radius)
    a.add('cloth', 4)
    for want in (False, True):
        w.now = rain_time(a.lat, a.lng, want); a.channel = None; a.busy_until = 0
        assert w.act(a.id, 'work', op='craft', recipe='bandages')['ok']
    assert heard == [35, 35 * TUNE["rain_noise_mult"]]


# ---------------------------------------------------------------- the helicopter
def world_with(now, *actors):
    w = World(rng=random.Random(3))
    for a in actors:
        w.add_actor(a, now)
        w.set_position(a.id, a.lat, a.lng, 1.0)
    return w


def test_two_players_in_one_area_hear_the_same_helicopter_and_another_town_does_not():
    heard, overhead, gone = a_pass()
    assert overhead - heard == TUNE["heli_warn_s"] and gone - overhead == TUNE["heli_over_s"]
    one = Actor(id=1, lat=LAT, lng=LNG, born=heard - 5 * DAY)
    two = Actor(id=2, born=heard - 2 * 3600)                 # a different life, a different age
    two.lat, two.lng = shift(LAT, LNG, 900, 500)
    far = Actor(id=3, lat=LAT + 3, lng=LNG + 3, born=heard - 5 * DAY)
    assert weather.area_of(two.lat, two.lng) == weather.area_of(LAT, LNG) != weather.area_of(far.lat, far.lng)
    w = world_with(heard - 30, one, two, far)
    w.step(heard - 20)
    assert not any(e["e"] == "heli" for a in (one, two, far) for e in a.events)
    w.step(heard + 1)
    first = [[e for e in a.events if e["e"] == "heli"] for a in (one, two)]
    assert first[0] == first[1] == [{"e": "heli", "phase": "coming", "overhead": round(overhead), "ends": round(gone)}]
    assert w.body(one)["weather"]["heli"]["phase"] == "coming"
    if weather.helicopter(far.lat, far.lng, heard + 1) is None:      # its own schedule, almost always empty now
        assert not any(e["e"] == "heli" for e in far.events)
    for a in (one, two):
        a.events.clear()
    w.step(overhead + 1)
    assert [e["phase"] for a in (one, two) for e in a.events if e["e"] == "heli"] == ["overhead", "overhead"]
    w.step(overhead + 2)                                             # said once, not every step
    assert sum(e["e"] == "heli" for e in one.events) == 1
    one.events.clear()
    w.step(gone + 1)
    assert [e["phase"] for e in one.events if e["e"] == "heli"] == ["gone"]
    assert w.body(one)["weather"]["heli"] is None


def test_overhead_it_draws_idle_zombies_to_whoever_is_outdoors_and_passes_over_those_inside():
    heard, overhead, gone = a_pass()
    w, a, b = shelter()                                              # inside the home building
    a.born = overhead - 5 * DAY
    inside = [a.lat, a.lng]
    outside = b.ll((-10, -10))
    z = Zed(id='z1', kind='walker', lat=0, lng=0, hp=30)
    z.lat, z.lng = shift(*outside, -70, -40)                          # well out of sight, in the open
    w.zeds[z.id] = z
    w.set_position(a.id, *inside, 1.0)
    w.now = overhead + 1
    for i in range(1, 60):
        w.step(overhead + 1 + i * .5)
    assert z.state == 'idle' and z.goal is None                      # indoors: it has no reason to come
    assert w.body(a)["weather"]["heli"]["sheltered"] is True
    a.lat, a.lng = outside
    w.set_position(a.id, *outside, 1.0)
    for i in range(1, 30):
        w.step(w.now + .5)
    assert z.state in ('investigate', 'alert', 'chase')
    assert w.body(a)["weather"]["heli"]["sheltered"] is False


def test_a_first_hour_survivor_and_the_warning_minute_draw_nothing():
    heard, overhead, gone = a_pass()
    for born, t in ((overhead - 600, overhead + 5), (overhead - 5 * DAY, heard + 5)):
        a = Actor(id=1, lat=LAT, lng=LNG, born=born)
        w = world_with(t - 1, a)
        z = Zed(id='z1', kind='walker', lat=0, lng=0, hp=30)
        z.lat, z.lng = shift(LAT, LNG, 90, 0)
        w.zeds[z.id] = z
        for i in range(1, 40):
            w.step(t + i * .5)
        assert z.state == 'idle', (born, t, z.state)


def test_passes_are_rare_bounded_daylight_only_and_never_overlap_a_block_edge():
    from app.daylight import light_level
    size = TUNE["heli_block_s"]
    area = weather.area_of(LAT, LNG)
    first = int(1_790_000_000 // size)                              # real dates: a year of blocks
    windows = [(block, weather._heli_window(area, block)) for block in range(first, first + 2920)]
    per_day = sum(w is not None for _, w in windows) / 365
    assert 0.8 < per_day < 2.0                                       # about one or two a day
    for block, w in windows:
        if w:
            assert block * size <= w[0] < w[1] < w[2] <= (block + 1) * size
            assert light_level(LAT, LNG, int(w[0])) >= 0.3           # heard in daylight, never in the dark
