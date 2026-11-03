"""Anonymous device-token sessions."""
from __future__ import annotations

import hashlib
import random
import secrets
import time

from sqlalchemy import delete, select

from app.config import get_settings
from app.models import Player, SessionToken

# The device_id is a secret bearer credential the client generates, not a hardware identifier.
MIN_DEVICE_ID_LEN = 16


SESSIONS_KEPT = 4
_NAME_A = ("Rusty", "Quiet", "Lucky", "Muddy", "Sleepy", "Brave", "Dusty", "Nimble", "Stubborn", "Hungry",
           "Careful", "Wandering", "Tired", "Patient", "Clumsy", "Cheerful", "Soggy", "Restless", "Thrifty", "Calm")
_NAME_B = ("Otter", "Badger", "Heron", "Fox", "Beetle", "Moose", "Sparrow", "Turtle", "Raccoon", "Hare",
           "Lynx", "Magpie", "Newt", "Owl", "Pigeon", "Stoat", "Toad", "Vole", "Walrus", "Yak")


def hash_device(device_id: str) -> str:
    return hashlib.sha256(f"osz:{device_id}".encode()).hexdigest()


def hash_token(token: str) -> str:
    """Only a digest is stored: a copy of the database or a backup cannot open anyone's session."""
    return hashlib.sha256(f"osz-session:{token}".encode()).hexdigest()


def generated_name() -> str:
    """With free text off nobody types a name, so nothing needs moderating and nobody types their own."""
    r = random.SystemRandom()
    return f"{r.choice(_NAME_A)} {r.choice(_NAME_B)} {r.randint(10, 99)}"


async def create_anonymous_player(session, device_id: str, name: str) -> dict:
    if not device_id or len(device_id) < MIN_DEVICE_ID_LEN:
        raise ValueError("device_id must be a high-entropy secret (>= 16 chars)")
    dt = hash_device(device_id)
    free_text = get_settings().free_text
    player = (await session.execute(
        select(Player).where(Player.device_token == dt))).scalar_one_or_none()
    if player is None:
        player = Player(device_token=dt, name=(name[:40] or "Survivor") if free_text else generated_name())
        session.add(player)
        await session.flush()
    elif free_text and name and name != "Survivor" and name != player.name:
        player.name = name[:40]
    # Old sessions go, so repeated logins cannot grow the table.
    kept = (await session.execute(select(SessionToken.token).where(SessionToken.player_id == player.id)
            .order_by(SessionToken.issued_at.desc()).limit(SESSIONS_KEPT - 1))).scalars().all()
    await session.execute(delete(SessionToken).where(SessionToken.player_id == player.id, SessionToken.token.not_in(kept)))
    token = secrets.token_urlsafe(32)
    session.add(SessionToken(token=hash_token(token), player_id=player.id))
    await session.commit()
    return {"token": token, "player": player}


async def verify_token(session, token: str) -> int | None:
    row = (await session.execute(
        select(SessionToken).where(SessionToken.token == hash_token(token)))).scalar_one_or_none()
    if row is None or row.expires_at < int(time.time()):
        return None
    return row.player_id
