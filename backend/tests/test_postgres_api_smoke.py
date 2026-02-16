import importlib.util
import os

import pytest

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None
RUN_POSTGRES_TESTS = os.getenv("RUN_POSTGRES_TESTS") == "1"
DATABASE_URL = os.getenv("DATABASE_URL", "")


@pytest.mark.postgres_live
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
@pytest.mark.skipif(not RUN_POSTGRES_TESTS, reason="RUN_POSTGRES_TESTS is not enabled")
def test_postgres_backend_api_smoke(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.infrastructure.postgres_models import metadata
    from app.infrastructure.repository_factory import get_library_repo
    from app.main import app

    if not DATABASE_URL.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not configured for a PostgreSQL backend")

    monkeypatch.setenv("DJ_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)

    repo = get_library_repo()
    metadata.drop_all(bind=repo.engine)
    metadata.create_all(bind=repo.engine)

    client = TestClient(app)

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["backend"] == "postgres"
    assert ready.json()["checks"]["storage"] == "ok"

    create_playlist = client.post("/api/v1/playlists", json={"name": "Smoke"})
    assert create_playlist.status_code == 201
    playlist_id = create_playlist.json()["id"]

    add_track = client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "A", "artist": "Artist", "file_path": "/a.wav"},
    )
    assert add_track.status_code == 201

    playlist = client.get(f"/api/v1/playlists/{playlist_id}")
    assert playlist.status_code == 200
    assert playlist.json()["name"] == "Smoke"
    assert len(playlist.json()["tracks"]) == 1

    playback = client.get(f"/api/v1/playlists/{playlist_id}/playback")
    assert playback.status_code == 200
    assert playback.json()["playlist_id"] == playlist_id
