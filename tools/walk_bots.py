"""Scripted players on a fake clock: how does a walk actually pace out?

    python -m tools.walk_bots [--walks 200] [--minutes 20] [--policy fighter|walker|mixed] [--night]
                              [--set key=value ...] [--density 1.0] [--pace 1.35] [--quiet] [--heli]

Each bot walks real streets-sized blocks at 1.35 m/s (--pace 6 is the tap-to-walk travel pace) through the same spawner the server uses,
reacts after a human-ish delay (0.4 to 0.9 s) and sometimes picks the wrong button. The output is
the pacing a player would feel: minutes between scares, fight length, wounds, deaths.
"""
from __future__ import annotations

import argparse
import math
import random
import statistics as st

from app.game.content import STARTER_KIT
from app.game.sim import Actor, World, dist_m, shift
from app.game.spawn import Spawner

LAT, LNG = 44.9778, -93.2650
HZ = 5


def new_world(seed, night, density, tune):
    w = World(rng=random.Random(seed), tune=tune, spawner=Spawner(density=density, salt=str(seed)),
              light_fn=(lambda *_: 0.0) if night else (lambda *_: 1.0))
    a = Actor(id=1, lat=LAT, lng=LNG, born=-10 * 86400)
    for code, qty in STARTER_KIT:
        row = a.add(code, qty)
        if code == "bat":
            a.hands = row["id"]
    w.add_actor(a, 1.0)
    w.set_position(1, LAT, LNG, 3.0)
    return w, a


