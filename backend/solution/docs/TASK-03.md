# Task 3: Performance history

Branch: `EM-XW-004-T03`.

## Endpoint

```http
GET /portfolios/P-9001/performance-history?range=1M
```

The response is an array of `{ "date": "YYYY-MM-DD", "marketValue": number }`
objects, sorted by date in ascending order. The optional `range` defaults to
`All`. Range values are case-sensitive; an empty or unknown value returns HTTP
400 with `{ "error": "invalid_range", "message": "..." }`.

| Range | Inclusive start | Inclusive end |
| --- | --- | --- |
| `1D` | Today | Today |
| `1M` | One calendar month before today | Today |
| `YTD` | January 1 of the current year | Today |
| `1Y` | One calendar year before today | Today |
| `All` | Earliest available snapshot | Today |

Today is evaluated in UTC on every request. Month/year subtraction clamps an
invalid day to the target month's last day: March 31, 2026 starts a `1M` window
on February 28, 2026, and February 29, 2024 starts a `1Y` window on February 28,
2023. Ranges are anchored to the actual current date, not the latest snapshot.
Future snapshots are excluded for every range, including `All`.

Short histories, gaps, and explicit empty arrays are returned as stored without
padding or generating data. A stale history can therefore return an empty `1D`
or `YTD` response.

## Storage and Task 1 integration

Daily snapshots are read from the repository's generated
`backend/fixtures/performance-history.json`. The file maps portfolio IDs to arrays
of snapshots. JSON keeps this read-only exercise reproducible without database
migrations. Run the existing sample-data generator explicitly from the repository
root before starting the app:

```sh
node backend/fixtures/generate-history.mjs
```

The generator writes synthetic example data ending on the date it runs; the
result is gitignored. It is never run during requests. Regenerating replaces the
sample history file. `PORTFOLIO_HISTORY_PATH` can override the path in Django
settings for integration or tests. File changes are visible on the next request.

Portfolio existence is resolved through the shared `require_portfolio` adapter.
Until the teammate's Task 1 integration is available, the local seed portfolio
registry is the default provider. Set `GET_CRM_DATA_CALLABLE` to the dotted import
path of `get_crm_data(portfolio_id)` to use Task 1's mapped output; the adapter
checks its `portfolioId`. Its structured `ApiError` errors propagate, including
unknown IDs and unavailable CRM data. Task 3 does not implement the CRM fetcher
or Task 1's endpoint.

An unknown portfolio returns a structured HTTP 404. A missing/unreadable history
file, malformed JSON, absent history entry for a known portfolio, or invalid
snapshot data returns a structured HTTP 503. A known portfolio with no history
must have an explicit `[]` entry. Dates must be valid canonical `YYYY-MM-DD`
strings and unique per portfolio. Market values must be finite JSON numbers;
booleans, numeric strings, and values too large to emit as a finite JSON number
are rejected. Zero and negative market values are permitted. Values are parsed
as `Decimal` and serialized as JSON numbers; output has the normal precision
limitations of a JSON consumer's number type. Extra stored fields are omitted
from the response. No currency conversion is performed (Task 7 is separate).

## Code and validation

- `portfolio/performance.py`: pure validation, calendar boundaries, and filtering;
  imports no Django, HTTP, or storage modules and never mutates the input.
- `portfolio/performance_service.py`: one main orchestration function, with a
  per-request UTC date helper.
- `portfolio/performance_views.py`: query parsing and JSON response only.
- `portfolio/performance_urls.py`: the task's route, included by the app URLconf.
- `portfolio/test_performance.py`: deterministic pure-unit and Django HTTP tests.

From `backend/solution`, with the required environment variables configured:

```sh
python manage.py check
python manage.py test portfolio.test_performance
python -m unittest portfolio.test_performance.PerformanceFilteringTests
```

The tests fix today's date and use temporary JSON files; they need no network,
mock CRM process, generated fixture file, or database. Coverage includes all five
ranges and inclusive boundaries, leap days, month/year transitions, January 1,
short and stale histories, gaps, future exclusion, empty arrays, sorting, input
immutability, invalid dates/numbers, duplicate dates, JSON response schema,
invalid ranges, unknown IDs, missing/malformed files, updated-file visibility,
per-request date refresh, metadata-provider errors, HEAD, and HTTP method errors.

For a manual smoke test after fixture generation and app startup:

```sh
curl "http://127.0.0.1:3000/portfolios/P-9001/performance-history?range=1D"
curl "http://127.0.0.1:3000/portfolios/P-9002/performance-history?range=1Y"
curl "http://127.0.0.1:3000/portfolios/P-EMPTY/performance-history"
curl -i "http://127.0.0.1:3000/portfolios/P-9001/performance-history?range=bad"
curl -i "http://127.0.0.1:3000/portfolios/UNKNOWN/performance-history"
```

The second call demonstrates a short history (60 generated daily snapshots)
returned for a one-year request without padding. Auth, currency conversion,
database writes, and caching are outside Task 3's scope.
