from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.domain.imports import ImportJob, parse_connector

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "app.db"


class ImportJobRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS import_jobs (
                    id TEXT PRIMARY KEY,
                    connector TEXT NOT NULL,
                    source_uri TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save(self, job: ImportJob) -> ImportJob:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO import_jobs (id, connector, source_uri, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job.id, job.connector.value, job.source_uri, job.status, job.created_at),
            )
            connection.commit()
        return job

    def get(self, job_id: str) -> ImportJob | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, connector, source_uri, status, created_at FROM import_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        return ImportJob(
            id=row["id"],
            connector=parse_connector(row["connector"]),
            source_uri=row["source_uri"],
            status=row["status"],
            created_at=row["created_at"],
        )


_repository: ImportJobRepository | None = None


def get_import_jobs_repository() -> ImportJobRepository:
    global _repository
    if _repository is None:
        _repository = ImportJobRepository()
    return _repository
