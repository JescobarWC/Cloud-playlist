import pytest
import json
from pathlib import Path

from app.infrastructure.library_repository import LibraryRepository


def test_playlist_track_and_analysis_roundtrip(tmp_path: Path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")

    playlist_id = repository.create_playlist("Main Set")
    track_id = repository.add_track_to_playlist(
        playlist_id=playlist_id,
        title="Track A",
        artist="Artist A",
        file_path="/tmp/track-a.wav",
    )

    repository.save_track_analysis(track_id, bpm=124.0, musical_key="A4", waveform_json=json.dumps([0.1, 0.2]))

    playlist = repository.get_playlist(playlist_id)
    assert playlist is not None
    assert playlist["name"] == "Main Set"
    assert len(playlist["tracks"]) == 1
    assert playlist["tracks"][0]["id"] == track_id
    assert playlist["tracks"][0]["analysis"]["bpm"] == 124.0


def test_add_track_to_missing_playlist_raises(tmp_path: Path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")

    with pytest.raises(ValueError, match="not found"):
        repository.add_track_to_playlist(99, "Track", "Artist", "/tmp/a.wav")
