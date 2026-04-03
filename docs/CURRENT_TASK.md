# Current Task

## Immediate Objective

Prepare the codebase for migration from the current GitHub repo to a new private GitHub repo with reduced continuity to the old public-facing identity.

## What Is Already Done

- local Git repo initialized
- `main` branch created
- initial commit created
- README improved
- demo deployment runbook added
- current repo pushed once to the existing GitHub repo
- quick privacy audit completed

## Effective Current State

As of 2026-04-03:

- backend tests pass: `48 passed`
- frontend build passes
- local repo is clean
- current `origin` still points to the old GitHub repo
- audit found no tracked real secrets
- audit did find older branding / naming that should be replaced before migration

## Main Remaining Work

The most useful next work is now:

1. choose the new project/product name
2. replace old public-facing labels in:
   - docs
   - frontend UI
   - backend app name / messages
3. decide whether default/example credential strings should be tightened
4. switch `origin` to the new private GitHub repo
5. push the cleaned version

## Recommended Order

1. rename visible identity in code/docs/UI
2. re-check privacy-sensitive strings
3. update Git remote
4. push to the new private repo
5. then continue with deployment planning

## Constraints

- do not expose secrets in docs, code, or chats
- avoid unnecessary destructive Git operations
- preserve working functionality while renaming project identity
- keep route/service architecture intact

## Useful Commands

```powershell
git remote -v
git status --short
git log --oneline -5

git remote set-url origin <NEW_PRIVATE_REPO_URL>
git push -u origin main
```

## Resume Hint For Next Conversation

Use this summary:

"The project is a working local crypto trading MVP with FastAPI, React/Vite, PostgreSQL, Telegram integration, multi-strategy assignments, and auto-demo support. Tests and frontend build are green. A local Git repo was initialized and pushed once to the old GitHub repo, but a privacy/identity audit showed that legacy public branding still appears in code/docs/UI. No real secrets were found in tracked files. The immediate next step is to rename/reposition the project locally, then switch `origin` to the new private GitHub repo and push only the cleaned version."
