"""Deterministic RNG + time bucketing. The basis of the shared world."""
from __future__ import annotations

import hashlib
import random


def seeded(key: str) -> random.Random:
    h = hashlib.sha256(key.encode("utf-8")).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def time_bucket(now_epoch: int, window_seconds: int) -> int:
    return int(now_epoch) // int(window_seconds)


def world_seed(cell: str, bucket: int, kind: str) -> str:
    return f"{kind}:{cell}:{bucket}"
