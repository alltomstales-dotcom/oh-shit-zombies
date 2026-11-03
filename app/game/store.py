"""Saving and loading: survivors (one JSON document each) and the zombies that are dead."""
from __future__ import annotations

import time

from sqlalchemy import delete, select, update, func, event
from sqlalchemy.orm import Session

from app.game.content import STARTER_KIT, TUNE, ITEMS
from app.game.sim import Actor
from app.models import Survivor, ZedDead, PlayerHome, BaseMembership, BaseSelection
import copy

_KEEP = ("lat", "lng", "hp", "end", "wounds", "items", "hands", "born", "infected_at", "turns_at",
         "hunger", "thirst", "sleep", "lantern", "worn", "remains", "background", "kills", "walked_m", "building_searches", "loot_shelves", "loot_receipts", "xp", "skill_xp", "training_m", "explored", "study", "studied", "knowledge", "learned_media", "placed_at", "placement_epoch", "floor_level", "floor_building", "floor_epoch", "gps_anchor", "_next_item_id", "_next_wound_id")
HEAL_AFTER_H = {"scratch": 6.0, "laceration": 24.0, "bite": 72.0}

@event.listens_for(Session,'after_commit')
def _committed_home_versions(session):
    for home,version in session.info.pop('osz_home_versions',[]):home['_base_version']=version

@event.listens_for(Session,'after_rollback')
def _discard_home_versions(session):session.info.pop('osz_home_versions',None)

async def save_home(session,a):
    if a.home is None:return
    owner=a.home_owner or a.id
    if owner!=a.id:
        member=await session.get(BaseMembership,(owner,a.id))
        selected=await session.get(BaseSelection,a.id)
        if member is None or selected is None or selected.owner_id!=owner or member.role!=a.base_role:
            raise PermissionError('shared base access changed')
    row=await session.get(PlayerHome,owner,populate_existing=True)
    if not a.home.get('_shared'):
        if row is None:row=PlayerHome(player_id=owner);session.add(row)
        if row.state and row.state.get('_shared'):raise RuntimeError('shared base must be rebound before saving')
        row.state=copy.deepcopy(a.home);return
    state=copy.deepcopy(a.home);expected=state.pop('_base_version',0)
    if row is None:
        version=1;state['_base_version']=version
        session.add(PlayerHome(player_id=owner,state=state))
    else:
        current=copy.deepcopy(row.state);version=current.pop('_base_version',0)
        if current!=state:
            version=expected+1;state['_base_version']=version
            res=await session.execute(update(PlayerHome).where(PlayerHome.player_id==owner,
                func.coalesce(PlayerHome.state['_base_version'].as_integer(),0)==expected)
                .values(state=state).execution_options(synchronize_session=False))
            if res.rowcount!=1:raise RuntimeError('shared base changed; refresh before saving')
    session.info.setdefault('osz_home_versions',[]).append((a.home,version))


def to_state(a: Actor) -> dict:
    d = {k: getattr(a, k) for k in _KEEP}
    d["claimed"] = sorted(a.claimed)
    return copy.deepcopy(d)


def from_state(row: Survivor, name: str) -> Actor:
    s = row.state or {}
    a = Actor(id=row.player_id, life_id=getattr(row,'id',0), name=name, born=row.born)
    for k in _KEEP:
        if k in s:
            setattr(a, k, s[k])
    a.claimed = set(s.get("claimed", []))
    return a


def starter(player_id: int, name: str, now: float, lat: float = 0.0, lng: float = 0.0) -> Actor:
    a = Actor(id=player_id, name=name, born=now, lat=lat, lng=lng)
    for code, qty in STARTER_KIT:
        row = a.add(code, qty)
        if code == "bat":
            a.hands = row["id"]
    for code in ("shirt","pants","boots","schoolbag"):
        row=a.add(code);a.worn[ITEMS[code]["slot"]]=row["id"]
    return a


