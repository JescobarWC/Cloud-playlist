import importlib.util
from pathlib import Path

import pytest

from app.infrastructure import library_repository
from app.infrastructure.library_repository import LibraryRepository

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_tools_duplicate_and_replace_flow(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    library_repository._library_repository = LibraryRepository(db_path=tmp_path / "app.db")
    client = TestClient(app)

    playlist_id = client.post("/api/v1/playlists", json={"name": "Set"}).json()["playlist_id"]
    client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "Hello Song", "artist": "Artist", "file_path": "/a.wav"},
    )
    client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "hello song", "artist": "artist", "file_path": "/b.wav"},
    )

    duplicates = client.get("/api/v1/tools/duplicates")
    assert duplicates.status_code == 200
    assert len(duplicates.json()) == 1

    preview = client.post(
        "/api/v1/tools/find-replace",
        json={"field_name": "title", "search_text": "Song", "replace_text": "Track", "apply": False},
    )
    assert preview.status_code == 200
    assert preview.json()["changed_tracks"] >= 1

    applied = client.post(
        "/api/v1/tools/find-replace",
        json={"field_name": "title", "search_text": "Song", "replace_text": "Track", "apply": True},
    )
    assert applied.status_code == 200
    op_id = applied.json()["operation_id"]
    assert op_id

    undo = client.post(f"/api/v1/tools/find-replace/{op_id}/undo")
    assert undo.status_code == 200
    assert undo.json()["restored_tracks"] >= 1
