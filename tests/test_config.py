import pytest
from app.config import Settings


def test_production_requires_persistent_postgres():
    with pytest.raises(ValueError, match="persistent PostgreSQL"):
        Settings(env="prod", secret_key="x" * 32, database_url="sqlite+aiosqlite:///:memory:")
    cfg = Settings(env="prod", secret_key="x" * 32, database_url="postgresql://u:p@db/osz")
    assert cfg.database_url == "postgresql+asyncpg://u:p@db/osz"
