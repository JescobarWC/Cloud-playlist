from app.core.settings import get_settings


def test_settings_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DJ_STORAGE_BACKEND", raising=False)
    monkeypatch.delenv("DJ_SQLITE_DB_PATH", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = get_settings()

    assert settings.storage_backend == "sqlite"
    assert settings.sqlite_db_path.endswith("backend/data/app.db")
    assert settings.database_url.startswith("postgresql+")


def test_settings_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("DJ_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("DJ_SQLITE_DB_PATH", "/tmp/custom.db")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@host:5432/db")

    settings = get_settings()

    assert settings.storage_backend == "postgres"
    assert settings.sqlite_db_path == "/tmp/custom.db"
    assert settings.database_url == "postgresql+psycopg://u:p@host:5432/db"
