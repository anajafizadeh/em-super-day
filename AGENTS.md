# AGENTS.md

> **Claude Code users:** Claude Code reads `CLAUDE.md`, not `AGENTS.md`. Add a `CLAUDE.md` (or `CLAUDE.local.md`) whose first line is `@AGENTS.md`. Codex and Cursor read this file directly.

## Session context

- Pair session: two developers, about [TBD] hours, one shared git repo, any AI tools.
- We split the tasks, work in parallel and integrate often. Keep `main` green.
- Do not make any assumptions, make any decisions on your own. Make suggestions when you're unsure but the developers make the final decision.

## Stack & commands

| | |
|---|---|
| Language / framework | **TBD** |
| Install | **TBD** [Once we tell you the stack, fill in this one youself] |
| Run app | **TBD** [Once we tell you the stack, fill in this one youself] |
| Run tests | **TBD** (e.g. `pytest`) |
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