from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.infrastructure.repository_factory import get_library_repo

router = APIRouter(prefix="/api/v1/playlists/{playlist_id}/playback", tags=["playback"])


class SeekRequest(BaseModel):
    position_seconds: float = Field(..., ge=0)


class LoadTrackRequest(BaseModel):
    track_id: int


class PlaybackStateResponse(BaseModel):
    playlist_id: int
    track_ids: list[int]
    current_track_id: int | None
    current_position_seconds: float
    is_playing: bool
    current_index: int | None


@router.get("", response_model=PlaybackStateResponse)
def get_playback_state(playlist_id: int) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.get_playback_state(playlist_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlaybackStateResponse(**state)


@router.post("/play", response_model=PlaybackStateResponse)
def play(playlist_id: int) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.set_playing(playlist_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlaybackStateResponse(**state)


@router.post("/pause", response_model=PlaybackStateResponse)
def pause(playlist_id: int) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.set_playing(playlist_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlaybackStateResponse(**state)


@router.post("/seek", response_model=PlaybackStateResponse)
def seek(playlist_id: int, payload: SeekRequest) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.seek(playlist_id, payload.position_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlaybackStateResponse(**state)


@router.post("/next", response_model=PlaybackStateResponse)
def next_track(playlist_id: int) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.move_track(playlist_id, "next")
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message) from exc
    return PlaybackStateResponse(**state)


@router.post("/previous", response_model=PlaybackStateResponse)
def previous_track(playlist_id: int) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.move_track(playlist_id, "previous")
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message) from exc
    return PlaybackStateResponse(**state)


@router.post("/load", response_model=PlaybackStateResponse)
def load_track(playlist_id: int, payload: LoadTrackRequest) -> PlaybackStateResponse:
    repository = get_library_repo()
    try:
        state = repository.set_current_track(playlist_id, payload.track_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        raise HTTPException(status_code=status, detail=message) from exc
    return PlaybackStateResponse(**state)
