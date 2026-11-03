"""Anonymous session creation, the public settings the client needs, and deleting yourself."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_anonymous_player
from app.config import get_settings
from app.db import get_session
from app.models import Player
from app.ratelimit import RateLimiter, client_ip
from app.routes.deps import current_player

router = APIRouter(prefix="/api", tags=["auth"])

# Cap anonymous account creation per client IP to blunt DB-spam on a public URL.
_session_limiter = RateLimiter(limit=20, window_s=60)
_new_accounts = RateLimiter(limit=get_settings().new_accounts_per_hour, window_s=3600)
_NAME_STRIP = re.compile(r"[<>&\"'\x00-\x1f]")


class SessionCreate(BaseModel):
    device_id: str = Field(min_length=16, max_length=200)
    name: str = Field(default="Survivor", min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        # Strip HTML-significant + control chars so a name can never inject markup.
        v = _NAME_STRIP.sub("", v).strip()
        return v or "Survivor"


@router.post("/session")
async def create_session(body: SessionCreate, request: Request,
                         session: AsyncSession = Depends(get_session)):
    ip = client_ip(request.headers, request.client, get_settings().trust_proxy)
    if not _session_limiter.allow(ip) or not _new_accounts.allow("all"):
        raise HTTPException(status_code=429, detail="too many sessions, slow down")
    try:
        out = await create_anonymous_player(session, body.device_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    p = out["player"]
    return {"token": out["token"], "player": {"id": p.id, "name": p.name}}


@router.get("/config")
async def public_config():
    """What this server allows. The client asks before it offers GPS or a name box."""
    from app.game.starts import catalog
    cfg = get_settings()
    from app.game.hub import get_hub
    playing = len(get_hub().conns)
    return {"real_gps": cfg.real_gps, "free_text": cfg.free_text, "starts": catalog(),
            "max_players": cfg.max_players, "full": playing >= cfg.max_players}


@router.delete("/me")
async def delete_me(player: Player = Depends(current_player), session: AsyncSession = Depends(get_session)):
    from app.game.hub import get_hub
    # Give the connection back before queueing for the world lock. Whoever holds that lock may need a
    # connection, so fifteen deletes waiting here while holding theirs froze the whole game.
    pid = player.id
    await session.close()
    await get_hub().forget_player(pid)
    return {"ok": True}


@router.get("/backgrounds")
async def background_catalog():
    from app.game.backgrounds import catalog
    return catalog()
