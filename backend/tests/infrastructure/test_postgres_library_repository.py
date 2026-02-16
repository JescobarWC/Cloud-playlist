import importlib.util
import json
import time

import pytest

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_importable() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    assert PostgresLibraryRepository is not None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_playlist_roundtrip() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    repository = PostgresLibraryRepository("sqlite+pysqlite:///:memory:")

    playlist_id = repository.create_playlist("Set")
    track_id = repository.add_track_to_playlist(playlist_id, "Track A", "Artist", "/a.wav")
    repository.save_track_analysis(track_id, 128.0, "Am", json.dumps([0.1, 0.2]))

    playlist = repository.get_playlist(playlist_id)

    assert playlist is not None
    assert playlist["id"] == playlist_id
    assert playlist["name"] == "Set"
    assert len(playlist["tracks"]) == 1
    assert playlist["tracks"][0]["analysis"] == {"bpm": 128.0, "key": "Am", "waveform": [0.1, 0.2]}


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_playback_controls() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    repository = PostgresLibraryRepository("sqlite+pysqlite:///:memory:")

    playlist_id = repository.create_playlist("Set")
    first_track = repository.add_track_to_playlist(playlist_id, "A", "Artist", "/a.wav")
    second_track = repository.add_track_to_playlist(playlist_id, "B", "Artist", "/b.wav")

    state = repository.set_playing(playlist_id, True)
    assert state["is_playing"] is True

    time.sleep(0.02)
    progressed = repository.get_playback_state(playlist_id)
    assert progressed["current_position_seconds"] > state["current_position_seconds"]

    moved = repository.move_track(playlist_id, "next")
    assert moved["current_track_id"] == second_track
    assert moved["current_position_seconds"] == 0.0

    selected = repository.set_current_track(playlist_id, first_track)
    assert selected["current_track_id"] == first_track
    assert selected["current_position_seconds"] == 0.0
