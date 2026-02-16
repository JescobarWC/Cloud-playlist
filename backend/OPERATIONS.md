# Backend Operations Runbook (Beta)

This document defines the minimum operational baseline for the backend beta.

## Environments

- **Local dev**: `DJ_STORAGE_BACKEND=sqlite`
- **CI Postgres**: `DJ_STORAGE_BACKEND=postgres`, `RUN_POSTGRES_TESTS=1`
- **Beta env**: `DJ_STORAGE_BACKEND=postgres`, Alembic migrations applied before app startup

## Required environment variables

- `DJ_STORAGE_BACKEND`: `sqlite` or `postgres`
- `DATABASE_URL`: required for postgres mode
- `DJ_SQLITE_DB_PATH`: optional for sqlite mode

## Startup checklist (beta)

1. Install dependencies: `python -m pip install -e .[dev]`
2. Run migrations (postgres): `alembic upgrade head`
3. Start API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
4. Validate probes:
   - `GET /health` -> `200 {"status":"ok"}`
   - `GET /ready` -> `200` and `checks.storage == "ok"`

## CI checks

- Workflow: `.github/workflows/backend-postgres-ci.yml`
- Runs:
  - `pytest -q -m postgres_live`
  - `pytest -q -m "not postgres_live"`

## Incident quick checks

1. `GET /ready` and inspect `error` field if status is `not_ready`
2. Validate `DATABASE_URL` and backend mode
3. Re-run migrations: `alembic upgrade head`
4. Re-run smoke tests:
   - `pytest -q tests/test_postgres_api_smoke.py`
   - `pytest -q tests/infrastructure/test_postgres_live_repositories.py`