def walk(seed, minutes, policy, night, density, tune, grace=False, pace=1.35, quiet=False):
    rng = random.Random(seed * 7919 + 1)
    w, a = new_world(seed, night, density, tune)
    if grace:
        a.born = 0.0
    if quiet:
        w.act(1, "quiet", op="start")
    t, px, py = 1.0, 0.0, 0.0                       # metres from the start
    heading = rng.choice([0, 90, 180, 270])
    leg_left = rng.uniform(60, 160)
    react_at = 0.0
    m = dict(notices=0, grabs=0, fights=[], hits=0, bites=0, kills=0, died=None, min_end=100.0,
             max_panic=0.0, fight_actions=0, fight_s=0.0, first_notice=None, gaps=[], stashes=0,
             max_on=0, bandages=0, backs=0, infected=False, shelf_loot_qty=0)
    fight_start, last_notice = None, None
    stand = False
    for _ in range(int(minutes * 60 * HZ)):
        t += 1.0 / HZ
        engaged = [z for z in w.zeds.values() if z.state == "engaged" and z.target == 1]
        chasers = [z for z in w.zeds.values() if z.target == 1 and z.state in ("chase", "alert", "engaged")]
        near = [z for z in chasers if dist_m(a.lat, a.lng, z.lat, z.lng) < 12]
        downed = [z for z in w.zeds.values() if z.state in ("down", "rising")
                  and dist_m(a.lat, a.lng, z.lat, z.lng) < 5.0]
        # --- feet
        want_fight = policy == "fighter" or (policy == "mixed" and len(chasers) <= 2)
        stand = bool(engaged) or bool(a.channel) or (want_fight and (near or downed))
        if not stand:
            stepm = min(pace, w.movement_speed(a)) / HZ
            if chasers and not want_fight:              # walk directly away from the nearest
                z = min(chasers, key=lambda z: dist_m(a.lat, a.lng, z.lat, z.lng))
                dx = (a.lng - z.lng) * 111320 * math.cos(math.radians(a.lat))
                dy = (a.lat - z.lat) * 111320
                d = math.hypot(dx, dy) or 1.0
                px, py = px + dx / d * stepm, py + dy / d * stepm
            else:
                px += math.sin(math.radians(heading)) * stepm
                py += math.cos(math.radians(heading)) * stepm
                leg_left -= stepm
                if leg_left <= 0:
                    heading = (heading + rng.choice([-90, 90, 0])) % 360
                    leg_left = rng.uniform(60, 160)
        lat, lng = shift(LAT, LNG, px + rng.gauss(0, 1.5), py + rng.gauss(0, 1.5))   # GPS wobble
        w.set_position(1, lat, lng, 5.0)
        w.step(t)
        # --- what happened
        for e in a.events:
            k = e["e"]
            if k == "groan" and e.get("you"):
                m["notices"] += 1
                if m["first_notice"] is None:
                    m["first_notice"] = t
                if last_notice is not None and t - last_notice > 20:
                    m["gaps"].append(t - last_notice)
                last_notice = t
            elif k == "grabbed":
                m["grabs"] += 1
            elif k == "hit_you":
                m["hits"] += 1
                m["bites"] += e["wound"] == "bite"
            elif k == "found":
                m["stashes"] += 1
                m['shelf_loot_qty'] += sum(i['qty'] for i in e.get('items',[]))
            elif k == "bandaged":
                m["bandages"] += 1
            elif k == "broke_free":
                m["backs"] += 1
        a.events.clear()
        m["min_end"] = min(m["min_end"], a.end)
        m["max_panic"] = max(m["max_panic"], a.panic)
        m["max_on"] = max(m["max_on"], len(engaged))
        if engaged and fight_start is None:
            fight_start = t
        if fight_start is not None and not engaged and not near:
            m["fights"].append(t - fight_start)
            fight_start = None
        if engaged:
            m["fight_s"] += 1.0 / HZ
        if a.dead:
            m["died"] = (t, a.death["cause"])
            break
        # --- hands, after a human delay
        if t < react_at or t < a.busy_until or (a.channel and a.channel["kind"] == "back"):
            continue
        act = None
        if engaged:
            if (len(engaged) >= 3 or a.hp < 35 or a.end < 12) and a.end >= 15 and t >= a.back_ready_at \
                    and policy != "fighter":
                act = ("back", {})
            elif downed and len(engaged) <= 1:
                act = ("swing", {})
            elif len(engaged) >= 2 or a.end < 25:
                act = ("shove", {})
            else:
                act = ("swing", {})
            if rng.random() < 0.10:
                act = (rng.choice(["swing", "shove"]), {})
        elif downed and want_fight:
            act = ("swing", {})
        elif near and want_fight:
            z = min(near, key=lambda z: dist_m(a.lat, a.lng, z.lat, z.lng))
            if dist_m(a.lat, a.lng, z.lat, z.lng) <= 3.2:
                act = ("swing", {"target": z.id})
        elif not chasers and not a.channel:
            if any(wd["bleeding"] for wd in a.wounds) and a.count("bandage"):
                act = ("bandage", {})
            elif a.panic > 50 and a.count("snack"):
                act = ("use", {"code": "snack"})
            elif a.end < 40 and a.count("water"):
                act = ("use", {"code": "water"})
            else:
                for s in w.stashes.values():
                    if s["id"] not in a.claimed and dist_m(a.lat, a.lng, s["lat"], s["lng"]) < 12:
                        act = ("search", {"stash": s["id"]})
                        break
        if act:
            r = w.act(1, act[0], **act[1])
            if r.get("ok"):
                if engaged:
                    m["fight_actions"] += 1
                if act[0] in ("swing", "shove") and r.get("kill"):
                    m["kills"] += 1
                react_at = max(a.busy_until, t) + rng.uniform(0.15, 0.5)
            else:
                react_at = t + rng.uniform(0.4, 0.9)
    m["kills"] = a.kills
    m["minutes"] = (t - 1.0) / 60.0
    m["hp"] = a.hp
    m["infected"] = a.infected_at is not None
    # Conservative farming ceiling: all killed-body stock, without paying
    # search/approach time, danger or carry capacity. This bot does not take it.
    m['body_loot_qty'] = sum(i['qty'] for b in w.corpses.values() for i in b['items'])
    return m


