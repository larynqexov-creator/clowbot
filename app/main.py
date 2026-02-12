from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI
from redis import Redis
from sqlalchemy import text

from app.api.routers.actions import router as actions_router
from app.api.routers.admin import router as admin_router
from app.api.routers.mindmap import router as mindmap_router
from app.api.routers.outbox import router as outbox_router
from app.api.routers.science_grants import router as science_grants_router
from app.api.routers.skills import router as skills_router
from app.api.routers.tasks import router as tasks_router
from app.api.routers.tools import router as tools_router
from app.core.config import settings
from app.core.db import engine
from app.core.logging import configure_logging
from app.memory.object_store import ensure_minio_bucket, minio_ready
from app.memory.vector_store import ensure_qdrant_collection, qdrant_ready

configure_logging(settings.LOG_LEVEL)
log = logging.getLogger("app")

app = FastAPI(title=settings.APP_NAME)


def _retry_backoff(fn, *, attempts: int = 30, base_sleep_s: float = 1.0, max_sleep_s: float = 2.0, what: str) -> bool:
    sleep_s = base_sleep_s
    for i in range(1, attempts + 1):
        try:
            fn()
            return True
        except Exception as e:
            if i == attempts:
                log.error("Startup: %s still not ready after %s attempts: %s", what, attempts, str(e))
                return False
            log.warning("Startup: %s not ready (attempt %s/%s): %s", what, i, attempts, str(e))
            time.sleep(sleep_s)
            sleep_s = min(max_sleep_s, sleep_s * 2.0)
    return False


def _check_postgres() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
        return bool(r.ping())
    except Exception:
        return False


@app.on_event("startup")
def _startup() -> None:
    # Do not crash API if deps are temporarily unavailable.
    # In CI/unit tests we skip these to avoid slow retries/hangs.
    if not settings.ENSURE_EXTERNAL_DEPS_ON_STARTUP:
        log.info("Startup: ENSURE_EXTERNAL_DEPS_ON_STARTUP=false; skipping qdrant/minio ensure")
        return

    _retry_backoff(lambda: ensure_qdrant_collection(), what="qdrant")
    _retry_backoff(lambda: ensure_minio_bucket(), what="minio")


@app.get("/health")
def health() -> dict[str, Any]:
    deps = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "qdrant": qdrant_ready(),
        "minio": minio_ready(),
    }
    return {"ok": all(deps.values()), "deps": deps, "app": settings.APP_NAME}


app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(science_grants_router, prefix="/science/grants", tags=["science-grants"])
app.include_router(mindmap_router, prefix="/mindmap", tags=["mindmap"])
app.include_router(actions_router, prefix="/actions", tags=["actions"])
app.include_router(outbox_router, prefix="/outbox", tags=["outbox"])
app.include_router(skills_router, prefix="/skills", tags=["skills"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])
