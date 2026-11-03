"""Where the zombies and the abandoned bags are. Deterministic per map cell and per day, so the
world is the same for everyone and nothing has to be stored until somebody changes it."""
from __future__ import annotations

from app.game.content import (
    CELL_PRECISION, NIGHT_PACK_CHANCE, PACK_SIZE, PACKS_PER_CELL, SPAWN_WINDOW_S, STASH_KINDS,
    STASH_PER_CELL, STASH_TABLE, STASH_LOOT, ITEMS, ZED_KINDS, ZED_VARIANTS,
)
from app.game.sim import _pick, shift
from app.geo import _decode_bbox, _hash32, cell_of, neighbors
from app.rng import seeded


class Spawner:
    def __init__(self, density: float = 1.0, salt: str = "", night_packs: float = 1.0):
        self.density = density      # scales how many packs a cell holds
        self.salt = salt
        self.night_packs = night_packs  # scales the extra after-dark packs

    def bucket(self, now: float) -> int:
        return int(now) // SPAWN_WINDOW_S

    def expires(self, now: float) -> float:
        return float((self.bucket(now) + 1) * SPAWN_WINDOW_S)

    def cells_near(self, lat: float, lng: float) -> list[str]:
        c = cell_of(lat, lng, CELL_PRECISION)
        return [c] + neighbors(c)

    def _place(self, rng, cell):
        la0, la1, ln0, ln1 = _decode_bbox(cell)
        return la0 + (la1 - la0) * rng.random(), ln0 + (ln1 - ln0) * rng.random()

    def _pack(self, rng, cell, b, tag, night) -> list[dict]:
        out = []
        clat, clng = self._place(rng, cell)
        kinds = [(k, v["weight"]) for k, v in ZED_KINDS.items()]
        n = _pick(rng, PACK_SIZE)
        pace = rng.random()                                   # a pack moves at one pace, so it arrives together
        spread = 3.0 + 0.8 * n
        for i in range(n):
            kind = _pick(rng, kinds)
            spec = ZED_KINDS[kind]
            lat, lng = shift(clat, clng, rng.uniform(-spread, spread), rng.uniform(-spread, spread))
            lo, hi = spec["speed"]
            speed = lo + (hi - lo) * min(1.0, max(0.0, pace + rng.uniform(-0.12, 0.12)))
            zid = f"z:{cell}:{b}:{tag}:{i}"
            hp = float(rng.randint(*spec["hp"]))
            rng.randrange(12)        # the look was drawn here when there were twelve; the draw stays so that packs stay where they were
            out.append({"id": zid, "lat": lat, "lng": lng, "kind": kind, "hp": hp, "speed": speed,
                        "variant": _hash32(zid) % ZED_VARIANTS, "night": night})
        return out

    def zeds(self, cell: str, now: float) -> list[dict]:
        b = self.bucket(now)
        rng = seeded(f"zeds:{self.salt}:{cell}:{b}")
        out = []
        n = _pick(rng, PACKS_PER_CELL)
        if self.density != 1.0:                              # scale, keeping it deterministic
            scaled = n * self.density
            n = int(scaled) + (1 if rng.random() < scaled - int(scaled) else 0)
        for p in range(n):
            out += self._pack(rng, cell, b, f"p{p}", False)
        if self.night_packs == 1.0:                           # the original draw, unchanged
            if rng.random() < NIGHT_PACK_CHANCE * min(1.0, self.density):
                out += self._pack(rng, cell, b, "n", True)
        else:
            expect = NIGHT_PACK_CHANCE * min(1.0, self.density) * self.night_packs
            k = int(expect) + (1 if rng.random() < expect - int(expect) else 0)
            for j in range(k):
                out += self._pack(rng, cell, b, "n" if j == 0 else f"n{j}", True)
        return out

    def stashes(self, cell: str, now: float) -> list[dict]:
        b = self.bucket(now)
        rng = seeded(f"stash:{self.salt}:{cell}:{b}")
        out = []
        for i in range(_pick(rng, STASH_PER_CELL)):
            lat, lng = self._place(rng, cell)
            kind = rng.choice(STASH_KINDS)
            table = STASH_LOOT[kind]
            loot, condition = [], {}
            for _ in range(rng.choice([1, 2, 2, 3])):
                code = _pick(rng, [(c, w) for c, w, _q in table])
                lo, hi = next(q for c, _w, q in table if c == code)
                loot.append((code, rng.randint(lo, hi)))
                if ITEMS[code]["kind"] in ("weapon", "gun"):
                    condition[code] = rng.randint(4, 9)
            out.append({"id": f"s:{cell}:{b}:{i}", "lat": lat, "lng": lng,
                        "kind": kind, "loot": loot, "condition": condition})
        return out
