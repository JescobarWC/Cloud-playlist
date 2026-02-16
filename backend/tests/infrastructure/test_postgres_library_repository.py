import importlib.util

import pytest

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_importable() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    assert PostgresLibraryRepository is not None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_library_repository_can_initialize_engine() -> None:
    from app.infrastructure.postgres_library_repository import PostgresLibraryRepository

    repository = PostgresLibraryRepository("sqlite+pysqlite:///:memory:")

    assert repository is not None
    assert repository.engine is not None
