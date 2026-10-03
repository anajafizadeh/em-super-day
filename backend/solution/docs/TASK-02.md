# Task 2: Holdings

`GET /portfolios/{portfolioId}/holdings` returns an array of the twelve fields in
the Task 2 specification. `HEAD` is also supported. Other methods return HTTP 405
with `{ "error": "method_not_allowed", "message": "..." }`.

## Design and data

- `portfolio/holdings_views.py` is the thin HTTP adapter.
- `portfolio/holdings_service.py:get_holdings` checks portfolio existence through
  the shared metadata adapter, reads the seed file, selects the requested
  portfolio's records, and invokes the calculation function.
- `portfolio/holdings.py:calculate_holdings` has no Django, HTTP, or storage
  dependencies. It validates its input and returns new dictionaries without
  mutating the source.
- Positions are persisted in `backend/fixtures/seed.json`. A
  `PORTFOLIO_SEED_PATH` Django setting can override this path. No database or
  migrations are needed for this endpoint.

The metadata adapter accepts the teammate's Task 1 `get_crm_data` output.
Portfolio identity is established before holdings are loaded. Task 1's CRM total
is intentionally not the weight denominator: this endpoint sums current holding
values on every request, as agreed. See the solution README for how to configure
the metadata provider and run with the local fixture adapter before Task 1 arrives.

## Calculations and edge cases

All numeric inputs are converted to `Decimal`; JSON file fractions are loaded as
`Decimal` directly. Calculations use 28 significant digits and are serialized as
JSON numbers. No monetary rounding or forced adjustment of weights is applied.
JSON clients using binary floating point can observe normal representation limits.
Ratios are decimals (`0.2` means 20%).

| Output | Calculation |
| --- | --- |
| `marketValue` | `quantity * price` |
| `weightPercent` | `marketValue / sum(current portfolio market values)` |
| `unrealizedGainLoss` | `(price - costBasisPerShare) * quantity` |
| `dayChangeAmount` | `(price - previousClosePrice) * quantity` |
| `dayChangePercent` | `(price - previousClosePrice) / previousClosePrice` |

Zero portfolio total produces zero weights; zero previous close produces a zero
day-change ratio. A zero-quantity position has zero market value, weight, unrealized
gain/loss, and day-change amount. Its security price-change ratio still follows the
specified formula: the seed's `ZERO` position returns `dayChangePercent: 0.2`.
Fractional and finite negative numeric values follow the supplied formulas.

Required metadata must be nonempty strings. Required numeric values must be
finite JSON numbers; booleans, strings, missing/null values, and nonfinite numbers
are rejected. Invalid source data produces HTTP 503 with `data_unavailable`,
rather than a misleading partial valuation. Every source row must identify its
portfolio; only selected rows require complete valuation fields. Stored derived
fields, if present, are ignored and recomputed. A known portfolio with no positions
returns `[]`; an unknown portfolio returns a structured 404. Metadata provider
errors retain their structured status/code.

## Validation

From `backend/solution`, with dependencies installed:

```sh
python -m unittest portfolio.test_holdings.HoldingsCalculationTests -v
python manage.py test portfolio.test_holdings -v 2
python manage.py check
```

The first command needs no Django settings or environment variables. The Django
commands need the required environment configuration from `.env.example`.

Tests verify supplied seed results, decimal fractions, losses, zero quantity,
zero previous close, zero totals, empty and single-position portfolios, portfolio
isolation, price changes on subsequent requests, source immutability, malformed
input and files, JSON numeric types and exact field set, unknown IDs, metadata
failures, HEAD, and JSON 405 responses with CSRF enforcement enabled. HTTP tests
stub Task 1 metadata so they do not depend on CRM availability.

Seed reference values for `P-9001`: total market value `48930`, AAPL market value
`27300`, BND market value `21630`, unrealized gains/losses `3300` and `-570`, and
day-change amounts `300` and `-270`. `P-EMPTY` returns `[]`; `P-9002` has one `NEW`
position with market value `500` and zero day-change percent.

This task does not implement authentication, currency conversion, transaction
replay, or the Task 1 CRM client.
