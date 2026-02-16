import pytest

from app.domain.imports import ImportConnector, create_import_job, parse_connector


@pytest.mark.parametrize(
    ("raw_connector", "expected"),
    [
        ("rekordbox", ImportConnector.REKORDBOX),
        ("serato", ImportConnector.SERATO),
        ("m3u", ImportConnector.M3U),
        ("csv", ImportConnector.CSV),
        ("virtualdj", ImportConnector.VIRTUAL_DJ),
        ("Virtual DJ", ImportConnector.VIRTUAL_DJ),
        ("vdj", ImportConnector.VIRTUAL_DJ),
    ],
)
def test_parse_connector_accepts_supported_and_aliases(raw_connector: str, expected: ImportConnector) -> None:
    assert parse_connector(raw_connector) == expected


def test_parse_connector_rejects_unknown_connector() -> None:
    with pytest.raises(ValueError, match="Unsupported connector"):
        parse_connector("traktor")


def test_create_import_job_defaults_to_queued() -> None:
    job = create_import_job("virtualdj", "/music/VirtualDJ/database.xml")

    assert job.status == "queued"
    assert job.connector == ImportConnector.VIRTUAL_DJ
    assert job.source_uri == "/music/VirtualDJ/database.xml"
    assert job.id
    assert job.created_at
