# Current State

This document reflects the actual local state of the project as of 2026-03-22.

## Overall Status

The project is now a working local MVP with a usable backend and a redesigned frontend.

What currently exists:

- authentication and session bootstrap
- admin seed/configuration flows
- user assignments by symbol and strategy
- strategy analysis and signal scan/execute flows
- trade listing and management
- signal history and overlay payloads
- Telegram notifications for key trading events
- background worker and demo engine with environment-aware startup
- deterministic mock/local market-data mode for local validation
- frontend dashboard with overview, assignments, chart, overlays, signal actions, trade activity, and admin monitoring

The frontend is no longer just a default Bootstrap-looking shell. It now has a coherent visual redesign and better responsive behavior, though mobile polish can still be improved further.

## Verified Working

The following have been validated locally:

- backend test suite passes
- frontend TypeScript build passes
- frontend production build passes
- backend local server responds on `http://127.0.0.1:8000/`
- frontend is served locally through the backend root route
- Telegram message sending works when local credentials are configured
- schema and runtime now support multiple strategies on the same user/symbol pair

Latest validation snapshot:

- `pytest`: `44 passed`
- `frontend`: `npm run build` passes
- local backend root: `http://127.0.0.1:8000/` returns frontend HTML

## Important Recent Fixes

These changes are part of the current baseline:

- root `.gitignore` was added so `.env` and local secrets are not accidentally tracked
- Telegram local test script was fixed and aligned with the real notification service
- local secrets were hardened in `.env`:
  - `JWT_SECRET_KEY`
  - `ADMIN_SESSION_SECRET`
  - `ADMIN_PASSWORD`
- Telegram variables are now confirmed as loaded from `.env`
- frontend received a major visual redesign:
  - redesigned login screen
  - redesigned dashboard shell/header
  - improved trading workspace presentation
  - improved trade activity panel
  - improved admin monitor presentation
  - dark chart surface with better visual contrast
- frontend watchlist was reworked to avoid blurred overlapping cards
- frontend now exposes multiple strategy setups for the same symbol more clearly
- assignment selector now supports switching between multiple strategies for one symbol
- backend schema was corrected for true multi-strategy assignments:
  - `user_pair_strategies` uniqueness is now `(user_id, symbol_id, strategy_id)`
- admin assignment API logic was updated so it no longer overwrites one strategy with another on the same symbol
- local admin data now includes both BTC strategies:
  - `SMC_H4_M15`
  - `SMC_H1_M5`

## Current Data / Local Demo State

For the current local admin account, the BTC assignments now include:

- `BTC/USDT` + `SMC_H4_M15` (`H4/M15`)
- `BTC/USDT` + `SMC_H1_M5` (`H1/M5`)

This means the frontend can now show multiple strategies for the same symbol, assuming the session is refreshed.

## Telegram Status

Telegram integration is present and wired into the app.

Current notification flows include:

- trade opened
- trade closed
- trade skipped
- strategy paused
- daily summary

Important implementation details:

- credentials are loaded from `.env`
- no Telegram secrets are stored in code
- only safe URL buttons remain in Telegram messages
- notifications use assignment-level balances, not the removed user-level balance field

## Current Operational Caveats

The project is stable locally, but these caveats still matter:

- live market data still depends on external exchanges when `MARKET_DATA_MODE=live`
- worker and demo engine are controlled by config, but if enabled in live mode they still rely on exchange connectivity
- deployment/runbook documentation is still lighter than the implementation
- frontend responsiveness is better than before, but still not fully polished on all small-screen layouts
- local multi-strategy setup scripts may still need cleanup for smoother repeatability

## Current Environment Behavior

By default:

- in `development` and `test`, the background trade worker is disabled unless `ENABLE_WORKER=true`
- in `development` and `test`, the demo engine is disabled unless `ENABLE_DEMO_ENGINE=true`
- market data remains live unless `MARKET_DATA_MODE=mock` or `MARKET_DATA_MODE=local`

This keeps local work quieter and safer.

## Useful Local URLs

- backend + built frontend: `http://127.0.0.1:8000/`
- frontend dev server, when launched separately: `http://127.0.0.1:4173/`

## Recommended Next Work

The best next phase is not broad feature sprawl. It is controlled stabilization and polish:

1. clean up local multi-strategy setup/bootstrap so repeated environment setup is deterministic
2. continue responsive/frontend UX polish, especially on smaller screens
3. improve deployment-oriented docs and runtime observability
4. expand tests around multi-strategy assignment behavior and admin flows
5. decide whether current runtime mode should be surfaced in the UI
