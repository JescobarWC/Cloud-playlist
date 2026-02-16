import os

import pytest

RUN_POSTGRES_TESTS = os.getenv("RUN_POSTGRES_TESTS") == "1"
DATABASE_URL = os.getenv("DATABASE_URL", "")


@pytest.mark.skipif(not RUN_POSTGRES_TESTS, reason="RUN_POSTGRES_TESTS is not enabled")
def test_postgres_live_library_and_import_jobs_roundtrip() -> None:
    from app.domain.imports import create_import_job
    from app.infrastructure.postgres_import_jobs_repository import PostgresImportJobsRepository
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository
    from app.infrastructure.postgres_models import metadata

    if not DATABASE_URL.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not configured for a PostgreSQL backend")

    metadata.drop_all(bind=PostgresLibraryRepository(DATABASE_URL).engine)

    library_repo = PostgresLibraryRepository(DATABASE_URL)
    import_repo = PostgresImportJobsRepository(DATABASE_URL)

    playlist_id = library_repo.create_playlist("Postgres Set")
    track_id = library_repo.add_track_to_playlist(playlist_id, "A", "Artist", "/a.wav")
    playlist = library_repo.get_playlist(playlist_id)

    assert playlist is not None
    assert playlist["id"] == playlist_id
    assert playlist["tracks"][0]["id"] == track_id

    job = create_import_job("virtualdj", "/tmp/database.xml")
    saved = import_repo.save(job)
    fetched = import_repo.get(saved.id)

    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.source_uri == "/tmp/database.xml"
