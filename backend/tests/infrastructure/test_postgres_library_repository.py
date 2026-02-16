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


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_analysis_job_lifecycle() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    repository = PostgresLibraryRepository("sqlite+pysqlite:///:memory:")

    playlist_id = repository.create_playlist("Set")
    repository.add_track_to_playlist(playlist_id, "A", "Artist", "/a.wav")
    repository.add_track_to_playlist(playlist_id, "B", "Artist", "/b.wav")

    repository.create_analysis_job("job-1", playlist_id, total_tracks=2)
    repository.start_analysis_job("job-1")
    repository.record_analysis_job_progress("job-1", analyzed_increment=1)
    repository.record_analysis_job_progress("job-1", failed_increment=1)
    repository.complete_analysis_job("job-1")

    job = repository.get_analysis_job("job-1")

    assert job is not None
    assert job["status"] == "completed_with_errors"
    assert job["total_tracks"] == 2
    assert job["analyzed_tracks"] == 1
    assert job["failed_tracks"] == 1
    assert job["progress"] == 100.0


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_find_replace_and_duplicates() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    repository = PostgresLibraryRepository("sqlite+pysqlite:///:memory:")

    playlist_id = repository.create_playlist("Set")
    first_id = repository.add_track_to_playlist(playlist_id, "My Song", "Artist", "/a.wav")
    second_id = repository.add_track_to_playlist(playlist_id, "my song", "artist", "/b.wav")

    duplicates = repository.find_duplicate_tracks()
    assert len(duplicates) == 1
    assert duplicates[0]["title"] == "my song"
    assert duplicates[0]["artist"] == "artist"
    assert sorted(duplicates[0]["track_ids"]) == sorted([first_id, second_id])

    preview = repository.preview_find_replace("title", "Song", "Track")
    assert len(preview) == 1
    assert preview[0]["new_value"] == "My Track"

    apply_result = repository.apply_find_replace("op-1", "title", "Song", "Track")
    assert apply_result == {"operation_id": "op-1", "changed_tracks": 1}

    changed = repository.get_track(first_id)
    assert changed is not None
    assert changed["title"] == "My Track"

    undo_result = repository.undo_find_replace("op-1")
    assert undo_result == {"operation_id": "op-1", "restored_tracks": 1}

    restored = repository.get_track(first_id)
    assert restored is not None
    assert restored["title"] == "My Song"
