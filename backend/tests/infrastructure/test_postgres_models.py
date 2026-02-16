import importlib.util

import pytest

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy is not installed in this environment")
def test_postgres_models_expose_expected_tables() -> None:
    from app.infrastructure.postgres_models import metadata

    expected = {
        "playlists",
        "tracks",
        "playlist_tracks",
        "track_analysis",
        "playback_sessions",
        "analysis_jobs",
        "replace_operations",
        "replace_changes",
        "import_jobs",
    }

    assert expected.issubset(set(metadata.tables.keys()))
