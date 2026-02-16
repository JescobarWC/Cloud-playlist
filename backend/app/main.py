from fastapi import FastAPI

from app.api.v1.imports import router as imports_router
from app.api.v1.normalize import router as normalize_router
from app.api.v1.virtualdj import router as virtualdj_router
from app.api.v1.playlists import router as playlists_router
from app.api.v1.playback import router as playback_router

app = FastAPI(
    title="DJ Library & Bridge Platform API",
    version="0.3.0",
    description=(
        "Backend API for importing, normalizing, and exporting DJ library data "
        "across Rekordbox, Serato, VirtualDJ, and open formats."
    ),
)

app.include_router(imports_router)
app.include_router(normalize_router)
app.include_router(virtualdj_router)
app.include_router(playlists_router)
app.include_router(playback_router)


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    """Simple service health endpoint used by local/dev orchestration."""
    return {"status": "ok"}
