import importlib.util

import pytest

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_virtualdj_preview_endpoint_returns_normalized_payload() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    xml = """
    <VirtualDJ_Database>
      <Song FilePath="/music/a.mp3">
        <Tags Author="Artist A" Title="Track A" Bpm="124" />
      </Song>
      <Playlists>
        <Playlist Name="Main Set">
          <Song FilePath="/music/a.mp3" />
        </Playlist>
      </Playlists>
    </VirtualDJ_Database>
    """

    client = TestClient(app)
    response = client.post("/api/v1/connectors/virtualdj/preview", json={"database_xml": xml})

    assert response.status_code == 200
    payload = response.json()
    assert payload["connector"] == "virtualdj"
    assert payload["track_count"] == 1
    assert payload["playlist_count"] == 1
    assert payload["library"]["tracks"][0]["title"] == "Track A"


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_virtualdj_preview_endpoint_rejects_invalid_xml() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/connectors/virtualdj/preview", json={"database_xml": "<broken>"})

    assert response.status_code == 400
