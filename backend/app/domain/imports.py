from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class ImportConnector(str, Enum):
    REKORDBOX = "rekordbox"
    SERATO = "serato"
    M3U = "m3u"
    CSV = "csv"
    VIRTUAL_DJ = "virtualdj"


@dataclass(frozen=True)
class ImportJob:
    id: str
    connector: ImportConnector
    source_uri: str
    status: str
    created_at: str


def parse_connector(raw_connector: str) -> ImportConnector:
    normalized = raw_connector.strip().lower().replace("-", "").replace(" ", "")
    aliases = {
        "virtualdj": ImportConnector.VIRTUAL_DJ,
        "virtualdj8": ImportConnector.VIRTUAL_DJ,
        "vdj": ImportConnector.VIRTUAL_DJ,
    }
    if normalized in aliases:
        return aliases[normalized]

    try:
        return ImportConnector(normalized)
    except ValueError as exc:
        supported = ", ".join(connector.value for connector in ImportConnector)
        raise ValueError(f"Unsupported connector '{raw_connector}'. Supported: {supported}") from exc


def create_import_job(raw_connector: str, source_uri: str) -> ImportJob:
    connector = parse_connector(raw_connector)
    timestamp = datetime.now(timezone.utc).isoformat()
    return ImportJob(
        id=str(uuid4()),
        connector=connector,
        source_uri=source_uri,
        status="queued",
        created_at=timestamp,
    )
