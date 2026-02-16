from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.infrastructure.repository_factory import get_library_repo

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class DuplicateGroup(BaseModel):
    title: str
    artist: str
    track_count: int
    track_ids: list[int]


class FindReplaceRequest(BaseModel):
    field_name: str = Field(..., description="title | artist")
    search_text: str = Field(..., min_length=1)
    replace_text: str
    apply: bool = False


class FindReplacePreviewItem(BaseModel):
    track_id: int
    old_value: str
    new_value: str


class FindReplaceResponse(BaseModel):
    operation_id: str | None = None
    changed_tracks: int
    preview: list[FindReplacePreviewItem]


class UndoResponse(BaseModel):
    operation_id: str
    restored_tracks: int


@router.get("/duplicates", response_model=list[DuplicateGroup])
def find_duplicates() -> list[DuplicateGroup]:
    repository = get_library_repo()
    return [DuplicateGroup(**item) for item in repository.find_duplicate_tracks()]


@router.post("/find-replace", response_model=FindReplaceResponse)
def find_replace(payload: FindReplaceRequest) -> FindReplaceResponse:
    repository = get_library_repo()
    try:
        preview = repository.preview_find_replace(payload.field_name, payload.search_text, payload.replace_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not payload.apply:
        return FindReplaceResponse(changed_tracks=len(preview), preview=[FindReplacePreviewItem(**x) for x in preview])

    operation_id = str(uuid4())
    result = repository.apply_find_replace(operation_id, payload.field_name, payload.search_text, payload.replace_text)
    return FindReplaceResponse(
        operation_id=operation_id,
        changed_tracks=int(result["changed_tracks"]),
        preview=[FindReplacePreviewItem(**x) for x in preview],
    )


@router.post("/find-replace/{operation_id}/undo", response_model=UndoResponse)
def undo_find_replace(operation_id: str) -> UndoResponse:
    repository = get_library_repo()
    try:
        result = repository.undo_find_replace(operation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UndoResponse(operation_id=operation_id, restored_tracks=int(result["restored_tracks"]))
