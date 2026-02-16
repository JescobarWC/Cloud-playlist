import importlib.util
import math
import time
import wave
from array import array
from pathlib import Path

import pytest

from app.infrastructure import library_repository
from app.infrastructure.library_repository import LibraryRepository

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


def _write_sine_wav(path: Path, seconds: float = 0.2, freq: float = 440.0, sample_rate: int = 44100) -> None:
    total_samples = int(seconds * sample_rate)
    data = array("h")
    for i in range(total_samples):
        data.append(int(12000 * math.sin(2 * math.pi * freq * (i / sample_rate))))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(data.tobytes())


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_analysis_job_endpoint_processes_playlist_tracks(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    db_path = tmp_path / "app.db"
    good_file = tmp_path / "ok.wav"
    bad_file = tmp_path / "bad.mp3"
    _write_sine_wav(good_file)
    bad_file.write_text("not-a-real-audio")

    library_repository._library_repository = LibraryRepository(db_path=db_path)
    client = TestClient(app)

    playlist_id = client.post("/api/v1/playlists", json={"name": "Analyze"}).json()["playlist_id"]
    client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "Good", "artist": "Artist", "file_path": str(good_file)},
    )
    client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "Bad", "artist": "Artist", "file_path": str(bad_file)},
    )

    create = client.post(f"/api/v1/playlists/{playlist_id}/analysis-jobs")
    assert create.status_code == 202
    job_id = create.json()["job_id"]

    final_payload = None
    for _ in range(100):
        resp = client.get(f"/api/v1/analysis-jobs/{job_id}")
        assert resp.status_code == 200
        payload = resp.json()
        if payload["status"] in {"completed", "completed_with_errors", "failed"}:
            final_payload = payload
            break
        time.sleep(0.02)

    assert final_payload is not None
    assert final_payload["total_tracks"] == 2
    assert final_payload["analyzed_tracks"] + final_payload["failed_tracks"] == 2
    assert final_payload["status"] in {"completed", "completed_with_errors"}


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_get_analysis_job_404_when_missing(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    library_repository._library_repository = LibraryRepository(db_path=tmp_path / "app.db")
    client = TestClient(app)

    response = client.get("/api/v1/analysis-jobs/missing")
    assert response.status_code == 404


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_cancel_analysis_job_endpoint(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    db_path = tmp_path / "app.db"
    audio_path = tmp_path / "ok.wav"
    _write_sine_wav(audio_path, seconds=2.0)

    library_repository._library_repository = LibraryRepository(db_path=db_path)
    client = TestClient(app)

    playlist_id = client.post("/api/v1/playlists", json={"name": "Cancelable"}).json()["playlist_id"]
    for _ in range(3):
        client.post(
            f"/api/v1/playlists/{playlist_id}/tracks",
            json={"title": "T", "artist": "A", "file_path": str(audio_path)},
        )

    created = client.post(f"/api/v1/playlists/{playlist_id}/analysis-jobs")
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    cancelled = client.post(f"/api/v1/analysis-jobs/{job_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] in {"cancelled", "completed", "completed_with_errors"}