def summarise(rows, label):
    n = len(rows)
    mins = sum(r["minutes"] for r in rows)
    hours = mins / 60.0
    fights = [f for r in rows for f in r["fights"]]
    gaps = [g for r in rows for g in r["gaps"]]
    deaths = [r for r in rows if r["died"]]
    first = [r["first_notice"] for r in rows if r["first_notice"]]
    fa = sum(r["fight_actions"] for r in rows)
    fs = sum(r["fight_s"] for r in rows)

    def q(xs, p):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else float("nan")
    print(f"\n== {label}: {n} walks, {mins:.0f} min simulated")
    print(f"  noticed by a zombie      {sum(r['notices'] for r in rows) / hours:6.1f} per hour"
          f"   (first one after {st.median(first) if first else float('nan'):.0f} s, median)")
    print(f"  scares (20 s apart)      {(len(gaps) + len(first)) / hours:6.1f} per hour   gap median {q(gaps, .5):.0f} s   10% under {q(gaps, .1):.0f} s   90% under {q(gaps, .9):.0f} s")
    print(f"  grabbed                  {sum(r['grabs'] for r in rows) / hours:6.1f} per hour")
    print(f"  fights                   {len(fights) / hours:6.1f} per hour   median {q(fights, .5):.1f} s   90% under {q(fights, .9):.1f} s")
    print(f"  decisions while grabbed  {fa / fs * 60 if fs else 0:6.1f} per minute")
    print(f"  most on you at once      median {st.median(r['max_on'] for r in rows):.0f}   90% under {q([r['max_on'] for r in rows], .9)}")
    print(f"  hits taken               {sum(r['hits'] for r in rows) / hours:6.1f} per hour   bites {sum(r['bites'] for r in rows) / hours:.2f} per hour")
    print(f"  kills                    {sum(r['kills'] for r in rows) / hours:6.1f} per hour")
    print(f"  lowest endurance         median {st.median(r['min_end'] for r in rows):.0f}   peak panic median {st.median(r['max_panic'] for r in rows):.0f}")
    print(f"  bags searched            {sum(r['stashes'] for r in rows) / hours:6.1f} per hour")
    print(f"  died during the walk     {len(deaths)} of {n} ({100 * len(deaths) / n:.0f}%)"
          + (f"   median at {st.median(d['died'][0] for d in deaths) / 60:.1f} min" if deaths else ""))
    print(f"  infected by the end      {sum(r['infected'] for r in rows)} of {n} ({100 * sum(r['infected'] for r in rows) / n:.0f}%)")
    print(f"  health at the end        median {st.median(r['hp'] for r in rows):.0f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--walks", type=int, default=200)
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--policy", default="all")
    ap.add_argument("--night", action="store_true")
    ap.add_argument("--grace", action="store_true")
    ap.add_argument("--density", type=float, default=1.0)
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--pace", type=float, default=1.35)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--heli", action="store_true", help="a helicopter is overhead from minute 5 to minute 15 of every walk")
    args = ap.parse_args()
    # The bots' clock is fake, so the real sky schedule means nothing here: dry and quiet unless asked.
    from app.game import weather
    weather.rain = lambda lat, lng, now: None
    weather.helicopter = lambda lat, lng, now: ({"id": "bots", "phase": "overhead", "overhead": 300.0, "ends": 900.0}
                                                if args.heli and 300.0 <= now < 900.0 else None)
    tune = {}
    for kv in args.set:
        k, v = kv.split("=")
        tune[k] = float(v)
    for pol in (["walker", "mixed", "fighter"] if args.policy == "all" else [args.policy]):
        rows = [walk(s, args.minutes, pol, args.night, args.density, tune, args.grace, args.pace, args.quiet) for s in range(args.walks)]
        summarise(rows, f"{pol}{' at night' if args.night else ''} at {args.pace} m/s{' creeping' if args.quiet else ''}{' with a helicopter overhead for 10 of the minutes' if args.heli else ''}")
