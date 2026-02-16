import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Response
from starlette.requests import Request

from app.api.v1.analysis_jobs import router as analysis_jobs_router
from app.api.v1.imports import router as imports_router
from app.api.v1.normalize import router as normalize_router
from app.api.v1.playback import router as playback_router
from app.api.v1.playlists import router as playlists_router
from app.api.v1.tools import router as tools_router
from app.api.v1.virtualdj import router as virtualdj_router
from app.core.settings import get_settings
from app.infrastructure.repository_factory import get_library_repo

logger = logging.getLogger("app.api")

app = FastAPI(
    title="DJ Library & Bridge Platform API",
    version="0.3.0",
    description=(
        "Backend API for importing, normalizing, and exporting DJ library data "
        "across Rekordbox, Serato, VirtualDJ, and open formats."
    ),
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid4())

    response = await call_next(request)
    response.headers["x-request-id"] = request_id

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(imports_router)
app.include_router(normalize_router)
app.include_router(virtualdj_router)
app.include_router(playlists_router)
app.include_router(playback_router)
app.include_router(analysis_jobs_router)
app.include_router(tools_router)


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    """Simple service health endpoint used by local/dev orchestration."""
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def readiness(response: Response) -> dict[str, str]:
    """Readiness check verifying configured backend can be reached."""
    settings = get_settings()
    backend = settings.storage_backend

    try:
        repo = get_library_repo()
        if hasattr(repo, "engine"):
            with repo.engine.connect() as conn:  # type: ignore[attr-defined]
                conn.exec_driver_sql("SELECT 1")
        elif hasattr(repo, "_connect"):
            with repo._connect() as conn:  # type: ignore[attr-defined]
                conn.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover - defensive runtime safety
        response.status_code = 503
        return {"status": "not_ready", "backend": backend, "checks": {"storage": "error"}, "error": str(exc)}

    return {"status": "ready", "backend": backend, "checks": {"storage": "ok"}}
