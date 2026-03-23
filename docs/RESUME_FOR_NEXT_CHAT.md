# Resume For Next Chat

Use this file first when resuming the project in a new conversation.

## Short Resume

The project is a working local crypto trading copilot MVP with:

- FastAPI backend
- React/Vite frontend
- PostgreSQL + Alembic
- auth, admin flows, assignments, signal scan/execute, overlays, trades
- Telegram notifications
- worker/demo engine with config-based startup gating
- mock/local market-data mode for local validation

## Current Local State

- backend tests pass
- frontend build passes
- backend serves the built frontend locally on `http://127.0.0.1:8000/`
- Telegram works when `.env` is configured
- frontend has been visually redesigned
- schema now supports multiple strategies on the same symbol
- local admin currently has BTC assignments for:
  - `SMC_H4_M15`
  - `SMC_H1_M5`

## Main Remaining Work

- make local multi-strategy setup scripts fully repeatable
- continue responsive/frontend polish
- improve runbook and deployment docs
- add tests around multi-strategy assignment behavior
- improve runtime observability

## Read Next

After this file, read:

- `docs/CURRENT_STATE.md`
- `docs/CURRENT_TASK.md`
- `docs/AI_CONTEXT.md`
