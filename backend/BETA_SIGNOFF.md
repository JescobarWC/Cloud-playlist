# Backend Beta Sign-off Template

Date: ____-__-__
Branch/Tag: __________________
Environment: __________________

## Required gates

- [ ] `backend-postgres-ci` green for 3 consecutive runs
- [ ] `pytest -q -m postgres_live` green
- [ ] `pytest -q -m "not postgres_live"` green
- [ ] `GET /health` returns `{"status":"ok"}`
- [ ] `GET /ready` returns `{"status":"ready", "checks":{"storage":"ok"}, ...}`
- [ ] Alembic migration verification completed by second reviewer
- [ ] Smoke API flow validated (playlist/track/playback/analysis-job)
- [ ] Rollback target (image/tag/version) documented

## Evidence links

- CI run #1: __________________
- CI run #2: __________________
- CI run #3: __________________
- Smoke test run / logs: __________________
- Migration verification notes: __________________
- Rollback reference: __________________

## Go/No-Go decision

- Decision: [ ] GO  [ ] NO-GO
- Notes: ______________________________________________

## Signatures

- Tech Lead: __________________
- QA/Reviewer: __________________
- Ops/Platform: __________________
