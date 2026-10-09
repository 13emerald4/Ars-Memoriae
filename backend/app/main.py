from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.core import security
from app.core.config import settings
from app.jobs import scheduler
from app.routers import (
    auth,
    code_practice,
    decks,
    documents,
    export,
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
    tree,
)
from app.services import (
    plugins,
    queue_service,  # noqa: F401
    rendering,  # noqa: F401 — registers the §12 seams
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.media_root).mkdir(parents=True, exist_ok=True)
    for problem in security.insecure_defaults():
        logging.getLogger(__name__).warning("SECURITY: %s", problem)
    # Plugins load after the first-party strategies, so a plugin can override
    # a built-in rather than racing it (§12).
    plugins.load_all()
    if settings.enable_background_jobs:
        scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Memorization",
    version="0.1.0",
    description=(
        "Spaced repetition with FSRS scheduling, LLM-graded typed answers, "
        "SuperMemo-style priority queue, and incremental reading."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.trycloudflare\.com|.*\.loca\.lt)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    llm.router,
    code_practice.router,
    decks.router,
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
    # Do not intercept API, docs, openapi, or media routes
    if full_path.startswith(("api", "media", "health", "docs", "openapi.json", "redoc")):
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

