# AGENTS.md

> **Claude Code users:** Claude Code reads `CLAUDE.md`, not `AGENTS.md`. Add a `CLAUDE.md` (or `CLAUDE.local.md`) whose first line is `@AGENTS.md`. Codex and Cursor read this file directly.

## Session context

- Pair session: two developers, about [TBD] hours, one shared git repo, any AI tools.
- We split the tasks, work in parallel and integrate often. Keep `main` green.
- Do not make any assumptions, make any decisions on your own. Make suggestions when you're unsure but the developers make the final decision.

## Stack & commands

| | |
|---|---|
| Language / framework | Python 3.14 / Django 5.2 LTS (plain, no DRF). Project in `backend/solution/` |
| Install | `cd backend/solution && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env.local` |
| Run app | `cd backend/solution && python manage.py runserver 3000` (mock CRM: `node backend/mock-crm.mjs`) |
| Run tests | `cd backend/solution && pip install -r requirements-dev.txt && pytest` (integration tests auto-skip unless `node backend/mock-crm.mjs` is running) |
| Storage | **TBD**. |

## Code structure

- **Thin handlers/views.** They only parse the request and turn a result or an error into a response.
- **One main function per task.** It orchestrates the work from small validate/normalize helpers.
- **Pure calculation module.** No framework, HTTP or storage imports, so it's easy to test and to reuse across tasks.
- **Shared root modules:**
  - `utils`: the shared error type (`ApiError(status, error, message)`), an error-response helper, a JSON encoder for Decimal, JSON 404/500 handlers.
  - `constants`: non-secret values from the spec, such as placeholders, supported values, timeouts and retry policy.

## Decisions

- **AI agents ask before making design decisions.** For validation, error handling, data shape and structure, present the options, the tradeoffs and a recommendation, and let the developer choose.

## Secrets & config

- `.env.local` is gitignored. `.env.example`, with placeholders, is committed.
- The app fails fast if required config is missing.