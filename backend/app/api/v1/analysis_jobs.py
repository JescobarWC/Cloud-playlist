from __future__ import annotations

import json
import threading
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domain.audio_analysis import analyze_audio_file
from app.infrastructure.library_repository import LibraryRepository
from app.infrastructure.repository_factory import get_library_repo

router = APIRouter(tags=["analysis-jobs"])


class AnalysisJobResponse(BaseModel):
    job_id: str
    playlist_id: int
    status: str
    total_tracks: int
    analyzed_tracks: int
    failed_tracks: int
    progress: float
    error_message: str | None = None
    created_at: str
    updated_at: str


def _run_analysis_job(db_path, job_id: str, playlist_id: int) -> None:
    repository = LibraryRepository(db_path=db_path)
    try:
        repository.start_analysis_job(job_id)
        for track in repository.get_playlist_tracks_for_analysis(playlist_id):
            track_id = int(track["track_id"])
            file_path = str(track["file_path"])
            try:
                analysis = analyze_audio_file(file_path)
                waveform = [round(float(v), 6) for v in analysis["waveform"]]
                repository.save_track_analysis(
                    track_id=track_id,
                    bpm=analysis["bpm"],
                    musical_key=analysis["key"],
                    waveform_json=json.dumps(waveform),
                )
                repository.record_analysis_job_progress(job_id, analyzed_increment=1)
            except Exception:
                repository.record_analysis_job_progress(job_id, failed_increment=1)

        repository.complete_analysis_job(job_id)
    except Exception as exc:
        repository.fail_analysis_job(job_id, str(exc))


@router.post("/api/v1/playlists/{playlist_id}/analysis-jobs", response_model=AnalysisJobResponse, status_code=202)
def create_analysis_job(playlist_id: int) -> AnalysisJobResponse:
    repository = get_library_repo()
    try:
        tracks = repository.get_playlist_tracks_for_analysis(playlist_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job_id = str(uuid4())
    repository.create_analysis_job(job_id=job_id, playlist_id=playlist_id, total_tracks=len(tracks))

    thread = threading.Thread(
        target=_run_analysis_job,
        kwargs={"db_path": repository.db_path, "job_id": job_id, "playlist_id": playlist_id},
        daemon=True,
    )
    thread.start()

    job = repository.get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create analysis job")

    return AnalysisJobResponse(**job)


@router.get("/api/v1/analysis-jobs/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(job_id: str) -> AnalysisJobResponse:
    repository = get_library_repo()
    job = repository.get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Analysis job '{job_id}' not found")
    return AnalysisJobResponse(**job)
