import os

# The suite predates the public defaults and exercises real GPS and typed names; test_public_build covers the defaults.
os.environ.setdefault("REAL_GPS", "1")
os.environ.setdefault("FREE_TEXT", "1")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db as db
from app.db import Base
import app.models  # noqa: F401  ensure models register on Base


@pytest_asyncio.fixture
async def maker(monkeypatch):
    """An isolated in-memory database wired in as the app's sessionmaker."""
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool,
                                 connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    m = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(db, "_engine", engine)
    monkeypatch.setattr(db, "_sessionmaker", m)
    from app.game import hub
    hub.reset_hub()
    yield m
    hub.reset_hub()
    await engine.dispose()


@pytest.fixture(autouse=True)
def _no_map_retry_wait(monkeypatch):
    """Map-server retries wait for real seconds in production; tests should not."""
    from app.game import building_loader
    monkeypatch.setattr(building_loader, "RETRY_DELAYS", (0.001,))


@pytest.fixture(autouse=True)
def calm_sky(request, monkeypatch):
    """Every test runs under a dry sky with no helicopter and no herd on the roads, except the
    tests about the weather and the tests about herds.

    Rain, the helicopter and herds are pure functions of place and time, so without this an
    unrelated test would change its result with the clock value it happens to use.
    """
    from app.game import herds, weather
    from app.game.content import TUNE
    if not request.module.__name__.endswith("test_weather"):
        monkeypatch.setitem(TUNE, "rain_chance", 0.0)
        monkeypatch.setitem(TUNE, "heli_chance", 0.0)
    if not request.module.__name__.endswith("test_herds"):
        monkeypatch.setitem(TUNE, "herd_chance", 0.0)
    for cached in (weather._rain_block, weather._heli_window, herds._crossing):
        cached.cache_clear()
    yield
    for cached in (weather._rain_block, weather._heli_window, herds._crossing):
        cached.cache_clear()

