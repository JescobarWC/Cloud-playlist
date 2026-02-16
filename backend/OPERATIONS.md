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

## One-command beta gate (recommended)

From repository root:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dj_bridge \
  ./backend/scripts/beta_go_no_go.sh
```

Optional probe validation against a running API:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dj_bridge \
BASE_URL=http://localhost:8000 \
  ./backend/scripts/beta_go_no_go.sh
```

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

## Beta exit checklist (Go/No-Go)

Mark all items before promoting backend as beta-operational:

- [ ] `backend-postgres-ci` green on **3 consecutive runs** for target branch
- [ ] `pytest -q -m postgres_live` green in CI with `RUN_POSTGRES_TESTS=1`
- [ ] `pytest -q -m "not postgres_live"` green in CI
- [ ] `/ready` returns `200` and `checks.storage == "ok"` in beta environment
- [ ] Alembic migration runbook (`alembic upgrade head`) verified by a second team member
- [ ] Smoke API flow validated in beta env:
  - create playlist
  - add track
  - read playlist
  - playback state endpoint
  - analysis-job create/poll/cancel
- [ ] Incident rollback step documented with previous image/version tag

Go decision:

- **GO**: all checks completed and signed off
- **NO-GO**: any critical check missing or flaky

Use `backend/BETA_SIGNOFF.md` to capture evidence and final sign-off.

