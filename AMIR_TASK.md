# Amir's contribution log (private)

## EM-001: Django project scaffold

- **Status:** Done. Pushed to `main` as `c99257f` (challenge materials + `.gitignore`) and `3e630f9` (Django scaffold).
- **What I set up:**
  - The backend skeleton the pair builds on: Django 5.2 LTS in `backend/solution/`, with a `config` project, a `portfolio` app and a root `constants.py`.
  - Env-based settings and a repo-wide `.gitignore`.
- **Key files and interfaces:**
  - `backend/solution/config/settings.py`: `_require_env()` raises `ImproperlyConfigured` on a missing key. `DJANGO_SECRET_KEY` and `CRM_BASE_URL` are required; `DJANGO_DEBUG` and `DJANGO_ALLOWED_HOSTS` are optional.
  - `config/urls.py` includes `portfolio.urls` at `""`. `portfolio/urls.py` has `app_name = 'portfolio'` and empty patterns.
  - Also added `requirements.txt` (pinned), `.env.example` and `backend/solution/README.md`.
  - Filled in the AGENTS.md stack rows (a shared file).
- **Reasoning and tradeoffs:**
  - Plain Django over DRF: fewer dependencies, and full control over the `{error, message}` error shape.
  - 5.2 LTS over 6.1: support window, and it runs on Python 3.14 from 5.2.8.
  - python-dotenv over django-environ: smaller and explicit, and it meets the AGENTS.md fail-fast rule.
- **Edge cases found:**
  - Python 3.14 needs Django 5.2.8 or later.
  - A shell hook (a Node version manager reading `engines` in `package.json`) fails on `cd` into the repo root. Use absolute paths or `git -C`.
- **Tests run (actual results):**
  - `manage.py check`: "System check identified no issues (0 silenced)."
  - Missing `DJANGO_SECRET_KEY`: raises `ImproperlyConfigured` with a clear message.
  - `runserver 3000`: `GET /` returns 200 (the Django welcome page, since DEBUG is on and there are no routes yet), and `GET /portfolios/P-9001` returns 404.
  - `git ls-files` contains no `.venv`, `.env.local`, `AMIR_*` or `CLAUDE.local.md` paths.
- **Collaboration:** Pushed directly to `main` so the partner can branch from it. Partner setup is in `backend/solution/README.md`.
- **AI assistance:** Claude proposed the options and tradeoffs, and I chose each one. Claude generated the scaffold, and I verified it with the checks above.
- **Limitations / next:**
  - No test runner chosen yet.
  - No `utils` module (ApiError, JSON 404/500 handlers).
  - Storage is undecided.
  - No endpoints yet.
- **Talking points:**
  - Fail-fast config.
  - Spec-matching unprefixed routes.
  - Kept the challenge materials and our solution in separate commits.

## EM-AN-001-T01: Task 1, `GET /portfolios/:id` via the CRM

- **Status:** Pushed as 5 commits on `EM-AN-001-T01` (`4ae6f47`..`b65766a`). The PR against `main` still has to be opened by Amir from the compare link, because `gh` isn't installed. The suite was rerun on the committed code before pushing: 67 passed in 4.15s.
- **What I designed:**
  - `get_crm_data(portfolio_id)` is the single entry point for CRM data: normalize the id, then fetch, then validate and map. Task 9 (cache) and Task 7 (currency) will build on it without re-validating.
  - I made every validation, normalization and error-handling decision; they are in AMIR_DECISIONS.md.
- **Key files and interfaces:**
  - `utils.py` (shared): `ApiError`, `error_response`, `DecimalJSONEncoder`.
  - `constants.py` (shared): CRM timeout 2s, 1 retry, path, id pattern, supported currencies.
  - `portfolio/crm_client.py`: `fetch_crm_portfolio`, which does the HTTP call, retry and error mapping.
  - `portfolio/normalizers.py` (pure): `normalize_portfolio_id`, `normalize_crm_portfolio`, `MONEY_FIELDS`.
  - `portfolio/services.py`: `get_crm_data`.
  - `views.py`, `urls.py`: thin view and route.
  - New files: `requirements-dev.txt`, `pytest.ini`.
- **Reasoning and tradeoffs:**
  - Decimal end to end, with float only in the JSON output. This keeps Task 7's conversion and rounding exact.
  - Nullable values but required identity fields. The client sees what is unknown, and nothing is invented.
  - Retry only on transient failures, since bad data is deterministic.
  - A bad CRM payload returns 400 `crm_bad_response`, so it is clearly the CRM's data and not our code. Outages give 502 and timeouts 504.
