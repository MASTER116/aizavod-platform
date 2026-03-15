from __future__ import annotations

import logging
import os
import time as _time
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import Response

from .config import get_backend_api_key, get_log_level
from .database import init_db

logger = logging.getLogger("aizavod")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _setup_logging() -> None:
    level = getattr(logging, get_log_level(), logging.INFO)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger("aizavod")
    root.handlers.clear()
    root.setLevel(level)
    root.propagate = False

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if not os.getenv("RENDER"):
        log_dir = _PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        file_h = RotatingFileHandler(
            log_dir / "aizavod.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_h.setFormatter(fmt)
        root.addHandler(file_h)

    logger.info("Logging configured (level=%s)", logging.getLevelName(level))


def _ensure_media_dirs() -> None:
    for subdir in ("reference", "generated", "processed"):
        (_PROJECT_ROOT / "media" / subdir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app):
    _setup_logging()
    _ensure_media_dirs()
    init_db()

    # Ensure default SystemSettings row exists
    from .database import SessionLocal
    from .models import SystemSettings

    db = SessionLocal()
    try:
        settings = db.query(SystemSettings).first()
        if not settings:
            db.add(SystemSettings(id=1))
            db.commit()
            logger.info("Created default SystemSettings")
    finally:
        db.close()

    # Start scheduler (APScheduler or Celery)
    from .config import get_celery_config

    celery_cfg = get_celery_config()
    if celery_cfg.use_celery:
        logger.info("USE_CELERY=true — tasks managed by Celery worker + beat")
    else:
        from services.scheduler import start_scheduler
        start_scheduler()
        logger.info("Scheduler started (APScheduler mode)")

    # Telegram bot runs as separate container (telegram-bot service)
    # Do NOT start it here to avoid getUpdates conflict

    logger.info("AIZAVOD backend started")
    yield

    # Cleanup
    if not celery_cfg.use_celery:
        from services.scheduler import stop_scheduler
        stop_scheduler()
    logger.info("AIZAVOD backend shutting down")


app = FastAPI(title="AIZAVOD - AI Instagram Factory", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_BACKEND_API_KEY = get_backend_api_key()
_PUBLIC_PREFIXES = ("/health", "/admin", "/docs", "/openapi.json", "/redoc", "/api/certifier", "/api/opportunities", "/api/conductor")


@app.middleware("http")
async def check_api_key(request: Request, call_next) -> Response:
    path = request.url.path
    if _BACKEND_API_KEY and not any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        key = request.headers.get("X-API-Key", "")
        if key != _BACKEND_API_KEY:
            return Response(
                content='{"detail":"Forbidden"}',
                status_code=403,
                media_type="application/json",
            )
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    if request.url.path == "/health":
        return await call_next(request)
    start = _time.perf_counter()
    response = await call_next(request)
    duration_ms = (_time.perf_counter() - start) * 1000
    logger.info(
        "%s %s %s %.0fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ─── Health ─────────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ─── Serve media files ──────────────────────────────────────────────────────

_media_dir = _PROJECT_ROOT / "media"
if _media_dir.exists():
    app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")


# ─── Routes ─────────────────────────────────────────────────────────────────

from .routes import (  # noqa: E402
    admin, characters, settings, content, posts, instagram,
    analytics, comments, monetization, webhooks,
    agent, dms, deals,
)

app.include_router(admin.router)
app.include_router(characters.router)
app.include_router(settings.router)
app.include_router(content.router)
app.include_router(posts.router)
app.include_router(instagram.router)
app.include_router(analytics.router)
app.include_router(comments.router)
app.include_router(monetization.router)
app.include_router(webhooks.router)
app.include_router(agent.router)
app.include_router(dms.router)
app.include_router(deals.router)

from .routes.certifier import router as certifier_router
app.include_router(certifier_router)

from .routes.opportunities import router as opportunities_router
app.include_router(opportunities_router)

from .routes.conductor import router as conductor_router
app.include_router(conductor_router)
