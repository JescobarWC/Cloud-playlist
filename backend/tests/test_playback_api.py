import importlib.util
from pathlib import Path

import pytest

from app.infrastructure import library_repository
from app.infrastructure.library_repository import LibraryRepository

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_playback_transport_flow(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    library_repository._library_repository = LibraryRepository(db_path=tmp_path / "app.db")

    client = TestClient(app)

    playlist = client.post("/api/v1/playlists", json={"name": "Main"}).json()
    playlist_id = playlist["playlist_id"]

    first_track = client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "Track 1", "artist": "Artist", "file_path": "/tmp/1.wav"},
    ).json()["track_id"]
    second_track = client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "Track 2", "artist": "Artist", "file_path": "/tmp/2.wav"},
    ).json()["track_id"]

    state = client.get(f"/api/v1/playlists/{playlist_id}/playback")
    assert state.status_code == 200
    assert state.json()["current_track_id"] == first_track

    assert client.post(f"/api/v1/playlists/{playlist_id}/playback/play").json()["is_playing"] is True
    seek_position = client.post(f"/api/v1/playlists/{playlist_id}/playback/seek", json={"position_seconds": 15}).json()[
        "current_position_seconds"
    ]
    assert 15.0 <= seek_position <= 15.1
    assert client.post(f"/api/v1/playlists/{playlist_id}/playback/next").json()["current_track_id"] == second_track
    assert (
        client.post(f"/api/v1/playlists/{playlist_id}/playback/load", json={"track_id": first_track}).json()[
            "current_track_id"
        ]
        == first_track
    )
    assert client.post(f"/api/v1/playlists/{playlist_id}/playback/pause").json()["is_playing"] is False


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_playback_next_on_empty_playlist_returns_400(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    library_repository._library_repository = LibraryRepository(db_path=tmp_path / "app.db")

    client = TestClient(app)
    playlist_id = client.post("/api/v1/playlists", json={"name": "Empty"}).json()["playlist_id"]

    response = client.post(f"/api/v1/playlists/{playlist_id}/playback/next")
    assert response.status_code == 400
