# Resume For Next Chat

Use this file first when resuming the project in a new conversation.

## Short Resume

The project is a working local crypto trading MVP with:

- FastAPI backend
- React/Vite frontend
- PostgreSQL + Alembic
- auth, admin flows, assignments, signal scan/execute, overlays, trades
- Telegram notifications
- worker/demo engine with config-based startup gating
- mock/local/live market-data modes

The project is no longer only in a local-dev phase:

- a local Git repository was initialized
- the project was pushed to an existing GitHub repo
- an audit was done to prepare migration to a new private GitHub repo

## Current Local State

- backend tests pass
- frontend build passes
- backend serves the built frontend locally on `http://127.0.0.1:8000/`
- schema supports multiple strategies on the same symbol
- local admin currently has BTC assignments for:
  - `SMC_H4_M15`
  - `SMC_H1_M5`
- UI now exposes runtime state and separates strategy monitoring more clearly
- scripts exist for local auto-demo startup/shutdown:
  - `scripts/start_auto_demo_local.ps1`
  - `scripts/start_auto_demo_live.ps1`
  - `scripts/stop_auto_demo.ps1`

## Git / Repo State

- current local branch: `main`
- current local repo is clean
- current remote `origin` still points to the old repo:
  - old public GitHub remote still configured locally
- latest pushed commits include:
  - initial project snapshot
  - improved README and demo deployment docs

## Audit Outcome

Quick audit conclusions:

- no real `.env` secrets were found in tracked files
- `.env` is ignored correctly
- logs, `venv`, `node_modules`, `dist`, and local artifacts are ignored
- however, the old public identity is still visible in code/docs/UI:
  - legacy public branding
  - old product wording in several files
- weak/example defaults are still visible in code/examples:
  - weak placeholder secrets
  - example DB URLs
- this means the next step before pushing to a new private repo should be a local rename/repositioning pass

## Immediate Next Work

The next conversation should focus on:

1. renaming/repositioning the project locally to reduce continuity with the old public repo
2. reviewing what product name should replace old labels in code/docs/UI
3. switching `origin` to the new private GitHub repo once provided
4. pushing only the cleaned/repositioned version to the new private repo

## Read Next

After this file, read:

- `docs/CURRENT_STATE.md`
- `docs/CURRENT_TASK.md`
- `docs/AI_CONTEXT.md`
