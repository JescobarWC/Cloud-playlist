from __future__ import annotations

from app.core.settings import get_settings
from app.infrastructure.import_jobs_repository import ImportJobRepository, get_import_jobs_repository
from app.infrastructure.library_repository import LibraryRepository, get_library_repository


def get_library_repo() -> LibraryRepository:
    settings = get_settings()
    if settings.storage_backend == "sqlite":
        return get_library_repository()

    if settings.storage_backend == "postgres":
        try:
            from app.infrastructure.postgres_library_repository import PostgresLibraryRepository
        except ImportError as exc:  # pragma: no cover - env dependent import path
            raise NotImplementedError(
                "PostgreSQL library adapter requires SQLAlchemy support in the runtime"
            ) from exc

        return PostgresLibraryRepository(settings.database_url)

    raise ValueError("Unsupported DJ_STORAGE_BACKEND. Use 'sqlite' or 'postgres'")


def get_import_jobs_repo() -> ImportJobRepository:
    settings = get_settings()
    if settings.storage_backend == "sqlite":
        return get_import_jobs_repository()

    if settings.storage_backend == "postgres":
        try:
            from app.infrastructure.postgres_import_jobs_repository import PostgresImportJobsRepository
        except ImportError as exc:  # pragma: no cover - env dependent import path
            raise NotImplementedError(
                "PostgreSQL import-jobs adapter requires SQLAlchemy support in the runtime"
            ) from exc

        return PostgresImportJobsRepository(settings.database_url)

    raise ValueError("Unsupported DJ_STORAGE_BACKEND. Use 'sqlite' or 'postgres'")
