"""Local daylight from real sun position.

Pure, deterministic functions: given a lat/lng and a unix time, work out how high the
sun is and turn that into a 0..1 light level + a phase label. Used to (a) tint the map to
the player's actual local daylight and (b) make zombies denser/tougher after dark.

The solar-altitude math is the standard low-precision NOAA approximation — accurate to
well within a degree, which is far more than a game map needs.
"""
from __future__ import annotations

import math

_DAY_S = 86400.0


def sun_altitude_deg(lat: float, lng: float, now: int) -> float:
    """Approximate solar altitude (degrees above the horizon) for a point and unix time."""
    # Day-of-year fractional angle (NOAA "fractional year" gamma, in radians).
    day = now / _DAY_S
    doy = (day % 365.2422)
    gamma = 2.0 * math.pi / 365.0 * doy
    # Equation of time (minutes) and solar declination (radians).
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    # True solar time (minutes) at this longitude. UTC minutes-of-day + lng offset + EoT.
    utc_min = (now % _DAY_S) / 60.0
    time_offset = eqtime + 4.0 * lng        # 4 min per degree of longitude
    tst = (utc_min + time_offset) % 1440.0
    ha = math.radians(tst / 4.0 - 180.0)    # hour angle (radians)
    phi = math.radians(lat)
    cos_zenith = (math.sin(phi) * math.sin(decl)
                  + math.cos(phi) * math.cos(decl) * math.cos(ha))
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    return 90.0 - math.degrees(math.acos(cos_zenith))


def light_level(lat: float, lng: float, now: int) -> float:
    """0.0 (full night) .. 1.0 (high sun). Smooth through dawn/dusk twilight."""
    alt = sun_altitude_deg(lat, lng, now)
    # Map altitude to light: below -6° (civil twilight end) is night; ramp to full by +12°.
    return max(0.0, min(1.0, (alt + 6.0) / 18.0))


def phase_for(light: float) -> str:
    if light <= 0.02:
        return "night"
    if light < 0.35:
        return "dusk"      # also dawn — same dim look
    if light < 0.75:
        return "day"
    return "noon"


def daylight(lat: float, lng: float, now: int) -> dict:
    """Snapshot payload: light level, phase label, and a 'darkness' 0..1 for the night
    spawn boost. Sent to the client (map tint) and used server-side (spawn scaling)."""
    light = light_level(lat, lng, now)
    return {
        "light": round(light, 3),
        "phase": phase_for(light),
        "alt": round(sun_altitude_deg(lat, lng, now), 1),
        "darkness": round(1.0 - light, 3),
    }
