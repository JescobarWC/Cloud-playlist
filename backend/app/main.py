from fastapi import FastAPI

from app.api.v1.imports import router as imports_router

app = FastAPI(
    title="DJ Library & Bridge Platform API",
    version="0.2.0",
    description=(
        "Backend API for importing, normalizing, and exporting DJ library data "
        "across Rekordbox, Serato, VirtualDJ, and open formats."
    ),
)

app.include_router(imports_router)


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    """Simple service health endpoint used by local/dev orchestration."""
    return {"status": "ok"}
