# DJ Library & Bridge Platform

Initial monorepo scaffold for a desktop + backend system that manages DJ libraries across ecosystems.

## Scope (Phase 1)

- Desktop app: Electron + React + TypeScript
- Backend API: FastAPI + PostgreSQL + Redis/Celery
- Initial connectors planned: Rekordbox, Serato, VirtualDJ, M3U, CSV
- Internal normalization model: tracks, playlists, cue points, beatgrids
- First export target: Rekordbox

## Current bootstrap

This PR introduces a minimal backend service bootstrap:

- FastAPI app entrypoint at `backend/app/main.py`
- Health endpoint `GET /health`
- Import job intake endpoint `POST /api/v1/imports`
- Connector normalization support for `rekordbox`, `serato`, `virtualdj`, `m3u`, and `csv`
- Basic pytest coverage for domain import connector normalization and health API behavior
- Backend dependency and test config in `backend/pyproject.toml`

## Run locally

Prerequisite: Python 3.10+

```bash
cd backend
python -m pip install -e .[dev]
pytest
uvicorn app.main:app --reload
```

## Example import request

```bash
curl -X POST http://localhost:8000/api/v1/imports \
  -H "Content-Type: application/json" \
  -d '{"connector": "virtualdj", "source_uri": "/music/VirtualDJ/database.xml"}'
```
