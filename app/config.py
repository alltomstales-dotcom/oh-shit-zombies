"""Environment-driven settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./osz.db"
    secret_key: str = "dev-secret-change-me"
    admin_key: str = ""               # set ADMIN_KEY to enable admin routes
    zed_density: float | None = None  # overrides the difficulty profile's zombie packs per map cell
    difficulty: str = "classic"       # classic (the Railway tuning) | public: see app/game/difficulty.py
    difficulty_tune: str = ""         # JSON dial overrides on top of the profile, for bot sweeps
    typesafe_api_key: str = ""        # optional: lets the Jev model choose the director's beats
    env: str = "dev"  # set ENV=prod on Railway
    tile_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    tile_max_z: int = 19
    tile_dark: bool = True          # grey and darken the tiles in the browser
    tile_credit: str = "© OpenStreetMap contributors"
    # Public server defaults. Real GPS and free text are opt-in; the Railway build sets both on.
    real_gps: bool = False          # ask for and store real device location
    free_text: bool = False         # let players type names; off means generated names
    trust_proxy: str = "none"       # none | cloudflare | railway: whose client-IP header to believe
    max_players: int = 25           # concurrent survivors (this machine holds 25; 30 is the edge); more see "server full"
    max_conns_per_ip: int = 6
    new_accounts_per_hour: int = 600
    retention_days: int = 90        # anonymous accounts unseen for this long are deleted
    base_url: str = ""              # public address, used to identify the game to the map servers

    @model_validator(mode="after")
    def _normalize_db(self):
        u = self.database_url
        if u.startswith("postgres://"):
            u = "postgresql+asyncpg://" + u[len("postgres://"):]
        elif u.startswith("postgresql://"):
            u = "postgresql+asyncpg://" + u[len("postgresql://"):]
        object.__setattr__(self, "database_url", u)
        return self

    @model_validator(mode="after")
    def _guard_prod_secret(self):
        weak = {"dev-secret-change-me", "change-me-in-prod"}
        if self.env == "prod" and (self.secret_key in weak or len(self.secret_key) < 16):
            raise ValueError("SECRET_KEY must be a strong (>=16 char) value in production")
        if self.env == "prod" and not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Production requires a persistent PostgreSQL DATABASE_URL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
