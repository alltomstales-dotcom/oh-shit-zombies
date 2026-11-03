"""Difficulty profiles: every dial that decides how dangerous a five-minute walk is, in one place.

`classic` is the game as it was tuned for friends on Railway, number for number. `public` is the
setting chosen by the bot sweep of November 2026 (see ~/osz-stack/SWEEP.md and DEVLOG.md): scripted
bots die in about a third of five-minute lives, instead of almost never.

Pick one with DIFFICULTY=classic|public. DIFFICULTY_TUNE takes a JSON object of dial overrides on
top of the chosen profile, which is how the sweep tried settings without editing code. Nothing here
removes a system; it only changes how much of each there is.

Dials:
  density        zombie packs per map cell, multiplied (the old ZED_DENSITY setting)
  night_packs    how many of the extra after-dark packs come out, multiplied
  zed_speed      zombie walking pace, multiplied (the survivor's paces never change)
  noise          how far a survivor's footsteps and searching carry, multiplied
  notice         how quickly a zombie in range notices you, multiplied
  grace_notice   a new survivor's first day: noticing is multiplied by this
  grace_bite     a new survivor's first day: the chance a wound is a bite is multiplied by this
  early_s        the gentle first moments after arriving, in seconds (0: none, the classic game)
  early_notice   during them, zombies notice you this much as fast
  early_speed    during them, whatever chases you walks at this share of its pace
  director       how the pacing director behaves (see director.py)
"""
from __future__ import annotations

import json

DIRECTOR_EASE = {
    "mode": "ease",          # the original: weighted chance, and it backs off when you are hurt
    "lull_s": (45.0, 100.0),
}

DIRECTOR_ESCALATE = {
    "mode": "escalate",      # pressure rises with time in the session, and being hurt doesn't stop it
    "gentle_s": 60.0,        # the first minute: only the opening shamblers, nothing sent after you
    "ramp_s": 240.0,         # from gentle to full pressure over the next four minutes
    "lull_start_s": (40.0, 70.0),
    "lull_end_s": (12.0, 25.0),
    "group_grow": 3,         # zombies added to a group at full pressure
    "hunt_size": (3, 5),     # a pack already on your trail, only once pressure passes half
}

PROFILES = {
    "classic": {
        "density": 1.3, "night_packs": 1.0, "zed_speed": 1.0, "noise": 1.0, "notice": 1.0,
        "grace_notice": 0.6, "grace_bite": 0.5, "early_s": 0.0, "early_notice": 1.0, "early_speed": 1.0,
        "director": DIRECTOR_EASE,
    },
    # Chosen by the sweep of 2 November 2026 (setting "P4" in SWEEP.md): scripted bots died in about
    # a third of five-minute lives, against none in classic. More zombies, nearly twice as fast,
    # quicker to notice, no first-day grace, a harder escalating director, and a gentle first minute.
    "public": {
        "density": 4.0, "night_packs": 1.0, "zed_speed": 1.8, "noise": 1.0, "notice": 2.0,
        "grace_notice": 1.0, "grace_bite": 1.0, "early_s": 60.0, "early_notice": 0.1, "early_speed": 0.5,
        "director": dict(DIRECTOR_ESCALATE, group_grow=6, hunt_size=(5, 8), lull_end_s=(8.0, 15.0)),
    },
}

NOISE_KEYS = ("noise_still_m", "noise_quiet_m", "noise_walk_m", "noise_travel_m", "noise_sprint_m", "search_noise_m")
DIRECTORS = {"ease": DIRECTOR_EASE, "escalate": DIRECTOR_ESCALATE}


def resolve(name: str = "classic", overrides: str | dict | None = None) -> dict:
    """The profile's dials with any overrides on top. Unknown names fall back to classic."""
    base = PROFILES.get((name or "classic").strip().lower(), PROFILES["classic"])
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    if isinstance(overrides, str):
        overrides = json.loads(overrides) if overrides.strip() else {}
    for k, v in (overrides or {}).items():
        if k == "director":
            if isinstance(v, str):
                v = DIRECTORS[v]
            mode = v.get("mode", out["director"].get("mode"))
            merged = dict(DIRECTORS[mode]) if mode != out["director"].get("mode") else dict(out["director"])
            merged.update(v)
            out["director"] = merged
        elif k in PROFILES["classic"]:
            out[k] = v
        else:
            raise ValueError(f"unknown difficulty dial {k!r}")
    return out


def tune_for(d: dict, base: dict) -> dict:
    """World TUNE overrides for these dials. `base` is the TUNE they multiply."""
    t = {"zed_speed_mult": float(d["zed_speed"]), "grace_notice": float(d["grace_notice"]),
         "grace_bite": float(d["grace_bite"]), "early_s": float(d["early_s"]),
         "early_notice": float(d["early_notice"]), "early_speed": float(d["early_speed"])}
    if d["noise"] != 1.0:
        t.update({k: base[k] * d["noise"] for k in NOISE_KEYS})
    if d["notice"] != 1.0:
        t.update(notice_rate_near=base["notice_rate_near"] * d["notice"],
                 notice_rate_far=base["notice_rate_far"] * d["notice"])
    return t


def describe(d: dict) -> str:
    dr = d["director"]
    return (f"density {d['density']}, night packs x{d['night_packs']}, zombie speed x{d['zed_speed']}, "
            f"noise x{d['noise']}, notice x{d['notice']}, first-day grace notice {d['grace_notice']} "
            f"bite {d['grace_bite']}, first {d['early_s']:.0f} s notice x{d['early_notice']} chase x{d['early_speed']}, "
            f"director {dr['mode']}")
