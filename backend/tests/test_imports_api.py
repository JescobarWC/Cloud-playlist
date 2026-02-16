import importlib.util
from pathlib import Path

import pytest

from app.infrastructure import import_jobs_repository
from app.infrastructure.import_jobs_repository import ImportJobRepository

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_create_and_get_import_job_roundtrip(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    import_jobs_repository._repository = ImportJobRepository(db_path=tmp_path / "app.db")

    client = TestClient(app)
    create_response = client.post(
        "/api/v1/imports",
        json={"connector": "Virtual DJ", "source_uri": "/music/VirtualDJ/database.xml"},
    )

    assert create_response.status_code == 202
    create_payload = create_response.json()
    job_id = create_payload["job_id"]

    get_response = client.get(f"/api/v1/imports/{job_id}")

    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["job_id"] == job_id
    assert get_payload["connector"] == "virtualdj"


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_get_import_job_returns_404_when_missing(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    import_jobs_repository._repository = ImportJobRepository(db_path=tmp_path / "app.db")

    client = TestClient(app)
    response = client.get("/api/v1/imports/missing")

    assert response.status_code == 404