- **Bugs and edge cases handled:**
  - The CRM returns all of the client's accounts, so the account is selected by `acct_ref` and not the first one.
  - Nested accounts location.
  - `mode=missing` gives nulls.
  - The id is stripped and uppercased (`p-9002 ` works).
  - `bool` is rejected as a number.
  - NaN and Infinity in JSON are rejected.
  - A naive timestamp gives `asOf` null.
  - The 10s CRM hang is capped at about 4s.
- **Tests run (actual results):**
  - `pytest -v`: **67 passed in 4.41s**. That includes 6 integration tests against the real mock CRM:
    - modes `ok`, `nested`, `missing` and `error` (CRM call count checked: 2 = 1 + retry), plus `timeout` (504 in under 6s)
    - an unknown id (404)
  - Manual curl:
    - `P-9001` and `p-9002 ` give 200.
    - `UNKNOWN` gives 404, and `bad!id` gives 400.
    - `mode=missing` gives 200 with nulls.
- **Integration with partner's Task 2 (merged `main` into my branch):**
  - `b7b4802` merged their work. There were 4 conflicts:
    - `utils.py`: took the partner's version, since it is a superset with the same interface.
    - `constants.py`, `urls.py`, `views.py`: kept both sides.
  - `50a4095`: I chose to adopt the partner's `@api_get` / `json_response` for my view. It now returns a JSON 405 and allows HEAD, which closed my "plain 405" gap.
  - Tests after the merge:
    - `pytest`: 103 passed (my 67 + their 36).
    - `manage.py test`: Ran 36, OK.
    - `manage.py check`: clean.
  - Found during integration (raised with the partner rather than editing their files):
    - Their `data.require_portfolio` compares the raw id to my uppercased `portfolioId`, so `/portfolios/p-9001/holdings` would give 502 once wired.
    - Holdings would depend on the live CRM until Task 9.
    - Decision: wire `GET_CRM_DATA_CALLABLE=portfolio.services.get_crm_data` after Task 9.
    - `manage.py test` misses my 67 pytest tests. Decision: the team uses `pytest` (it runs both styles).
- **AI assistance:** Claude listed the options and tradeoffs, and I made every call. Claude wrote the code and tests; I reviewed them against the plan, and the results above come from real runs.
- **Limitations / next:**
  - No auth yet (Task 4, partner).
  - No cache yet (Task 9 next).
  - No `?currency` yet (Task 7).
  - `normalizers.py` imports `ApiError` from `utils`, which imports Django's `JsonResponse`. So it is not strictly Django-free.
- **Talking points:**
  - One validated entry point that other tasks reuse.
  - Status codes that tell callers who is at fault.
  - Retries tuned to the mock's failure pattern.

## EM-AN-003-T07: Task 7, currency display with live rates

