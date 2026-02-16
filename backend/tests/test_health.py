import importlib.util

import pytest

FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_healthcheck_returns_ok() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_readiness_returns_ready_for_default_backend() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["backend"] in {"sqlite", "postgres"}


@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="fastapi is not installed in this environment")
def test_readiness_returns_503_when_repository_unavailable(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    import app.main as main_module

    def _raise_repo_error():
        raise RuntimeError("repository unavailable")

    monkeypatch.setattr(main_module, "get_library_repo", _raise_repo_error)

    client = TestClient(main_module.app)
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert "repository unavailable" in response.json()["error"]
