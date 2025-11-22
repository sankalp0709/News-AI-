# Release Notes v1

## Overview
Initial staging-ready build of Insight Narrator Node with scheduler, RL loop improvements, tests, and staging endpoint for frontend integration.

## Features
- Scheduler (`scripts/scheduler.py`) with hourly/4-hour/daily modes, daemon support, and rotating logs.
- RL feedback loop with reward shaping via `RL_WEIGHTS_JSON` and actions: queue, requeue, demote.
- Metadata now includes `confidence_score` and runtime `rl_reward_score` on feedback.
- Staging endpoint `/processed/sample` for frontend consumption.

## Endpoints
- `POST /feedback` → returns `{ id, reward, action, requeued, queued, demoted }` and writes `reward_score`.
- `POST /requeue` → returns `{ id, requeued }`.
- `GET /processed/sample` → item with fields: `id, script, tone, confidence_score, audio_path, priority_score, trend_score, rl_reward_score`.

## Logging
- Rotating logs: `logs/server.log`, errors at `logs/errors.log`.
- Scheduler logs: `logs/scheduler.log`, errors at `logs/errors.log`.

## Tests
- Unit tests under `tests/` and integration runner `scripts/run_full_test.py`.

## Run
- API server: `python scripts/api_server.py --port 8500`
- Scheduler: `python scripts/scheduler.py hourly --daemon`