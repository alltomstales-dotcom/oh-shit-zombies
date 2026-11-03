"""Database tables. Small on purpose: a survivor's whole body and pack is one JSON document."""
from __future__ import annotations

import time

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> int:
    return int(time.time())


class Player(Base):
    """A person (one device). Survivors come and go; the player stays."""
    __tablename__ = "player"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[int] = mapped_column(BigInteger, default=_now)
    last_seen: Mapped[int] = mapped_column(BigInteger, default=_now)


class SessionToken(Base):
    __tablename__ = "session_token"
    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    issued_at: Mapped[int] = mapped_column(BigInteger, default=_now)
    expires_at: Mapped[int] = mapped_column(BigInteger, default=lambda: _now() + 86400 * 90)


class Survivor(Base):
    """One life. `state` is the simulation's Actor, saved whole."""
    __tablename__ = "survivor"
    __table_args__ = (Index("ix_survivor_player_alive", "player_id", "alive"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    name: Mapped[str] = mapped_column(String(40), default="Survivor")
    alive: Mapped[bool] = mapped_column(Boolean, default=True)
    born: Mapped[float] = mapped_column(Float, default=lambda: time.time())
    died_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen: Mapped[float] = mapped_column(Float, default=lambda: time.time())
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    death: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class PlayerHome(Base):
    """Owner storage/world investment survives individual survivor lives."""
    __tablename__ = "player_home"
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class PlayerMemory(Base):
    """What a player remembers of the map. It outlives survivors, like the home does."""
    __tablename__ = "player_memory"
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class BaseMembership(Base):
    """Explicit permission, separate from survivor lives and display names."""
    __tablename__ = "base_membership"
    owner_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(12), default="builder")


class BaseSelection(Base):
    __tablename__ = "base_selection"
    player_id: Mapped[int] = mapped_column(ForeignKey("player.id"), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("player.id"))


class BaseInvite(Base):
    """Only a digest is retained. Rotating/revoking invalidates older invitations."""
    __tablename__ = "base_invite"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("player.id"), index=True)
    role: Mapped[str] = mapped_column(String(12))
    expires_at: Mapped[float] = mapped_column(Float)


class ZedDead(Base):
    """A zombie somebody killed: it stays dead for everyone until `until`."""
    __tablename__ = "zed_dead"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    until: Mapped[float] = mapped_column(Float, index=True)


class WorldCorpse(Base):
    """Conserved aftermath: shared zombie loot and owner recovery packs with explicit expiry."""
    __tablename__ = "world_corpse"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    until: Mapped[float] = mapped_column(Float, index=True)
    revision: Mapped[int] = mapped_column(default=1)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class WorldVehicle(Base):
    __tablename__ = "world_vehicle"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    revision: Mapped[int] = mapped_column(default=1)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class BuildingRegion(Base):
    """Cached OSM footprints or explicitly generated fallback shelters."""
    __tablename__ = "building_region"
    id: Mapped[str] = mapped_column(String(6), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="osm")
    expires_at: Mapped[float] = mapped_column(Float)
    records: Mapped[list] = mapped_column(JSON, default=list)


class BuildingOpening(Base):
    """Shared doors/windows survive app replacement independently of survivors."""
    __tablename__ = "building_opening"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class BuildingLevel(Base):
    """Shared fictional upper-floor openings persist independently of survivor lives."""
    __tablename__ = "building_level"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)


class WorldEvent(Base):
    __tablename__ = "world_events"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    fired_at: Mapped[float] = mapped_column(Float, nullable=False)
