from app.infrastructure.library_repository import LibraryRepository


def test_analysis_job_lifecycle(tmp_path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")
    playlist_id = repository.create_playlist("A")
    repository.add_track_to_playlist(playlist_id, "Track", "Artist", "/tmp/track.wav")

    repository.create_analysis_job("job-1", playlist_id, total_tracks=1)
    repository.start_analysis_job("job-1")
    repository.record_analysis_job_progress("job-1", analyzed_increment=1)
    repository.complete_analysis_job("job-1")

    job = repository.get_analysis_job("job-1")
    assert job is not None
    assert job["status"] == "completed"
    assert job["progress"] == 100.0


def test_analysis_job_completed_with_errors(tmp_path) -> None:
    repository = LibraryRepository(db_path=tmp_path / "app.db")
    playlist_id = repository.create_playlist("A")

    repository.create_analysis_job("job-2", playlist_id, total_tracks=1)
    repository.start_analysis_job("job-2")
    repository.record_analysis_job_progress("job-2", failed_increment=1)
    repository.complete_analysis_job("job-2")

    job = repository.get_analysis_job("job-2")
    assert job is not None
    assert job["status"] == "completed_with_errors"
