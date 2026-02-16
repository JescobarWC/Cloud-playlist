from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CuePoint:
    index: int
    position_seconds: float
    label: str | None = None


@dataclass(frozen=True)
class BeatgridMarker:
    index: int
    position_seconds: float
    bpm: float


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    artist: str
    bpm: float | None = None
    key: str | None = None
    cue_points: list[CuePoint] = field(default_factory=list)
    beatgrid: list[BeatgridMarker] = field(default_factory=list)


@dataclass(frozen=True)
class Playlist:
    id: str
    name: str
    track_ids: list[str]


@dataclass(frozen=True)
class LibrarySnapshot:
    tracks: list[Track]
    playlists: list[Playlist]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_cue_points(raw_track: dict[str, Any]) -> list[CuePoint]:
    raw_points = raw_track.get("cue_points", [])
    cues: list[CuePoint] = []
    for i, cue in enumerate(raw_points, start=1):
        seconds = _to_float(cue.get("position_seconds"))
        if seconds is None:
            continue
        cues.append(CuePoint(index=i, position_seconds=seconds, label=cue.get("label")))
    return cues


def _normalize_beatgrid(raw_track: dict[str, Any]) -> list[BeatgridMarker]:
    raw_markers = raw_track.get("beatgrid", [])
    markers: list[BeatgridMarker] = []
    for i, marker in enumerate(raw_markers, start=1):
        seconds = _to_float(marker.get("position_seconds"))
        bpm = _to_float(marker.get("bpm"))
        if seconds is None or bpm is None:
            continue
        markers.append(BeatgridMarker(index=i, position_seconds=seconds, bpm=bpm))
    return markers


def normalize_library_payload(raw_tracks: list[dict[str, Any]], raw_playlists: list[dict[str, Any]]) -> LibrarySnapshot:
    tracks: list[Track] = []
    for idx, raw_track in enumerate(raw_tracks, start=1):
        track_id = str(raw_track.get("id") or f"track-{idx}")
        title = str(raw_track.get("title") or "Unknown title")
        artist = str(raw_track.get("artist") or "Unknown artist")
        tracks.append(
            Track(
                id=track_id,
                title=title,
                artist=artist,
                bpm=_to_float(raw_track.get("bpm")),
                key=raw_track.get("key"),
                cue_points=_normalize_cue_points(raw_track),
                beatgrid=_normalize_beatgrid(raw_track),
            )
        )

    known_ids = {track.id for track in tracks}
    playlists: list[Playlist] = []
    for idx, raw_playlist in enumerate(raw_playlists, start=1):
        playlist_id = str(raw_playlist.get("id") or f"playlist-{idx}")
        name = str(raw_playlist.get("name") or f"Playlist {idx}")
        raw_ids = raw_playlist.get("track_ids", [])
        normalized_ids = [str(track_id) for track_id in raw_ids if str(track_id) in known_ids]
        playlists.append(Playlist(id=playlist_id, name=name, track_ids=normalized_ids))

    return LibrarySnapshot(tracks=tracks, playlists=playlists)
