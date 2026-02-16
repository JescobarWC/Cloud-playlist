import importlib.util

import pytest

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_normalize_endpoint_returns_normalized_library() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/normalize",
        json={
            "connector": "Virtual DJ",
            "tracks": [{"id": "t1", "title": "Titanium", "artist": "Guetta", "bpm": "126"}],
            "playlists": [{"id": "p1", "name": "Main", "track_ids": ["t1"]}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["connector"] == "virtualdj"
    assert payload["track_count"] == 1
    assert payload["playlist_count"] == 1
    assert payload["library"]["tracks"][0]["bpm"] == 126.0
