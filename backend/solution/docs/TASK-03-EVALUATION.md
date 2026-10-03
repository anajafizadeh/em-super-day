# Task 3 Evaluation Report

Evaluation date: October 3, 2026. Branch: `EM-XW-004-T03`.

**Result: PASS for the Task 3 acceptance criteria.** The conflict resolution
preserves all three portfolio endpoints and passes the combined regression
suite. This report evaluates the local integration of Task 3 commit `2b596f3`
with `main` commit `01430a271299faa1035d4f6e88671801404abfb7`; it does not record
a merge of Task 3 into `main`.

## Scope and implementation

The scope is Task 3 in [backend requirements](../../REQUIREMENTS.md):
`GET /portfolios/{id}/performance-history`, with optional `range` and an array
of `{date, marketValue}` snapshots. [Task 3 notes](TASK-03.md) document the
agreed calendar and storage conventions.

`portfolio/views.py` only reads the query parameter and formats the service
result. `get_performance_history` handles portfolio lookup, file loading, and
error mapping. `filter_performance_history` validates and filters snapshots
without Django, HTTP, file access, or a system clock. The caller supplies today,
which makes calendar tests deterministic. Shared errors and JSON encoding stay
in `utils.py`; the five allowed ranges stay in `constants.py`.

## Acceptance evaluation

| Requirement or boundary | Observed behavior and test evidence | Result |
| --- | --- | --- |
| Route and schema | Default request returns only `date` and numeric `marketValue`, in ascending date order; `test_default_all_schema_and_json_number` | PASS |
| All five ranges | Pure and Django request tests verify `1D`, `1M`, `YTD`, `1Y`, and `All`, including both boundaries | PASS |
| Current-year YTD | Starts January 1 of the UTC current year; January 1 itself is covered | PASS |
| Calendar month and year | March 31 clamps to February 28/29; January crosses to December; February 29 clamps in a non-leap target year | PASS |
| Short history and gaps | Returns available snapshots without padding; unit and request tests include a short history queried with `1Y` | PASS |
| Empty and stale history | Explicit `[]` returns HTTP 200; stale history does not shift the range back to the latest stored date | PASS |
| Future snapshots | Excluded for every range, including `All` | PASS |
| Invalid range | Empty, unknown, incorrectly cased, or whitespace-prefixed values return JSON HTTP 400 with `invalid_range` | PASS |
| Unknown portfolio | Returns structured HTTP 404; checked with both the local registry and actual Task 1 helper | PASS |
| Invalid storage | Missing file/portfolio entry, malformed JSON, invalid dates/numbers, and duplicate dates return structured HTTP 503 | PASS |
| Numeric and date validation | Rejects booleans, numeric strings, non-finite/oversized values, and noncanonical dates; zero and negative market values remain valid | PASS |
| Freshness and isolation | Reads file and UTC date per request; tests verify file updates, date changes, and no mutation of input rows | PASS |
| HTTP behavior | HEAD has no body; unsafe methods return JSON HTTP 405 with `Allow: GET, HEAD`, including with CSRF checks enabled | PASS |

Named tests are in [test_performance.py](../portfolio/test_performance.py).
Shared file loading, metadata-adapter contracts, and JSON errors are covered by
[test_shared.py](../portfolio/test_shared.py).

## Executed validation

Tests ran in
`C:\Users\wangx\Desktop\Electric Mind\EM-XW-004-T03\backend\solution`,
using Python 3.14.8, Django 5.2.17, pytest 9.1.1, and pytest-django 4.14.0.
The merged code was tested before its conflict-resolution commit.

| Check | Actual result |
| --- | --- |
| Complete pytest suite | **138 passed, 169 subtests passed**, 5.33 seconds; no failures, errors, or skips |
| Task 3 contribution to that run | 35 tests: 18 pure filtering tests and 17 Django request tests |
| Other regression coverage in that run | 25 Task 2 tests, 11 shared tests, and 67 Task 1 tests, including 6 real mock-CRM integration tests |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Installed dependency compatibility | All 17 installed packages compatible (`uv pip check`) |
| Supplied Node mock regression suite | 5 passed, no failures/skips; Node.js 22.19.0 |
| Combined routes with the actual Task 1 adapter | GET and HEAD succeeded for metadata, holdings, and history; verified 6 CRM calls |
| Combined error responses | 12 unsafe-method requests returned JSON 405; unknown route and Task 2/3 unknown portfolio IDs returned JSON 404 |
| Existing generated history smoke check | 401 ascending snapshots; latest market value 48,930, matching the sum of current holdings |

The CRM tests used a separate Node mock on a dynamically allocated loopback
port (`54031` for this run). It was stopped after validation. The extra adapter
smoke checks used Django's test client plus real network calls to that mock,
with `GET_CRM_DATA_CALLABLE=portfolio.services.get_crm_data`; they were separate
from the 138 pytest tests. They do not constitute a production-server or browser
test. Existing demo services and generated fixture contents were left untouched.

## Reproduction

From the repository root, start a **dedicated test mock** in another terminal.
Choose a free port; the following example uses 4402:

```powershell
node backend/mock-crm.mjs --port=4402 --host=127.0.0.1
```

From `backend/solution`, using the intended Python environment:

```powershell
python -m pip install -r requirements-dev.txt
$env:DJANGO_SECRET_KEY = 'pytest-local-test-key'
$env:CRM_BASE_URL = 'http://127.0.0.1:4402'
$env:DJANGO_ALLOWED_HOSTS = 'testserver,localhost,127.0.0.1'
$env:DJANGO_DEBUG = 'False'
$env:GET_CRM_DATA_CALLABLE = ''
python -m pytest -q
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pip check
```

For Task 3 and shared tests alone, use
`python -m pytest portfolio/test_performance.py portfolio/test_shared.py -v`.
These tests use temporary JSON and a fixed date; they need no CRM, generated
history, or database. The complete suite auto-skips its CRM integration tests
if the dedicated mock is unavailable; check that the full run reports no skips.
Those integration tests change the mock's global mode, so do not point them at
a shared demonstration service. Stop the dedicated mock after testing.

From the repository root, run the supporting fixture/mock regression with
`node --test support/mocks.test.mjs`.

## Limitations and assessment

- History is read-only synthetic JSON generated separately by the supplied
  script. There is no price feed, daily snapshot writer, database persistence,
  or invented data for missing days. Data eventually becomes stale unless
  regenerated; an empty current-day response can be correct.
- The local portfolio registry remains the default. The integrated Task 1
  helper is opt-in and checks identity; it does not supply daily snapshots.
  The adapter expects the exact canonical portfolio ID, such as `P-9001`.
- Decimal values serialize as JSON numbers and therefore have the usual
  floating-point precision limits at the output/consumer boundary.
- Authentication, currency conversion, caching, and transaction replay belong
  to other tasks. Load capacity, production deployment, and line/branch test
  coverage percentages were not measured.
- Node.js 22.19.0 passed the supporting tests locally. The repository recommends
  Node.js 24; that runtime was not tested in this evaluation.
- The backend workflow remains ignored and untracked. These are local test
  results, not a claim of GitHub Actions success.

All Task 3 definition-of-done items have direct passing test evidence. The
shared view and URL conflict resolution retains the teammate's CRM endpoint,
the holdings endpoint, and the history endpoint without moving calculations
into the views.
