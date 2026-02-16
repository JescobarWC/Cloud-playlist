from pathlib import Path

from app.domain.imports import create_import_job
from app.infrastructure.import_jobs_repository import ImportJobRepository


def test_save_and_get_import_job(tmp_path: Path) -> None:
    repository = ImportJobRepository(db_path=tmp_path / "app.db")
    job = create_import_job("virtualdj", "/music/VirtualDJ/database.xml")

    repository.save(job)
    stored = repository.get(job.id)

    assert stored is not None
    assert stored.id == job.id
    assert stored.connector.value == "virtualdj"
    assert stored.source_uri == "/music/VirtualDJ/database.xml"


def test_get_returns_none_for_missing_job(tmp_path: Path) -> None:
    repository = ImportJobRepository(db_path=tmp_path / "app.db")

    assert repository.get("missing") is None
