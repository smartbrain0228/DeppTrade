# AI Context

This file is intended to help a new AI assistant resume work quickly and accurately.

## Project Goal

Build a web-based crypto trading copilot with:

- user authentication
- exchange-backed market data
- strategy analysis and trade signals
- trade execution and monitoring
- operator-facing dashboard UX
- admin bootstrap and configuration flows
- Telegram notifications for operational events

The system supports both manual operator flows and automated demo-trading background logic.

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
- Bootstrap utilities plus custom CSS redesign
- lightweight-charts
- websocket updates

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

## What Was Recently Fixed

An assistant continuing this project should assume these are already done:

- tests run cleanly from repo root
- frontend build compiles
- startup moved to lifespan
- worker/demo engine no longer auto-start in dev/test unless explicitly enabled
- backend market data now supports deterministic mock/local mode
- Telegram integration was aligned with assignment-level balances
- local `.env` handling is safer and root `.gitignore` now protects secrets
- Telegram local test script was corrected
- frontend received a strong visual redesign
- watchlist layout was improved to avoid overlapping cards
- frontend supports switching between multiple strategies for the same symbol
- schema now allows multi-strategy assignments on the same user/symbol pair

## Current Risks / Constraints

- live market data still requires network access when `MARKET_DATA_MODE=live`
- local multi-strategy bootstrap is improved, but setup scripts still need cleanup for perfect repeatability
- responsive frontend quality is better than before, but not fully finished
- deployment/runbook docs are still not comprehensive

## Files That Matter Most

- `trading_bot_backend/app/main.py`
- `trading_bot_backend/app/config.py`
- `trading_bot_backend/app/models.py`
- `trading_bot_backend/app/routes/`
- `trading_bot_backend/app/services/`
- `frontend/src/pages/Home.tsx`
- `frontend/src/components/`
- `frontend/src/services/api.ts`
- `frontend/src/store/useTradingStore.ts`
- `docs/CURRENT_STATE.md`
- `docs/CURRENT_TASK.md`

## Important Local Facts

- backend local URL: `http://127.0.0.1:8000/`
- separate frontend dev URL, if running: `http://127.0.0.1:4173/`
- Telegram credentials are expected in `.env`
- current local admin data includes BTC assignments for:
  - `SMC_H4_M15`
  - `SMC_H1_M5`

## Resume Guidance

If starting a new conversation, do not assume the project is an early scaffold.

Assume instead:

- the local baseline is functional
- tests/builds are green
- the frontend has already been visually redesigned
- Telegram is already integrated
- the system now supports multiple strategies per symbol
- the remaining work is mainly setup hardening, responsive polish, observability, docs, and deeper operational robustness
