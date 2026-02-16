from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domain.imports import create_import_job
from app.infrastructure.import_jobs_repository import get_import_jobs_repository

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


class CreateImportRequest(BaseModel):
    connector: str = Field(..., description="Source connector (rekordbox, serato, m3u, csv, virtualdj)")
    source_uri: str = Field(..., description="Path or URI to source library data")


class ImportJobResponse(BaseModel):
    job_id: str
    connector: str
    source_uri: str
    status: str
    created_at: str


@router.post("", response_model=ImportJobResponse, status_code=202)
def create_import(payload: CreateImportRequest) -> ImportJobResponse:
    try:
        job = create_import_job(payload.connector, payload.source_uri)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository = get_import_jobs_repository()
    repository.save(job)

    return ImportJobResponse(
        job_id=job.id,
        connector=job.connector.value,
        source_uri=job.source_uri,
        status=job.status,
        created_at=job.created_at,
    )


@router.get("/{job_id}", response_model=ImportJobResponse)
def get_import(job_id: str) -> ImportJobResponse:
    repository = get_import_jobs_repository()
    job = repository.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Import job '{job_id}' was not found")

    return ImportJobResponse(
        job_id=job.id,
        connector=job.connector.value,
        source_uri=job.source_uri,
        status=job.status,
        created_at=job.created_at,
    )
