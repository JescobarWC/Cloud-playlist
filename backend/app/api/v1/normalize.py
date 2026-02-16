from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.imports import parse_connector
from app.domain.normalize import LibrarySnapshot, normalize_library_payload

router = APIRouter(prefix="/api/v1/normalize", tags=["normalization"])


class NormalizeLibraryRequest(BaseModel):
    connector: str = Field(..., description="Source connector (rekordbox, serato, virtualdj, m3u, csv)")
    tracks: list[dict[str, Any]] = Field(default_factory=list)
    playlists: list[dict[str, Any]] = Field(default_factory=list)


class NormalizeLibraryResponse(BaseModel):
    connector: str
    track_count: int
    playlist_count: int
    library: dict[str, Any]


@router.post("", response_model=NormalizeLibraryResponse)
def normalize_library(payload: NormalizeLibraryRequest) -> NormalizeLibraryResponse:
    connector = parse_connector(payload.connector)
    snapshot: LibrarySnapshot = normalize_library_payload(payload.tracks, payload.playlists)
    return NormalizeLibraryResponse(
        connector=connector.value,
        track_count=len(snapshot.tracks),
        playlist_count=len(snapshot.playlists),
        library={
            "tracks": [
                {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "bpm": track.bpm,
                    "key": track.key,
                    "cue_points": [
                        {
                            "index": cue.index,
                            "position_seconds": cue.position_seconds,
                            "label": cue.label,
                        }
                        for cue in track.cue_points
                    ],
                    "beatgrid": [
                        {
                            "index": marker.index,
                            "position_seconds": marker.position_seconds,
                            "bpm": marker.bpm,
                        }
                        for marker in track.beatgrid
                    ],
                }
                for track in snapshot.tracks
            ],
            "playlists": [
                {
                    "id": playlist.id,
                    "name": playlist.name,
                    "track_ids": playlist.track_ids,
                }
                for playlist in snapshot.playlists
            ],
        },
    )
