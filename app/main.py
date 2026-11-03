"""FastAPI application: tables, the game loop, the socket and the static client."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from urllib.parse import urlsplit

from app.config import get_settings
from app.db import Base, get_engine
import app.models  # noqa: F401  register models on Base
from app.routes import auth_routes, ws_routes

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
VERSION = "0.18.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from app.game.hub import get_hub
    hub = get_hub()
    await hub.start()
    from app.game.siege_hub import get_siege_hub
    sieges = get_siege_hub()
    await sieges.start()
    try:
        yield
    finally:
        await sieges.stop()
        await hub.stop()


class NoCacheStatic(StaticFiles):
    """Code and pages are always revalidated, so a deploy reaches phones at once; art is cached."""
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if path.endswith((".html", ".js", ".css", ".webmanifest")) or path in ("", "."):
            resp.headers["Cache-Control"] = "no-cache"
        else:
            resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp


class SecurityHeaders:
    """What a browser may do on this site. Geolocation is refused here as well as in the client."""
    def __init__(self, app):
        self.app = app
        cfg = get_settings()
        tiles = urlsplit(cfg.tile_url).netloc.replace("{s}", "*")
        tile_src = f"https://{tiles}" if tiles else ""
        csp = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
               f"img-src 'self' data: blob: {tile_src}; connect-src 'self'; media-src 'self' blob:; "
               "frame-src https://www.youtube-nocookie.com; object-src 'none'; base-uri 'none'; "
               "form-action 'none'; frame-ancestors 'none'")
        geo = "(self)" if cfg.real_gps else "()"
        self.headers = [(b"content-security-policy", csp.encode()),
                        (b"permissions-policy", f"geolocation={geo}, camera=(), microphone=(), payment=()".encode()),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY")]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def with_headers(message):
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *self.headers]
            await send(message)
        await self.app(scope, receive, with_headers)


def create_app() -> FastAPI:
    # No schema or API explorer on a public server; there is nothing a visitor needs from them.
    app = FastAPI(title="Oh shit, Zombies.", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SecurityHeaders)
    app.include_router(auth_routes.router)
    app.include_router(ws_routes.router)

    @app.get("/healthz")
    async def healthz():
        return {"ok": True, "version": VERSION}

    # Static client mounted LAST so /api and /ws take precedence. html=True serves index.html.
    if os.path.isdir(STATIC_DIR):
        app.mount("/", NoCacheStatic(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
