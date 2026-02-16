from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from xml.etree import ElementTree

from app.domain.normalize import LibrarySnapshot, normalize_library_payload
from app.domain.virtualdj import parse_virtualdj_database_xml

router = APIRouter(prefix="/api/v1/connectors/virtualdj", tags=["connectors", "virtualdj"])


class VirtualDjPreviewRequest(BaseModel):
    database_xml: str = Field(..., description="Raw contents of VirtualDJ database.xml")


class VirtualDjPreviewResponse(BaseModel):
    connector: str
    track_count: int
    playlist_count: int
    library: dict[str, Any]


@router.post("/preview", response_model=VirtualDjPreviewResponse)
def preview_virtualdj_import(payload: VirtualDjPreviewRequest) -> VirtualDjPreviewResponse:
    try:
        raw_tracks, raw_playlists = parse_virtualdj_database_xml(payload.database_xml)
    except ElementTree.ParseError as exc:
        raise HTTPException(status_code=400, detail="Invalid VirtualDJ database.xml content") from exc

    snapshot: LibrarySnapshot = normalize_library_payload(raw_tracks, raw_playlists)

    return VirtualDjPreviewResponse(
        connector="virtualdj",
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
