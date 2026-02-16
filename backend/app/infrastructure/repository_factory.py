from __future__ import annotations

from app.core.settings import get_settings
from app.infrastructure.import_jobs_repository import ImportJobRepository, get_import_jobs_repository
from app.infrastructure.library_repository import LibraryRepository, get_library_repository


def get_library_repo() -> LibraryRepository:
    settings = get_settings()
    if settings.storage_backend == "sqlite":
        return get_library_repository()

    if settings.storage_backend == "postgres":
        raise NotImplementedError(
            "PostgreSQL backend is not wired yet. Next step: SQLAlchemy models + Alembic migrations + repository adapter"
        )

    raise ValueError("Unsupported DJ_STORAGE_BACKEND. Use 'sqlite' or 'postgres'")


def get_import_jobs_repo() -> ImportJobRepository:
    settings = get_settings()
    if settings.storage_backend == "sqlite":
        return get_import_jobs_repository()

    if settings.storage_backend == "postgres":
        raise NotImplementedError(
            "PostgreSQL backend is not wired yet. Next step: SQLAlchemy models + Alembic migrations + repository adapter"
        )

    raise ValueError("Unsupported DJ_STORAGE_BACKEND. Use 'sqlite' or 'postgres'")
