# Project Architecture

This document describes the current technical architecture of the project.

## High-Level Layout

The repository is split into:

- a FastAPI backend in `trading_bot_backend/`
- a React/Vite frontend in `frontend/`
- Alembic migrations in `alembic/`
- pytest-based backend tests in `tests/`
- project context docs in `docs/`

## Backend

### Core Stack

- FastAPI
- SQLAlchemy async ORM
- Alembic
- PostgreSQL
- optional Redis
- JWT auth

### Main Backend Areas

- `trading_bot_backend/app/main.py`
  - application wiring
  - lifespan startup
  - middleware
  - router registration
  - static frontend mounting when `frontend/dist` exists

- `trading_bot_backend/app/config.py`
  - environment-driven settings
  - startup gating for background services

- `trading_bot_backend/app/models.py`
  - users
  - strategies
  - symbols
  - user pair/strategy assignments
  - trades
  - signal events

- `trading_bot_backend/app/routes/`
  - `auth.py`: register/login/bootstrap-admin/me
  - `portal.py`: user overview and assignments
  - `signals.py`: preview, scan, execute, history, overlay
  - `trades.py`: trade CRUD-like operations and multi-strategy stats
  - `admin_config.py`: admin seed/config flows
  - `market.py`: candle access
  - `backtest.py`: backtest endpoint

- `trading_bot_backend/app/services/`
  - `strategy.py`: main strategy analysis logic
  - `market_data.py`: exchange candle access plus deterministic mock/local candle generation
  - `signal_execution.py`: scan/execute coordination
  - `signal_history.py`: signal event persistence/query
  - `signal_overlays.py`: frontend-ready overlay payloads
  - `trade_execution.py`: trade creation/update/risk checks
  - `trade_management.py`: TP/SL/break-even/trailing logic
  - `worker.py`: background monitoring + daily summary
  - `demo_engine.py`: automated demo trading loop
  - `notifications.py` and `telegram_templates.py`: Telegram notifications

### Background Services

There are two background loops:

- trade worker
- demo engine

They are started from app lifespan only when config allows it.

Default behavior:

- disabled in `development`
- disabled in `test`
- can be explicitly enabled with:
  - `ENABLE_WORKER=true`
  - `ENABLE_DEMO_ENGINE=true`

## Data Model Notes

Important model relationships:

- `UserPairStrategy` is the assignment unit between user, symbol and strategy
- assignment-level fields now include:
  - `demo_balance`
  - `trade_count`
  - `is_paused`
- `Trade` stores execution details plus:
  - `spot_bias`
  - `futures_bias`
  - `has_divergence`
  - `skip_reason`
- `SignalEvent` persists scan/execute analysis snapshots

## Frontend

### Core Stack

- React
- TypeScript
- Vite
- Zustand

### Main Frontend Areas

- `frontend/src/pages/Home.tsx`
  - main dashboard composition

- `frontend/src/hooks/`
  - session bootstrap
  - dashboard data refresh
  - scan/execute coordination

- `frontend/src/services/api.ts`
  - REST client layer for auth, overview, assignments, signals, trades

- `frontend/src/services/websocket.ts`
  - live candle subscription

- `frontend/src/store/useTradingStore.ts`
  - persistent session state
  - selected assignment/symbol state
  - dashboard data state

- `frontend/src/components/`
  - dashboard layout
  - overview/trading panels
  - admin monitoring widgets

## Runtime Validation State

Currently verified:

- backend tests pass
- frontend build passes
- core API routes respond correctly locally
- backend market data can run in deterministic mock/local mode for local signal validation

Not fully isolated yet:

- production-like exchange-dependent flows still require external market access when running in live mode

## Architecture Direction

The codebase should continue to preserve these principles:

- keep API routes thin
- keep strategy/trading logic in services
- keep frontend as consumer of backend analysis, not re-implementer of strategy rules
- keep schema changes tracked through Alembic
