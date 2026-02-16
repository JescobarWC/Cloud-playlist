import importlib.util
import math
import wave
from array import array
from pathlib import Path

import pytest

from app.infrastructure import library_repository
from app.infrastructure.library_repository import LibraryRepository

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


def _write_sine_wav(path: Path, seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 44100) -> None:
    total_samples = int(seconds * sample_rate)
    data = array("h")
    for i in range(total_samples):
        data.append(int(18000 * math.sin(2 * math.pi * freq * (i / sample_rate))))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(data.tobytes())


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_playlist_management_and_track_analysis_flow(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    db_path = tmp_path / "app.db"
    audio_path = tmp_path / "tone.wav"
    _write_sine_wav(audio_path, seconds=1.0, freq=440.0)

    library_repository._library_repository = LibraryRepository(db_path=db_path)

    client = TestClient(app)

    create_playlist = client.post("/api/v1/playlists", json={"name": "Warmup"})
    assert create_playlist.status_code == 201
    playlist_id = create_playlist.json()["playlist_id"]

    add_track = client.post(
        f"/api/v1/playlists/{playlist_id}/tracks",
        json={"title": "Tone", "artist": "Generator", "file_path": str(audio_path)},
    )
    assert add_track.status_code == 201
    track_id = add_track.json()["track_id"]

    analyze = client.post(f"/api/v1/tracks/{track_id}/analyze")
    assert analyze.status_code == 200
    analysis = analyze.json()
    assert analysis["waveform"]

    playlist_response = client.get(f"/api/v1/playlists/{playlist_id}")
    assert playlist_response.status_code == 200
    playlist_payload = playlist_response.json()
    assert playlist_payload["name"] == "Warmup"
    assert playlist_payload["tracks"][0]["analysis"] is not None
