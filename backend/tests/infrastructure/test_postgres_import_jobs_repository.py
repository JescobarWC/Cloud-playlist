import importlib.util

import pytest

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_import_jobs_repository_importable() -> None:
    from app.infrastructure.postgres_import_jobs_repository import PostgresImportJobsRepository

    assert PostgresImportJobsRepository is not None
