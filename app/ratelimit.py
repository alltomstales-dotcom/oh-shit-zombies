"""Tiny in-memory fixed-window rate limiter. Single-instance; good enough for a playtest.

Not a distributed limiter — for multi-instance, move the counters to Redis.
"""
from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, limit: int, window_s: int):
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, list[float]] = {}
        self._swept = 0.0

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        cutoff = now - self.window_s
        # Every client address gets a key, so idle keys must be swept or the table only grows.
        if now - self._swept > self.window_s:
            self._swept = now
            self._hits = {k: v for k, v in self._hits.items() if v and v[-1] > cutoff}
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


def client_ip(headers, client, trust_proxy: str) -> str:
    """Who is asking. A forwarding header is only believed from the proxy that sets it."""
    header = {"cloudflare": "cf-connecting-ip", "railway": "x-real-ip"}.get(trust_proxy)
    found = headers.get(header) if header else None
    return (found or (client.host if client else "unknown"))[:64]
