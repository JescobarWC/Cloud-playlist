from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.imports import ImportJob, parse_connector

metadata = MetaData()

import_jobs_table = Table(
    "import_jobs",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("connector", String(32), nullable=False),
    Column("source_uri", String(2048), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class PostgresImportJobsRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: Engine = create_engine(database_url)
        metadata.create_all(self.engine)

    def save(self, job: ImportJob) -> ImportJob:
        created_at = datetime.fromisoformat(job.created_at)
        with Session(self.engine) as session:
            session.execute(
                import_jobs_table.insert().values(
                    id=job.id,
                    connector=job.connector.value,
                    source_uri=job.source_uri,
                    status=job.status,
                    created_at=created_at,
                )
            )
            session.commit()
        return job

    def get(self, job_id: str) -> ImportJob | None:
        with Session(self.engine) as session:
            row = session.execute(select(import_jobs_table).where(import_jobs_table.c.id == job_id)).mappings().first()

        if row is None:
            return None

        created_at = row["created_at"].isoformat()
        return ImportJob(
            id=row["id"],
            connector=parse_connector(row["connector"]),
            source_uri=row["source_uri"],
            status=row["status"],
            created_at=created_at,
        )