- **Status:** Committed on `EM-AN-003-T07` as 6 commits (`7c7c5a7`..`d61b05f`). Pushed. The PR to `main` is opened by Amir from the compare link (`gh` isn't installed). Performance-history conversion was left out of this PR (follow-up).
  - Before committing, I pulled `main`, which now includes the partner's Task 3, and resolved a `views.py` conflict by keeping their `performance_history` view unchanged.
  - Tests after the merge:
    - `pytest`: 205 passed, 1 deselected.
    - `manage.py test`: Ran 71, OK.
    - `manage.py check`: clean.
- **What I designed:**
  - I replaced the spec's static 0.73 with live CAD→USD rates from ExchangeRate-API.
  - Rates are cached until the provider's daily update, with a last-good-rate fallback and a 5-min failure cooldown.
  - Conversion goes through shared helpers (`apply_currency`), applied to my `/portfolios/:id` and the partner's `/holdings`.
  - I made every decision; they are in AMIR_DECISIONS.md.
- **Key files:**
  - `portfolio/currency.py` (pure): `normalize_currency`, `convert_amount`, `convert_record`, `HOLDING_MONEY_FIELDS`.
  - `portfolio/fx_client.py`: `fetch_pair_rate`, `FxError`. The key is never logged.
  - `portfolio/fx_service.py`: `get_exchange_rate`, `apply_currency`, `reset_cache`.
  - `services.py`: `get_portfolio` and `get_portfolio_holdings`.
  - `views.py`: both views pass `?currency`.
  - Normalizer: the native currency must be CAD.
  - Constants: FX settings plus `NATIVE_CURRENCY` and `MONEY_QUANTUM`.
  - Settings: `EXCHANGE_RATE_API_KEY` is required.
- **Reasoning and tradeoffs:**
  - Cache until `time_next_update_unix`, about 1 call/day. This protects the free-plan quota and avoids the ~0.36s latency.
  - Serve the last good rate rather than a fictional one.
  - Round only converted money (once, after conversion), so CAD responses are unchanged.
  - Per-item metadata keeps the holdings array contract.
- **Edge cases handled:**
  - An invalid currency costs no CRM or FX call.
  - CAD works even when FX is down.
  - Provider error-types are not retried (they don't help, and they use quota).
  - A provider `next_update` already in the past would have meant a call per request; it is guarded with the cooldown.
  - The API key is kept out of logs and exception messages (tested).
  - USD holdings sum equals the USD portfolio total (34348.86 = 34348.86).
- **Tests run (actual results):**
  - `pytest`: **170 passed, 1 deselected** (`fx_live`), 98 subtests.
  - `pytest -m fx_live`: 1 passed (a real API call).
  - `manage.py test`: Ran 36, OK.
  - `manage.py check`: clean.
  - Fail-fast check: no key gives `ImproperlyConfigured`.
  - Manual curl:
    - CAD gives exchangeRate 1.
    - `?currency=usd` gives 34348.86 at 0.702.
    - EUR gives 400.
    - USD holdings sum to 34348.86.
- **Collaboration:**
  - Edited the partner's `test_holdings.py` (2 lines: a `CURRENCY_FIELDS` set added to the endpoint schema check).
  - Their `get_holdings` is untouched.
  - Partner must add `EXCHANGE_RATE_API_KEY` to `.env.local`.
  - Task 3 history should use `apply_currency` once it merges.
- **AI assistance:** Claude researched the API docs, made 3 live calls to inspect real responses, and listed the options. I chose each one. Claude wrote the code and tests, and the results above come from real runs.
- **Limitations / next:**
  - Performance-history isn't converted (Task 3 isn't merged yet).
  - The rate cache is per process, so it resets on restart.
  - Task 9 is next.
- **Talking points:**
  - Live rates with a quota-aware daily cache.
  - Graceful degradation (last good rate, then 503).
  - Consistent cross-endpoint totals.

## Full regression run (after Task 7 PR, on `EM-AN-003-T07`)

- **Automated tests:**
  - `pytest`: 205 passed, 1 deselected, 0 skipped (integration ran against the real mock CRM).
  - `pytest -m fx_live`: 1 passed.
  - `manage.py test`: 71 OK.
  - `check`, `makemigrations --check` and `pip check`: all clean.
  - `node --test support/*.test.mjs`: 5/5.
- **Manual HTTP checks (Tasks 1, 2, 3, 7):**
  - Every status and body matched the spec, including a 504 in 4.0s (not 10s) and a 502 on CRM error.
  - Ranges: 1D = 1 point, 1M = 31, YTD from 01-01, 1Y = 366; P-9002 has 60 points.
  - USD holdings sum = USD portfolio total (34348.86).
- **Findings to raise with the partner:**
  - Tasks 2 and 3 return 404 for lowercase ids (`p-9001`), while Task 1 returns 200. Their `require_portfolio` doesn't normalize ids.
  - Unknown routes return Django's HTML debug page when DEBUG=True (JSON 404 only when DEBUG=False).

## Where I overruled the AI

| Topic | AI recommended | My decision | Outcome |
|---|---|---|---|
| Ignoring private files | `.git/info/exclude` (names hidden from partner) | List them in the shared `.gitignore` | Done; the names are visible in the pushed `.gitignore` |
| Id normalization | Pattern check only, case preserved | strip + uppercase, then pattern check; 400 "Invalid ID provided." | Done; `p-9002 ` resolves to P-9002 |
| FX API key at startup | Optional; 503 only when conversion needed (partner not blocked) | Required, fail fast | Done; the partner must add the key |
| Bad CRM payload status | 502 `crm_bad_response` | 400 `crm_bad_response`. Outages stay 502 and timeouts 504 | Done |

## Directions I set

- Django solution lives in `backend/solution/`. The project is named `config`, the app `portfolio`, and `constants.py` sits at the project root.
- Use a `.venv` virtualenv, shared with the pair via `requirements.txt`.
- Push the initial scaffold straight to `main`.
- Branch naming: `EM-AN-<odd number>-T<nn>`. The first task branch is `EM-AN-001-T01`, cut from `main` at `3e630f9`.
- Took Tasks 1, 9 and 7 together because they share the CRM data path. Task 1 comes first.
- Named the main function `get_crm_data` and made it the single reusable entry point for validated CRM data.
- Added a CRM retry policy myself (2s timeout + 1 retry, configured in `constants.py`) after noticing the mock fails 1 call in 5.
- Task 7 uses live ExchangeRate-API rates instead of the static seed rate. The native currency must be CAD.
