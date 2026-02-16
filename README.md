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
- Import job fetch endpoint `GET /api/v1/imports/{job_id}`
- Library normalization endpoint `POST /api/v1/normalize`
- VirtualDJ parser preview endpoint `POST /api/v1/connectors/virtualdj/preview`
- Playlist management endpoints (`POST /api/v1/playlists`, `POST /api/v1/playlists/{id}/tracks`, `GET /api/v1/playlists/{id}`)
- Track analysis endpoint `POST /api/v1/tracks/{track_id}/analyze` (MVP WAV waveform/BPM/key)
- Async analysis jobs endpoints (`POST /api/v1/playlists/{id}/analysis-jobs`, `GET /api/v1/analysis-jobs/{job_id}`, `POST /api/v1/analysis-jobs/{job_id}/cancel`)
- Duplicate finder and find/replace tools endpoints (`/api/v1/tools/*`) with undo
- Playback transport endpoints for playlists (`GET/POST /api/v1/playlists/{id}/playback*`) with clock-synced position progression
- Connector normalization support for `rekordbox`, `serato`, `virtualdj`, `m3u`, and `csv`
- SQLite-backed import job persistence (`backend/data/app.db`) for local development
- Storage backend selection groundwork via env (`DJ_STORAGE_BACKEND=sqlite|postgres`)
- Alembic baseline for PostgreSQL schema (`backend/alembic/*`)
- Basic pytest coverage for connector normalization, library normalization mapping, and health/API behavior
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


## Example normalization request

```bash
curl -X POST http://localhost:8000/api/v1/normalize \
  -H "Content-Type: application/json" \
  -d '{"connector":"Virtual DJ","tracks":[{"id":"t1","title":"Titanium","artist":"David Guetta","bpm":"126"}],"playlists":[{"id":"p1","name":"Main","track_ids":["t1"]}]}'
```


## Example VirtualDJ preview request

```bash
curl -X POST http://localhost:8000/api/v1/connectors/virtualdj/preview \
  -H "Content-Type: application/json" \
  -d @virtualdj-preview.json
```

Where `virtualdj-preview.json` contains:

```json
{
  "database_xml": "<VirtualDJ_Database><Song FilePath=\"/music/a.mp3\"><Tags Author=\"Artist A\" Title=\"Track A\" Bpm=\"124\"/></Song></VirtualDJ_Database>"
}
```


## Example get import job request

```bash
curl http://localhost:8000/api/v1/imports/<job_id>
```


## Example playlist + analysis flow

```bash
# 1) Create playlist
curl -X POST http://localhost:8000/api/v1/playlists \
  -H "Content-Type: application/json" \
  -d '{"name":"Warmup"}'

# 2) Add track to playlist
curl -X POST http://localhost:8000/api/v1/playlists/1/tracks \
  -H "Content-Type: application/json" \
  -d '{"title":"Track A","artist":"Artist A","file_path":"/path/to/file.wav"}'

# 3) Analyze track waveform/BPM/key
curl -X POST http://localhost:8000/api/v1/tracks/1/analyze

# 4) Fetch playlist with analysis metadata
curl http://localhost:8000/api/v1/playlists/1
```

> Note: analysis supports 16-bit PCM WAV/AIFF directly; other formats require `ffmpeg` to be installed for decode.


## Example playback transport flow

```bash
# Start playback
curl -X POST http://localhost:8000/api/v1/playlists/1/playback/play

# Seek 42s
curl -X POST http://localhost:8000/api/v1/playlists/1/playback/seek \
  -H "Content-Type: application/json" \
  -d '{"position_seconds":42}'

# Jump to next track
curl -X POST http://localhost:8000/api/v1/playlists/1/playback/next

# Load a specific track in deck state
curl -X POST http://localhost:8000/api/v1/playlists/1/playback/load \
  -H "Content-Type: application/json" \
  -d '{"track_id":2}'

# Read playback state
curl http://localhost:8000/api/v1/playlists/1/playback
```


## Example async analysis job flow

```bash
# 1) Create analysis job for playlist 1
curl -X POST http://localhost:8000/api/v1/playlists/1/analysis-jobs

# 2) Poll status
curl http://localhost:8000/api/v1/analysis-jobs/<job_id>

# 3) Cancel if needed
curl -X POST http://localhost:8000/api/v1/analysis-jobs/<job_id>/cancel
```


## Storage backend configuration

Current default backend is SQLite for local development.

- `DJ_STORAGE_BACKEND=sqlite` (default): uses local SQLite repositories.
- `DJ_STORAGE_BACKEND=postgres`: wired for import-jobs and library/playback/tools/analysis repositories via SQLAlchemy-backed adapters (factory-selected).
- `DJ_SQLITE_DB_PATH`: optional override for SQLite file path.
- `DATABASE_URL`: PostgreSQL connection URL used by the import-jobs adapter path.


## Beta readiness snapshot

Backend scope is close to an internal beta for core DJ-library workflows (imports, playlists, analysis jobs, playback transport, and tools).

Recommended remaining blocks before calling it **beta operativa**:

1. Add CI job that runs tests against a real PostgreSQL service (not only SQLite in-memory SQLAlchemy fallback).
2. Add end-to-end API smoke tests with `DJ_STORAGE_BACKEND=postgres` and `alembic upgrade head` in setup.
3. Add operational basics for production-like beta environments (structured logging, health/readiness depth checks, and minimal rate/error instrumentation).


## Example duplicate + find/replace flow

```bash
# Find duplicate tracks by normalized title+artist
curl http://localhost:8000/api/v1/tools/duplicates

# Preview replace
curl -X POST http://localhost:8000/api/v1/tools/find-replace \
  -H "Content-Type: application/json" \
  -d '{"field_name":"title","search_text":"Song","replace_text":"Track","apply":false}'

# Apply replace
curl -X POST http://localhost:8000/api/v1/tools/find-replace \
  -H "Content-Type: application/json" \
  -d '{"field_name":"title","search_text":"Song","replace_text":"Track","apply":true}'

# Undo replace
curl -X POST http://localhost:8000/api/v1/tools/find-replace/<operation_id>/undo
```


### PostgreSQL migration bootstrap

When running against PostgreSQL, initialize schema with Alembic:

```bash
cd backend
alembic upgrade head
```