def apply_time_away(a: Actor, away_s: float, now: float, tune: dict = TUNE) -> dict:
    """What happened to the body while the game was closed. Returns a short report."""
    rep = {"away_s": round(away_s), "healed": 0.0, "bled": 0.0, "closed": 0, "turned": False}
    if a.turns_at is not None and now >= a.turns_at:
        rep["turned"] = True
        return rep
    # Offline needs are capped and cannot silently kill a returning player.
    capped=min(1800,max(0,away_s))
    a.hunger=min(75,a.hunger+capped/90)
    a.thirst=min(75,a.thirst+capped/60)
    a.sleep=max(0,a.sleep-min(40,away_s/120))
    bleed_s = min(away_s, tune["offline_bleed_cap_s"])
    for w in a.wounds:
        if w["bleeding"]:
            rate = tune["bleed"][w["kind"]] * (tune["neck_bleed_mult"] if w["part"] == "neck" else 1.0)
            rep["bled"] += rate * bleed_s
            if away_s >= tune["offline_bleed_cap_s"]:
                w["bleeding"] = False            # held a rag to it until it stopped
    a.hp = max(5.0, a.hp - rep["bled"])
    if away_s > 600:
        gain = min(tune["hp_max"] - a.hp, tune["offline_heal_per_h"] * away_s / 3600.0)
        a.hp += max(0.0, gain)
        rep["healed"] = round(max(0.0, gain), 1)
        keep = []
        for w in a.wounds:
            age_h = (now - w["t"]) / 3600.0
            if not w["bleeding"] and age_h >= HEAL_AFTER_H[w["kind"]] * (0.75 if w["clean"] else 1.0):
                rep["closed"] += 1
            else:
                keep.append(w)
        a.wounds = keep
    if away_s > 60:
        a.end, a.panic = tune["end_max"], 0.0
    rep["bled"] = round(rep["bled"], 1)
    return rep


async def load_or_create(session, player, now: float | None = None) -> tuple[Actor, Survivor, dict | None]:
    """The player's living survivor, or a fresh one. Third value: what happened while away."""
    now = time.time() if now is None else now
    row = (await session.execute(select(Survivor).where(
        Survivor.player_id == player.id, Survivor.alive.is_(True))
        .order_by(Survivor.id.desc()).limit(1))).scalar_one_or_none()
    if row is None:
        a = starter(player.id, player.name, now)
        row = Survivor(player_id=player.id, name=player.name, born=now, last_seen=now, state=to_state(a))
        session.add(row)
        await session.commit()
        a.life_id=row.id
        return a, row, None
    a = from_state(row, player.name)
    report = apply_time_away(a, max(0.0, now - row.last_seen), now)
    return a, row, report


async def save(session, a: Actor, survivor_id: int, now: float | None = None, *, commit=True):
    now = time.time() if now is None else now
    row = await session.get(Survivor, survivor_id)
    if row is None:
        if not commit:raise LookupError('survivor disappeared during shared transfer')
        return
    if a.dead and row.alive:
        from app.game import corpses
        a.life_id=survivor_id
        body=corpses.survivor(a,now)
        await corpses.save_new(session,[body],[],commit=False)
    row.state = to_state(a)
    row.last_seen = now
    if a.dead and row.alive:
        row.alive, row.died_at, row.death = False, now, a.death
    await save_home(session,a)
    if commit:
        await session.commit()
        a.dirty = False


async def last_death(session, player_id: int) -> dict | None:
    row = (await session.execute(select(Survivor).where(
        Survivor.player_id == player_id, Survivor.alive.is_(False))
        .order_by(Survivor.id.desc()).limit(1))).scalar_one_or_none()
    return row.death if row else None


async def load_dead(session, now: float) -> dict[str, float]:
    await session.execute(delete(ZedDead).where(ZedDead.until < now))
    await session.commit()
    rows = (await session.execute(select(ZedDead))).scalars().all()
    return {r.id: r.until for r in rows}


async def save_dead(session, rows: list[tuple[str, float]]):
    for zid, until in rows:
        if await session.get(ZedDead, zid) is None:
            session.add(ZedDead(id=zid, until=until))
    await session.commit()
