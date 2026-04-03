# Current State

This document reflects the actual local state of the project as of 2026-04-03.

## Overall Status

The project is a working local MVP with:

- usable FastAPI backend
- redesigned React frontend
- multi-strategy assignment support
- scan / execute / overlays / trade activity
- Telegram integration
- worker + demo engine support
- runtime visibility in the UI
- Git repository now initialized and pushed once to GitHub

This is no longer just a local coding sandbox. It is now in transition from local MVP to a cleaner private product codebase.

## Verified Working

The following were validated recently:

- backend tests pass
- frontend production build passes
- backend serves built frontend locally
- auto-demo startup scripts exist for `mock` and `live`
- docs now include a clearer README and demo deployment runbook

Validated snapshot:

- `pytest`: `48 passed`
- `frontend`: `npm run build` passes

## Important Recent Changes

These are part of the current baseline:

- demo engine bug around missing `analysis["assignment"]` was fixed
- Telegram notification failures were downgraded to less noisy logs after first failure
- overview UI now exposes runtime state:
  - environment
  - market mode
  - worker on/off
  - demo engine on/off
  - Telegram configured or not
- admin monitoring UI now separates strategy outcomes more clearly:
  - `Wins`
  - `Fails`
  - `Skipped`
- local PowerShell scripts were added for auto-demo runs:
  - local mock mode
  - local live mode
  - stop script
- Git was initialized locally
- first commits were created and pushed to the current GitHub repo
- README and demo deployment docs were rewritten

## Git / Privacy State

Current repo state:

- branch: `main`
- working tree: clean
- current remote `origin` still targets the old repo

Audit findings:

- real secrets are not present in tracked files
- `.env` is not tracked
- ignored artifacts are handled correctly
- older public-facing project identity still exists in code/docs/UI:
  - legacy public branding strings
- some example/default credentials remain visible in code/examples:
  - weak placeholder secrets
  - example DB URLs

This means migration to a new private repo should be preceded by a rename/repositioning pass if the goal is to reduce obvious continuity with the old public repo.

## Current Operational Caveats

- live market mode still depends on exchange connectivity
- local auto-demo is possible but local observation is still less stable than a real server
- deployment docs are better than before, but production hardening is still not done
- the codebase still carries older naming and messaging that should be revised before private migration

## Useful Local URLs

- backend + built frontend: `http://127.0.0.1:8000/`
- frontend dev server, when launched separately: `http://127.0.0.1:4173/`
- auto-demo mock target: `http://127.0.0.1:8002/`
- auto-demo live target: `http://127.0.0.1:8003/`

## Recommended Next Work

The best next phase is now:

1. locally rename/reposition the project away from the old public identity
2. update code/docs/UI labels that still expose the older branding
3. replace the current GitHub remote with the new private GitHub repo
4. push only the cleaned/repositioned version to the new private repo
5. after that, resume deployment planning for demo automation
