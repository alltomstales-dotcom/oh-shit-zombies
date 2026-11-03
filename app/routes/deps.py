"""Shared route dependencies."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_token
from app.db import get_session
from app.models import Player


async def current_player(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> Player:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    player_id = await verify_token(session, token)
    if player_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    player = await session.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=401, detail="player not found")
    return player
