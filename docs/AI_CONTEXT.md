# AI Context

This file is intended to help a new AI assistant resume work quickly and accurately.

## Project Goal

Build a web-based crypto trading system focused on:

- strategy analysis
- signal validation
- demo trade execution and monitoring
- operator-facing dashboard UX
- Telegram notifications
- automated strategy observation in demo mode

The project started as a local MVP and is now moving toward a cleaner private product codebase.

## Stack

### Backend

- FastAPI
- SQLAlchemy async ORM
- Alembic
- PostgreSQL
- optional Redis
- `python-binance`
- `ccxt`

### Frontend

- React
- TypeScript
- Vite
- Zustand
- custom CSS redesign
- lightweight-charts

## Current Product Shape

The app already supports a real local MVP flow:

1. log in
2. bootstrap session
3. load overview
4. load user assignments
5. load candles and overlays
6. scan signal
7. execute if ready
8. refresh overview / trades / overlay
9. observe Telegram notifications for trading events

It also supports auto-demo behavior when enabled:

- demo engine scans active assignments
- worker manages open trades
- runtime state is exposed in the UI

## What Was Recently Fixed

Assume these are already done:

- tests run cleanly from repo root
- frontend build compiles
- startup uses lifespan
- worker/demo engine no longer auto-start in dev/test unless explicitly enabled
- backend market data supports deterministic mock/local mode
- demo engine assignment payload bug was fixed
- Telegram failure logging is less noisy
- UI exposes runtime state
- admin monitor separates strategy results more clearly
- local auto-demo PowerShell scripts were added
- Git repo was initialized locally
- project was pushed to the current GitHub repo once
- a quick privacy audit was completed

## Current Risks / Constraints

- live market mode still depends on exchange/network access
- deployment is not yet fully hardened
- old project identity still appears in code/docs/UI
- current `origin` still points to the old GitHub repo
- next work should avoid leaking continuity unnecessarily before migration to the new private repo

## Files That Matter Most

- `trading_bot_backend/app/main.py`
- `trading_bot_backend/app/config.py`
- `trading_bot_backend/app/models.py`
- `trading_bot_backend/app/routes/`
- `trading_bot_backend/app/services/`
- `frontend/src/components/`
- `frontend/src/pages/Home.tsx`
- `frontend/src/services/api.ts`
- `docs/CURRENT_STATE.md`
- `docs/CURRENT_TASK.md`
- `docs/RESUME_FOR_NEXT_CHAT.md`

## Important Local Facts

- backend local URL: `http://127.0.0.1:8000/`
- frontend dev URL: `http://127.0.0.1:4173/`
- auto-demo mock script targets port `8002`
- auto-demo live script targets port `8003`
- current local admin data includes BTC assignments for:
  - `SMC_H4_M15`
  - `SMC_H1_M5`

## Resume Guidance

If starting a new conversation, do not assume the next priority is feature work.

Assume instead:

- the local baseline is functional
- tests/builds are green
- Git and GitHub preparation has already started
- the next priority is repository/privacy migration
- the immediate job is to rename/reposition locally, then switch to the new private GitHub repo
