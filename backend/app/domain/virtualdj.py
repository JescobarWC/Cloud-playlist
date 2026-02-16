from __future__ import annotations

from typing import Any
from xml.etree import ElementTree


def _safe_text(value: str | None, default: str = "") -> str:
    if value is None:
        return default
    cleaned = value.strip()
    return cleaned or default


def parse_virtualdj_database_xml(xml_content: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse a minimal subset of VirtualDJ `database.xml` into raw track/playlist payloads.

    Notes:
    - This MVP parser focuses on Track tags and an optional <Playlists><Playlist><Song FilePath=.../></Playlist></Playlists>
      section when present.
    - It returns connector-agnostic raw dictionaries consumed by normalization.
    """

    root = ElementTree.fromstring(xml_content)

    tracks: list[dict[str, Any]] = []
    path_to_track_id: dict[str, str] = {}

    for idx, track in enumerate(root.findall("./Song"), start=1):
        file_path = track.attrib.get("FilePath") or track.attrib.get("Filepath")
        tags = track.find("Tags")

        title = "Unknown title"
        artist = "Unknown artist"
        bpm: float | None = None

        if tags is not None:
            title = _safe_text(tags.attrib.get("Title"), default=title)
            artist = _safe_text(tags.attrib.get("Author"), default=artist)
            raw_bpm = tags.attrib.get("Bpm")
            if raw_bpm is not None:
                try:
                    bpm = float(raw_bpm)
                except ValueError:
                    bpm = None

        track_id = f"vdj-{idx}"
        tracks.append(
            {
                "id": track_id,
                "title": title,
                "artist": artist,
                "bpm": bpm,
                "source_path": file_path,
            }
        )

        if file_path:
            path_to_track_id[file_path] = track_id

    playlists: list[dict[str, Any]] = []
    for pidx, playlist in enumerate(root.findall(".//Playlists/Playlist"), start=1):
        name = _safe_text(playlist.attrib.get("Name"), default=f"Playlist {pidx}")
        track_ids: list[str] = []

        for song in playlist.findall("Song"):
            file_path = song.attrib.get("FilePath") or song.attrib.get("Filepath")
            if file_path and file_path in path_to_track_id:
                track_ids.append(path_to_track_id[file_path])

        playlists.append(
            {
                "id": f"vdj-playlist-{pidx}",
                "name": name,
                "track_ids": track_ids,
            }
        )

    return tracks, playlists
