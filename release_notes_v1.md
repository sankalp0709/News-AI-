# Release Notes v1

## Overview
- Insight Node ready for staging integration and production hardening.

## Highlights
- Automated scheduler with interval runs and logging.
- RL feedback loop with reward shaping and auto actions.
- Metadata includes `confidence_score` and `rl_reward_score`.
- API endpoints for health, version, feed, feedback, requeue, and sample processed item.
- Full pytest suite and integration runner.
- Architecture diagram at `docs/architecture_v1.png`.

## Endpoints
- `GET /health`
- `GET /version`
- `GET /feed`
- `GET /processed/sample`
- `POST /feedback`
- `POST /requeue`

## Run
- API: `python scripts/api_server.py --port 8500`
- Scheduler: `python scripts/scheduler.py`
- Tests: `pytest -q`
- Integration: `python scripts/run_full_test.py`

## Packaging
- `integration_ready.zip` includes `/scripts`, `/models`, `/exports`, `/docs`, `/tests`.