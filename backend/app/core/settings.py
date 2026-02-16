from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    storage_backend: str
    sqlite_db_path: str
    database_url: str


_DEFAULT_SQLITE_PATH = "backend/data/app.db"
_DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/dj_bridge"


def get_settings() -> Settings:
    return Settings(
        storage_backend=os.getenv("DJ_STORAGE_BACKEND", "sqlite").strip().lower(),
        sqlite_db_path=os.getenv("DJ_SQLITE_DB_PATH", _DEFAULT_SQLITE_PATH),
        database_url=os.getenv("DATABASE_URL", _DEFAULT_DATABASE_URL),
    )
