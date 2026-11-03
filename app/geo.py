"""Geohash + spatial helpers. Pure, dependency-free, deterministic."""
from __future__ import annotations

import math

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash_encode(lat: float, lng: float, precision: int = 7) -> str:
    precision = max(1, min(12, int(precision)))  # bound to avoid abuse via client input
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    out: list[str] = []
    bit = ch = 0
    even = True
    while len(out) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            if lng >= mid:
                ch = (ch << 1) | 1
                lng_lo = mid
            else:
                ch = ch << 1
                lng_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                ch = (ch << 1) | 1
                lat_lo = mid
            else:
                ch = ch << 1
                lat_hi = mid
        even = not even
        bit += 1
        if bit == 5:
            out.append(_BASE32[ch])
            bit = ch = 0
    return "".join(out)


def cell_of(lat: float, lng: float, precision: int = 7) -> str:
    return geohash_encode(lat, lng, precision)


def _decode_bbox(gh: str) -> tuple[float, float, float, float]:
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    even = True
    for c in gh:
        cd = _BASE32.index(c)
        for i in range(4, -1, -1):
            bit = (cd >> i) & 1
            if even:
                mid = (lng_lo + lng_hi) / 2
                if bit:
                    lng_lo = mid
                else:
                    lng_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if bit:
                    lat_lo = mid
                else:
                    lat_hi = mid
            even = not even
    return lat_lo, lat_hi, lng_lo, lng_hi


def _center(gh: str) -> tuple[float, float]:
    lat_lo, lat_hi, lng_lo, lng_hi = _decode_bbox(gh)
    return (lat_lo + lat_hi) / 2, (lng_lo + lng_hi) / 2


_EARTH_R_M = 6_371_000.0


WANDER_R_M = 28.0   # how far a zombie shambles from its anchor (must match map.js)


def _hash32(s: str) -> int:
    """FNV-1a 32-bit — byte-identical to the JS _hash() in map.js."""
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def wander_pos(lat: float, lng: float, eid: str, now: float) -> tuple[float, float]:
    """A spawn's live shambling position — same deterministic formula the client animates,
    so the server agrees with where the zombie visibly is."""
    h = _hash32(eid)
    a, b, c = (h % 1000) / 1000, ((h >> 10) % 1000) / 1000, ((h >> 20) % 1000) / 1000
    ph1, ph2 = a * 6.283, b * 6.283
    per1, per2 = 33 + c * 38, 47 + a * 38
    dlat = WANDER_R_M * math.sin(now / per1 + ph1) / 111111.0
    dlng = WANDER_R_M * math.cos(now / per2 + ph2) / (111111.0 * (math.cos(math.radians(lat)) or 1.0))
    return lat + dlat, lng + dlng


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres between two lat/lng points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * _EARTH_R_M * math.asin(min(1.0, math.sqrt(a)))


# Twin Cities (Minneapolis–Saint Paul) metro bounding box. Dev/testing routes are
# geofenced here so only play from the testing area can mutate the world.
MSP_BOUNDS = (44.55, 45.25, -93.80, -92.75)   # (lat_min, lat_max, lng_min, lng_max)


def in_msp_metro(lat: float, lng: float) -> bool:
    la0, la1, ln0, ln1 = MSP_BOUNDS
    return la0 <= lat <= la1 and ln0 <= lng <= ln1


def neighbors(gh: str) -> list[str]:
    """The 8 surrounding cells of the same precision, self excluded."""
    lat, lng = _center(gh)
    lat_lo, lat_hi, lng_lo, lng_hi = _decode_bbox(gh)
    dlat = lat_hi - lat_lo
    dlng = lng_hi - lng_lo
    p = len(gh)
    out: list[str] = []
    seen: set[str] = set()
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            if i == 0 and j == 0:
                continue
            adj_lat = max(-90.0, min(90.0, lat + i * dlat))
            adj_lng = lng + j * dlng
            if adj_lng > 180.0:
                adj_lng -= 360.0
            elif adj_lng < -180.0:
                adj_lng += 360.0
            c = geohash_encode(adj_lat, adj_lng, p)
            if c != gh and c not in seen:
                seen.add(c)
                out.append(c)
    return out
