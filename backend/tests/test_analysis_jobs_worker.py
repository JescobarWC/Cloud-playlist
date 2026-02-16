from __future__ import annotations

import importlib.util

import pytest

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None

if FASTAPI_AVAILABLE:
    from app.api.v1 import analysis_jobs


class _FakeRepo:
    def __init__(self) -> None:
        self.started = False
        self.completed = False
        self.failed_message: str | None = None
        self.progress: list[tuple[int, int]] = []
        self.saved: list[int] = []

    def start_analysis_job(self, job_id: str) -> None:
        self.started = True

    def get_playlist_tracks_for_analysis(self, playlist_id: int):
        return [{"track_id": 1, "file_path": "/a.wav"}, {"track_id": 2, "file_path": "/b.wav"}]

    def is_analysis_job_cancelled(self, job_id: str) -> bool:
        return False

    def save_track_analysis(self, track_id: int, bpm, musical_key, waveform_json: str) -> None:
        self.saved.append(track_id)

    def record_analysis_job_progress(self, job_id: str, analyzed_increment: int = 0, failed_increment: int = 0) -> None:
        self.progress.append((analyzed_increment, failed_increment))

    def complete_analysis_job(self, job_id: str) -> None:
        self.completed = True

    def fail_analysis_job(self, job_id: str, error_message: str) -> None:
        self.failed_message = error_message


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_process_analysis_job_uses_backend_agnostic_repository(monkeypatch) -> None:
    repo = _FakeRepo()

    def _fake_analyze(_path: str):
        return {"waveform": [0.1, 0.2], "bpm": 120.0, "key": "Am"}

    monkeypatch.setattr(analysis_jobs, "analyze_audio_file", _fake_analyze)

    analysis_jobs._process_analysis_job(repo, job_id="job-1", playlist_id=42)

    assert repo.started is True
    assert repo.completed is True
    assert repo.failed_message is None
    assert repo.saved == [1, 2]
    assert repo.progress == [(1, 0), (1, 0)]


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_process_analysis_job_marks_failures_per_track(monkeypatch) -> None:
    repo = _FakeRepo()

    def _fake_analyze(path: str):
        if path.endswith("b.wav"):
            raise ValueError("broken")
        return {"waveform": [0.1], "bpm": 120.0, "key": "Am"}

    monkeypatch.setattr(analysis_jobs, "analyze_audio_file", _fake_analyze)

    analysis_jobs._process_analysis_job(repo, job_id="job-1", playlist_id=42)

    assert repo.completed is True
    assert repo.failed_message is None
    assert repo.saved == [1]
    assert repo.progress == [(1, 0), (0, 1)]
