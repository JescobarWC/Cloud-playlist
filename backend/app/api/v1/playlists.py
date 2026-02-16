from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domain.audio_analysis import analyze_audio_file
from app.infrastructure.library_repository import get_library_repository

router = APIRouter(prefix="/api/v1", tags=["playlists", "analysis"])


class CreatePlaylistRequest(BaseModel):
    name: str = Field(..., min_length=1)


class CreatePlaylistResponse(BaseModel):
    playlist_id: int
    name: str


class AddTrackRequest(BaseModel):
    title: str = Field(..., min_length=1)
    artist: str = Field(..., min_length=1)
    file_path: str = Field(..., min_length=1)


class AddTrackResponse(BaseModel):
    track_id: int
    playlist_id: int


class TrackAnalysisResponse(BaseModel):
    track_id: int
    bpm: float | None
    key: str | None
    waveform: list[float]
    duration_seconds: float


@router.post("/playlists", response_model=CreatePlaylistResponse, status_code=201)
def create_playlist(payload: CreatePlaylistRequest) -> CreatePlaylistResponse:
    repository = get_library_repository()
    playlist_id = repository.create_playlist(payload.name)
    return CreatePlaylistResponse(playlist_id=playlist_id, name=payload.name)


@router.post("/playlists/{playlist_id}/tracks", response_model=AddTrackResponse, status_code=201)
def add_track_to_playlist(playlist_id: int, payload: AddTrackRequest) -> AddTrackResponse:
    repository = get_library_repository()
    try:
        track_id = repository.add_track_to_playlist(
            playlist_id=playlist_id,
            title=payload.title,
            artist=payload.artist,
            file_path=payload.file_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return AddTrackResponse(track_id=track_id, playlist_id=playlist_id)


@router.get("/playlists/{playlist_id}")
def get_playlist(playlist_id: int) -> dict[str, object]:
    repository = get_library_repository()
    playlist = repository.get_playlist(playlist_id)
    if playlist is None:
        raise HTTPException(status_code=404, detail=f"Playlist '{playlist_id}' not found")
    return playlist


@router.post("/tracks/{track_id}/analyze", response_model=TrackAnalysisResponse)
def analyze_track(track_id: int) -> TrackAnalysisResponse:
    repository = get_library_repository()
    track = repository.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail=f"Track '{track_id}' not found")

    try:
        analysis = analyze_audio_file(str(track["file_path"]))
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    waveform = [round(float(v), 6) for v in analysis["waveform"]]
    bpm = analysis["bpm"]
    key = analysis["key"]
    repository.save_track_analysis(track_id=track_id, bpm=bpm, musical_key=key, waveform_json=json.dumps(waveform))

    return TrackAnalysisResponse(
        track_id=track_id,
        bpm=bpm,
        key=key,
        waveform=waveform,
        duration_seconds=float(analysis["duration_seconds"]),
    )
