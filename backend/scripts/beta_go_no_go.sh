#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   DATABASE_URL=postgresql+psycopg://... ./backend/scripts/beta_go_no_go.sh
# Optional:
#   BASE_URL=http://localhost:8000  # validates /health and /ready

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[beta-gate] Starting backend Go/No-Go checks"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "[beta-gate] ERROR: DATABASE_URL is required (postgresql+psycopg://...)" >&2
  exit 1
fi

export DJ_STORAGE_BACKEND=postgres
export RUN_POSTGRES_TESTS=1

echo "[beta-gate] Running Alembic migrations"
alembic upgrade head

echo "[beta-gate] Running postgres_live tests"
pytest -q -m postgres_live

echo "[beta-gate] Running non-postgres_live tests"
DJ_STORAGE_BACKEND=sqlite pytest -q -m "not postgres_live"

if [[ -n "${BASE_URL:-}" ]]; then
  echo "[beta-gate] Checking probes at ${BASE_URL}"
  health_payload="$(curl -fsS "${BASE_URL}/health")"
  ready_payload="$(curl -fsS "${BASE_URL}/ready")"

  python - <<'PY' "$health_payload" "$ready_payload"
import json
import sys

health = json.loads(sys.argv[1])
ready = json.loads(sys.argv[2])

assert health.get("status") == "ok", f"health not ok: {health}"
assert ready.get("status") == "ready", f"ready not ready: {ready}"
checks = ready.get("checks") or {}
assert checks.get("storage") == "ok", f"storage check not ok: {ready}"
print("[beta-gate] Probe checks passed")
PY
fi

echo "[beta-gate] SUCCESS: all Go/No-Go checks passed"
