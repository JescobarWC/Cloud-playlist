from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domain.imports import create_import_job

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


class CreateImportRequest(BaseModel):
    connector: str = Field(..., description="Source connector (rekordbox, serato, m3u, csv, virtualdj)")
    source_uri: str = Field(..., description="Path or URI to source library data")


class CreateImportResponse(BaseModel):
    job_id: str
    connector: str
    source_uri: str
    status: str
    created_at: str


@router.post("", response_model=CreateImportResponse, status_code=202)
def create_import(payload: CreateImportRequest) -> CreateImportResponse:
    try:
        job = create_import_job(payload.connector, payload.source_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateImportResponse(
        job_id=job.id,
        connector=job.connector.value,
        source_uri=job.source_uri,
        status=job.status,
        created_at=job.created_at,
    )
