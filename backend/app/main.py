from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.core import security
from app.core.config import settings
from app.db import engine
from app.jobs import scheduler
from app.routers import (
    auth,
    code_practice,
    decks,
    documents,
    export,
    graph,
    imports,
    interference,
    lexicon,
    llm,
    media,
    memory_athlete,
    optimize,
    queue,
    review,
    sessions,
    sources,
    stats,
    sync,
    tree,
)
from app.services import (
    plugins,
    queue_service,  # noqa: F401
    rendering,  # noqa: F401 — registers the §12 seams
)

logging.basicConfig(level=logging.INFO)


async def _auto_migrate() -> None:
    """Runs pending Alembic migrations on startup so fresh installs and git pulls work out of the box.

    A failure is fatal. Carrying on with a half-migrated schema fails later and
    less clearly, one endpoint at a time, and can write rows the next migration
    then trips over.
    """

    def _run():
        from alembic.config import Config

        from alembic import command

        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        if not alembic_ini.is_file():
            return False
        cfg = Config(str(alembic_ini))
        # Keep the server's own logging; see alembic/env.py.
        cfg.attributes["configure_logger"] = False
        command.upgrade(cfg, "head")
        return True

    log = logging.getLogger(__name__)
    try:
        ran = await asyncio.to_thread(_run)
    except Exception as exc:
        log.error(
            "Database migration failed: %s. The app will not start on a schema it "
            "cannot bring up to date. Fix the cause and restart, restore a backup of "
            "the database, or (only if you manage the schema yourself) set AUTO_MIGRATE=0.",
            exc,
        )
        raise RuntimeError(f"database migration failed: {exc}") from exc
    if ran:
        log.info("Database schema is up to date.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.media_root).mkdir(parents=True, exist_ok=True)
    if settings.auto_migrate:
        await _auto_migrate()
    for problem in security.insecure_defaults():
        logging.getLogger(__name__).warning("SECURITY: %s", problem)
    # Plugins load after the first-party strategies, so a plugin can override
    # a built-in rather than racing it (§12).
    plugins.load_all()
    if settings.enable_background_jobs:
        scheduler.start()
    yield
    scheduler.shutdown()
    await engine.dispose()


app = FastAPI(
    title="Memorization",
    version="0.1.0",
    description=(
        "Spaced repetition with FSRS scheduling, LLM-graded typed answers, "
        "hierarchical knowledge tree, priority queue, and incremental reading."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Local dev servers on any port, plus LAN IP ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    # for the mobile companion app on Wi-Fi.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def _security_headers(request, call_next):
    """Baseline browser hardening. Uploaded media is served from this origin,
    so nosniff matters most: a file stored as .png must never be interpreted as
    a page. No CSP here: the app relies on inline styles and one inline script."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


for router in (
    auth.router,
    llm.router,
    code_practice.router,
    decks.router,
    graph.router,
    tree.router,
    queue.router,
    review.router,
    sessions.router,
    sources.router,
    documents.router,
    imports.router,
    media.router,
    interference.router,
    lexicon.router,
    memory_athlete.router,
    stats.router,
    export.router,
    optimize.router,
    sync.router,
):
    app.include_router(router)

Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_root), name="media")


@app.get("/api/plugins")
async def list_plugins() -> dict:
    """What the §12 plugin loader picked up, including anything that failed."""
    from app.services import registry

    return {
        "plugin_dir": settings.plugin_dir or None,
        "enabled": bool(settings.plugin_dir),
        "plugins": [
            {"name": p.name, "path": p.path, "registered": p.registered, "error": p.error}
            for p in plugins.loaded()
        ],
        "seams": {seam: registry.available(seam) for seam in sorted(plugins.ALLOWED_SEAMS)},
    }


@app.get("/health")
async def health() -> dict:
    from app.services.fsrs_service import FSRSService

    return {
        "status": "ok",
        "fsrs_optimizer_installed": FSRSService.optimizer_available(),
        "default_grading_model": settings.default_grading_model,
    }


# ─── Frontend Static SPA Serving ──────────────────────────────────────────────
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir() and (_frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="frontend_assets")


_RESERVED_ROOTS = frozenset({"api", "media", "health", "docs", "openapi.json", "redoc", "assets"})


@app.get("/", include_in_schema=False)
async def serve_root():
    index_file = _frontend_dist / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "status": "ok",
        "message": "Ars Memoriae API is running. Build frontend with 'npm run build' to view the web UI.",
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_route(full_path: str):
    # Do not intercept API, docs, openapi, or media routes. Match whole path
    # segments: a bare prefix test also swallowed client routes such as
    # /apiary or /docs-archive.
    first_segment = full_path.split("/", 1)[0]
    if first_segment in _RESERVED_ROOTS:
        raise HTTPException(status_code=404, detail="Not Found")

    # The path arrives percent-decoded, so `..%2f` becomes a real `../`. Resolve
    # before serving and refuse anything that lands outside the build directory,
    # or this route hands out backend/.env and the database to anyone who asks.
    if full_path:
        dist_root = _frontend_dist.resolve()
        target = (dist_root / full_path).resolve()
        if target.is_relative_to(dist_root) and target.is_file():
            return FileResponse(target)

    index_file = _frontend_dist / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    raise HTTPException(status_code=404, detail="Frontend build index.html not found")

