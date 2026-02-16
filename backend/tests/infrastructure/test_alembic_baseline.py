from pathlib import Path


def test_alembic_baseline_files_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "alembic.ini").exists()
    assert (root / "alembic" / "env.py").exists()
    assert (root / "alembic" / "versions" / "0001_initial_schema.py").exists()
