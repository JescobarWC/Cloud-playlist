import pytest

from app.infrastructure.repository_factory import get_import_jobs_repo, get_library_repo


def test_repository_factory_returns_sqlite_repositories(monkeypatch) -> None:
    monkeypatch.setenv("DJ_STORAGE_BACKEND", "sqlite")

    assert get_library_repo() is not None
    assert get_import_jobs_repo() is not None


def test_repository_factory_postgres_not_implemented(monkeypatch) -> None:
    monkeypatch.setenv("DJ_STORAGE_BACKEND", "postgres")

    with pytest.raises(NotImplementedError):
        get_library_repo()
    with pytest.raises(NotImplementedError):
        get_import_jobs_repo()


def test_repository_factory_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("DJ_STORAGE_BACKEND", "mongo")

    with pytest.raises(ValueError, match="Unsupported DJ_STORAGE_BACKEND"):
        get_library_repo()
