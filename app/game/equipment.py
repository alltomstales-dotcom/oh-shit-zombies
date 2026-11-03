"""Wearable equipment: one slot per item, protection at the struck body part."""
from app.game.content import ITEMS

SLOTS = ("head", "torso", "legs", "hands", "feet", "back")


def worn_items(actor):
    for slot, iid in actor.worn.items():
        row = actor.item(iid)
        if row and ITEMS[row["code"]].get("slot") == slot and (row.get("cond") or 0) > 0:
            yield row, ITEMS[row["code"]]


def speed_factor(actor):
    factor = 1.0
    for _, spec in worn_items(actor):
        factor *= spec.get("pace", 1.0)
    return max(.7, factor)


def bag_bonus(actor):
    return sum(spec.get("capacity", 0) for _, spec in worn_items(actor))


def intercept(actor, part, wound, rng):
    for row, spec in worn_items(actor):
        if part not in spec.get("covers", ()):
            continue
        protection = spec.get("bite" if wound == "bite" else "scratch", 0)
        protection *= row["cond"] / spec.get("cond", 10)
        if rng.random() < protection:
            row["cond"] = max(0, row["cond"] - 1)
            actor.dirty = True
            return row
    return None


def wear(actor, item=None, slot=None, op="wear"):
    if op == "remove":
        if slot not in SLOTS:
            return {"ok": False, "why": "choose an equipment slot"}
        actor.worn.pop(slot, None)
    elif op == "wear":
        row = actor.item(item)
        spec = ITEMS.get(row["code"], {}) if row else {}
        if not spec.get("slot") or not (row.get("cond") or 0) > 0:
            return {"ok": False, "why": "that item cannot be worn"}
        actor.worn[spec["slot"]] = item
    else:
        return {"ok": False, "why": "unknown equipment action"}
    actor.dirty = True
    return {"ok": True, "worn": dict(actor.worn)}
