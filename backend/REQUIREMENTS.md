# Backend Tasks: Wealth Management Portfolio Dashboard

You are building the backend for a wealth management portfolio dashboard, from scratch. You may use any language/framework and any AI assistance. Persisting data in-memory, in a local file, or in a lightweight database (e.g. SQLite) is acceptable — document your choice and any assumptions.

Assume the platform's native/base currency is **CAD** unless otherwise specified.

A mock CRM service is provided separately for Task 1 — see that task for its response shape and known quirks.

---

## 1. Portfolio Metadata via CRM Integration

**Goal:** Fetch portfolio metadata from the provided mock CRM (not your own database), map its awkward external schema into your clean internal schema, and expose it through your own endpoint — while handling the CRM's occasional failures gracefully.

**Route:** `GET /portfolios/:id`

**Inputs (path params):**

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Portfolio identifier |

**Provided CRM response shape (example — not your schema, do not copy directly):**
```json
{
  "client_record": {
    "client_id": "abc123",
    "full_name": "Jane Doe",
    "accounts": [
      {
        "acct_ref": "P-9001",
        "acct_nickname": "Taxable Brokerage",
        "curr_val": { "amt": 482350.12, "ccy": "CAD" },
        "chg_1d": { "amt": 1520.44, "pct": 0.0032 },
        "since_inception_pct": 0.187
      }
    ]
  },
  "meta": { "retrieved_at": "2025-06-01T10:00:00Z", "source": "legacy-crm-v2" }
}
```
The CRM is known to nest fields inconsistently, use abbreviated/legacy naming, and **intermittently return a timeout or 5xx error** (simulate this in the provided mock — expect it roughly 1 in 5 calls unless configured otherwise).

**Output Schema (your endpoint, after mapping):**

| Field | Type | Description |
|---|---|---|
| `portfolioId` | `string` | Mapped from `acct_ref` |
| `clientId` | `string` | Mapped from `client_id` |
| `label` | `string` | Mapped from `acct_nickname` |
| `currency` | `string` | Mapped from `curr_val.ccy` |
| `totalMarketValue` | `number` | Mapped from `curr_val.amt` |
| `dayChangeAmount` | `number` | Mapped from `chg_1d.amt` |
| `dayChangePercent` | `number` | Mapped from `chg_1d.pct` |
| `totalReturnSinceInception` | `number` | Mapped from `since_inception_pct` |
| `asOf` | `string` (ISO 8601 datetime) | Mapped from `meta.retrieved_at` |

**Expected Behaviour:**
- Calls the mock CRM, maps its response into the clean output schema above.
- Handles CRM timeouts/errors without crashing or hanging the request indefinitely (e.g. a reasonable timeout + defined fallback behavior — see Task 9 for caching-based fallback).

**Edge Cases / Constraints:**
- CRM returns an error/timeout → endpoint should still respond sensibly (a clear error, or a stale-cache fallback per Task 9) rather than hanging or crashing.
- Unknown `id` (CRM has no matching account) → 404 with a structured error.
- CRM field values that are missing/null should not silently break the mapping — handle explicitly.

**Definition of Done:**
- Endpoint correctly maps a successful CRM response into your schema.
- Verified behavior when the CRM call fails/times out (no crash, no indefinite hang).
- Returns 404 when the CRM has no matching account.

---

## 2. Holdings Endpoint (metadata, valuation, and gain/loss)

**Goal:** Provide the full list of positions within a portfolio, including all calculated fields — market value, weight %, and gain/loss — computed server-side.

**Route:** `GET /portfolios/:id/holdings`

**Inputs (path params):**

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Portfolio identifier |

**Output Schema:** Array of holding objects:

| Field | Type | Description |
|---|---|---|
| `ticker` | `string` | Security ticker symbol |
| `name` | `string` | Security display name |
| `assetClass` | `string` | e.g. `"Equity"`, `"Fixed Income"`, `"Cash"`, `"Alternatives"` |
| `quantity` | `number` | Shares/units held |
| `costBasisPerShare` | `number` | Average cost per share/unit |
| `price` | `number` | Current price per share/unit |
| `previousClosePrice` | `number` | Price at prior day's close (used for day-change calc) |
| `marketValue` | `number` | `quantity × price` |
| `weightPercent` | `number` | `marketValue / portfolioTotalMarketValue` (decimal) |
| `unrealizedGainLoss` | `number` | `(price - costBasisPerShare) × quantity` |
| `dayChangeAmount` | `number` | `(price - previousClosePrice) × quantity` |
| `dayChangePercent` | `number` | `(price - previousClosePrice) / previousClosePrice` (decimal) |

**Expected Behaviour:**
- Returns an array of all holdings for the given portfolio, with every calculated field computed server-side (not stored as static values).
- Weight % is computed relative to the portfolio's total market value at request time.

**Edge Cases / Constraints:**
- A portfolio with no holdings returns an empty array (`[]`), not an error.
- `quantity: 0` should produce `0` for `marketValue`, `weightPercent`, and both gain/loss fields — not an error.
- `previousClosePrice: 0` should not cause a divide-by-zero on `dayChangePercent` — return `0` or `null` in that case (document your choice).
- Weight percentages across all holdings won't necessarily sum to exactly 100% due to rounding — this is expected, don't "correct" it.
- Unknown `id` returns 404.

**Definition of Done:**
- Endpoint returns correct holding data (including all calculated fields) for a valid portfolio ID.
- Verified with an empty-holdings portfolio, a zero-quantity holding, and a zero-previous-close case.
- Covered by unit tests for the calculation logic independent of the HTTP layer.

---

## 3. Performance History Endpoint

**Goal:** Provide historical total market value data for the performance line chart.

**Route:** `GET /portfolios/:id/performance-history`

**Inputs (path params + query params):**

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Portfolio identifier (path param) |
| `range` | `string` (query, optional) | One of `"1D"`, `"1M"`, `"YTD"`, `"1Y"`, `"All"`. Defaults to `"All"` if omitted |

**Output Schema:** Array of daily snapshots:

| Field | Type | Description |
|---|---|---|
| `date` | `string` (ISO 8601 date, `YYYY-MM-DD`) | Snapshot date |
| `marketValue` | `number` | Total portfolio market value on that date |

**Expected Behaviour:**
- Returns daily snapshots filtered to the requested `range`.
- `"YTD"` filters from January 1 of the current year, not from the earliest available data.

**Edge Cases / Constraints:**
- If less history exists than the requested range covers, return whatever is available rather than erroring or padding with fake data.
- Unknown/invalid `range` value should return a 400 with a structured error rather than silently defaulting.
- Unknown `id` returns 404.

**Definition of Done:**
- Endpoint returns correctly filtered data for each valid `range` value.
- Verified with a portfolio that has less history than one of the ranges (e.g. only 3 months of data with `range=1Y` requested).
- Verified that an invalid `range` value returns a 400.

---

## 4. Auth Middleware

**Goal:** Gate access to portfolio endpoints behind a basic authentication check.

**Inputs (request header):**

| Field | Type | Description |
|---|---|---|
| `Authorization` | `string` (header) | e.g. `"Bearer <token>"` or a mock API key |

**Output Schema (on failure):**

| Field | Type | Description |
|---|---|---|
| `error` | `string` | Short error code, e.g. `"unauthorized"` |
| `message` | `string` | Human-readable explanation |

**Expected Behaviour:**
- Requests without a valid `Authorization` header are rejected before reaching route logic.
- Requests with a valid token/key proceed normally to the intended endpoint.
- A mock/hardcoded valid token is acceptable — this doesn't need real user management.

**Edge Cases / Constraints:**
- Missing header → `401` with the error schema above.
- Malformed header (e.g. missing `"Bearer "` prefix) → `401`, not a crash/500.
- Valid header → request proceeds, no error response.

**Definition of Done:**
- Middleware correctly blocks requests missing/with invalid auth (`401`).
- Middleware correctly allows requests with valid auth through to the endpoint.
- Verified against at least one malformed-header case.

---

## 5. Asset Allocation Endpoint

**Goal:** Provide a breakdown of portfolio value by asset class for the allocation chart.

**Route:** `GET /portfolios/:id/allocation`

**Inputs (path params):**

| Field | Type | Description |
|---|---|---|
| `id` | `string` | Portfolio identifier |

**Output Schema:** Array of allocation entries:

| Field | Type | Description |
|---|---|---|
| `assetClass` | `string` | e.g. `"Equity"`, `"Fixed Income"`, `"Cash"`, `"Alternatives"` |
| `value` | `number` | Total market value held in that asset class |
| `percent` | `number` | `value / totalPortfolioMarketValue` (decimal) |

**Expected Behaviour:**
- Aggregates holdings by `assetClass` and returns one entry per class present in the portfolio.
- `percent` values are computed relative to the portfolio's total market value.

**Edge Cases / Constraints:**
- A portfolio concentrated 100% in one asset class should return a single entry with `percent: 1.0`, not error or omit missing classes.
- A portfolio with no holdings returns an empty array.

**Definition of Done:**
- Endpoint correctly aggregates and returns allocation data for a multi-asset-class portfolio.
- Verified with a single-asset-class portfolio and an empty-holdings portfolio.

---

## 6. Multi-Portfolio & Household View

**Goal:** Support clients with multiple portfolios and provide an aggregated view across them.

**Routes:**
- `GET /clients/:clientId/portfolios` — list of portfolios belonging to a client
- `GET /clients/:clientId/household-summary` — aggregated totals across all of the client's portfolios

**Inputs (path params):**

| Field | Type | Description |
|---|---|---|
| `clientId` | `string` | Client identifier |

**Output Schema — `/clients/:clientId/portfolios`:** Array of:

| Field | Type | Description |
|---|---|---|
| `portfolioId` | `string` | Portfolio identifier |
| `label` | `string` | Display name (e.g. `"Traditional IRA"`) |
| `totalMarketValue` | `number` | That portfolio's total market value |

**Output Schema — `/clients/:clientId/household-summary`:**

| Field | Type | Description |
|---|---|---|
| `clientId` | `string` | Client identifier |
| `totalMarketValue` | `number` | Sum of `totalMarketValue` across all the client's portfolios |
| `portfolioCount` | `number` | Number of portfolios included in the aggregate |
| `dayChangeAmount` | `number` | Sum of day change across all portfolios |
| `dayChangePercent` | `number` | Household-level day change as a decimal, weighted by portfolio value |

**Expected Behaviour:**
- Correctly lists all portfolios for a client.
- Correctly aggregates totals across portfolios for the household summary, with `dayChangePercent` weighted (not a naive average of each portfolio's %).

**Edge Cases / Constraints:**
- A client with only one portfolio should still return valid data from both endpoints (trivial aggregation).
- Unknown `clientId` returns 404.

**Definition of Done:**
- Both endpoints return correct data for a client with 2+ portfolios.
- Verified with a single-portfolio client.
- Verified that `dayChangePercent` is value-weighted, not a simple average, with a test case where portfolios have different sizes and different day-change percentages.

---

## 7. Currency Display Support (`?currency=CAD|USD`)

**Goal:** Let clients request portfolio, holdings, and performance data converted to a display currency, without needing a separate public conversion endpoint.

**Applies to:** `GET /portfolios/:id`, `GET /portfolios/:id/holdings`, `GET /portfolios/:id/performance-history`

**Inputs (query param, added to the above endpoints):**

| Field | Type | Description |
|---|---|---|
| `currency` | `string` (query, optional) | `"CAD"` or `"USD"`. Defaults to the portfolio's native currency (`"CAD"`) if omitted |

**Output Schema (additions to existing responses):**

| Field | Type | Description |
|---|---|---|
| `currency` | `string` | Currency the monetary values in this response are expressed in |
| `exchangeRate` | `number` | Rate used to convert from native currency to the requested currency (included for transparency/debugging) |

All existing monetary fields (`totalMarketValue`, `marketValue`, `price`, `unrealizedGainLoss`, etc.) are converted using this rate before being returned; non-monetary fields (`quantity`, `weightPercent`, `dayChangePercent`, etc.) are unaffected.

**Expected Behaviour:**
- Requesting `?currency=USD` returns all monetary fields converted, with `currency: "USD"` in the response.
- Omitting the param (or `?currency=CAD`) returns native, unconverted values.
- Conversion logic (rate lookup/cache) is internal — it does not need to be its own public endpoint.

**Edge Cases / Constraints:**
- An unsupported currency value (e.g. `?currency=EUR`) should return a 400 with a structured error, not silently fall back.
- Conversion must be applied consistently across all three endpoints — a client switching currency should get consistent totals whether it re-fetches the portfolio endpoint or the holdings endpoint.
- Rounding after conversion should be handled carefully so converted totals stay internally consistent (e.g. summed holdings ≈ portfolio total).

**Definition of Done:**
- All three endpoints correctly return converted values when `?currency=USD` is passed.
- Verified that omitting the param returns native CAD values.
- Verified that an invalid currency value returns a 400.

---

## 8. Holding Detail Endpoint

**Goal:** Provide extended, non-tabular data for a single holding to support the Detailed Holding View — information not already returned by the Holdings Endpoint (Task 2).

**Route:** `GET /holdings/:ticker/detail`

**Inputs (path params):**

| Field | Type | Description |
|---|---|---|
| `ticker` | `string` | Security ticker symbol |

**Output Schema:**

| Field | Type | Description |
|---|---|---|
| `ticker` | `string` | Security ticker symbol |
| `name` | `string` | Security display name |
| `sector` | `string` | e.g. `"Technology"` |
| `assetClass` | `string` | e.g. `"Equity"` |
| `purchaseDate` | `string` (ISO 8601 date) | Date the position was originally opened |
| `dividendYield` | `number \| null` | Decimal (e.g. `0.005` = 0.5%); `null` if the security pays no dividend |
| `fiftyTwoWeekLow` | `number` | Lowest price over the trailing 52 weeks |
| `fiftyTwoWeekHigh` | `number` | Highest price over the trailing 52 weeks |
| `priceHistory` | `array` | Array of `{ date: string, price: number }` objects |

**Expected Behaviour:**
- Returns the extended detail object for a given ticker, with fields the Holdings Endpoint does not already provide.
- `priceHistory` is returned as a chronologically ordered array.

**Edge Cases / Constraints:**
- Unknown `ticker` returns 404.
- A holding with no dividend returns `dividendYield: null` rather than `0` or omitting the field, so clients can distinguish "no dividend" from "0% dividend."
- A ticker with no available price history returns an empty array for `priceHistory`, not an error.

**Definition of Done:**
- Endpoint returns correct extended data for a known ticker.
- Verified with a non-dividend-paying holding (`dividendYield: null`).
- Verified with a ticker that has no price history (`priceHistory: []`).
- Returns 404 for an unknown ticker.

---

## 9. Caching Layer for CRM/Metadata Responses

**Goal:** Reduce load on the (slow/unreliable) mock CRM and make Task 1's endpoint resilient to CRM failures, by caching successful responses and falling back to stale cached data when the CRM is unavailable.

**Input Schema (internal cache interface — not a public endpoint):**

| Field | Type | Description |
|---|---|---|
| `key` | `string` | Cache key, e.g. portfolio `id` |
| `value` | `object` | The mapped portfolio metadata object (Task 1's output schema) |
| `ttlSeconds` | `number` | How long a cached entry is considered fresh |

**Output Schema (Task 1's endpoint, extended):**

| Field | Type | Description |
|---|---|---|
| `...` | | All fields from Task 1's output schema |
| `stale` | `boolean` | `true` if this response was served from cache past its TTL due to a CRM failure; `false` otherwise |
| `cachedAt` | `string` (ISO 8601 datetime) | When this cached value was originally fetched from the CRM |

**Expected Behaviour:**
- On a successful CRM call, the response is cached with a defined TTL (a short TTL like 30–60s is reasonable for this exercise).
- Within the TTL, repeated requests are served from cache without re-calling the CRM.
- If the TTL has expired and the CRM call fails/times out, the endpoint falls back to the last cached value with `stale: true` rather than failing the request.
- If there is no cached value at all and the CRM fails, the endpoint returns an appropriate error (nothing to fall back to).

**Edge Cases / Constraints:**
- First-ever request for a portfolio (cold cache) with a CRM failure has no fallback available — handle this distinctly from the "stale fallback available" case.
- Cache should be scoped per portfolio `id` — one portfolio's cached data should never be served for a different `id`.
- Clarify (and document) whether a successful CRM response after a stale period replaces the cache and resets `stale` to `false`.

**Definition of Done:**
- Verified that a repeated request within the TTL does not re-call the CRM (e.g. via a call counter/log in your mock).
- Verified that a simulated CRM failure after TTL expiry returns cached data with `stale: true`.
- Verified that a cold-cache + CRM-failure scenario returns a clear error rather than a crash.

---

## 10. Data Model & Ledger Replay

**Goal:** Design a normalized schema for the core entities, and implement logic that computes a holding's current quantity and cost basis by replaying its transaction history — rather than storing/mutating a running total directly.

**Schema Design (deliverable — an ERD or equivalent table definitions):**

Suggested entities and key fields (adapt as you see fit, document your reasoning):

| Table | Key Fields | Type |
|---|---|---|
| `clients` | `client_id` (PK), `name` | `string`, `string` |
| `portfolios` | `portfolio_id` (PK), `client_id` (FK), `label`, `currency` | `string`, `string`, `string`, `string` |
| `holdings` | `holding_id` (PK), `portfolio_id` (FK), `ticker` | `string`, `string`, `string` |
| `transactions` | `transaction_id` (PK), `holding_id` (FK), `type`, `quantity`, `price`, `date` | `string`, `string`, ``"BUY"\|"SELL"``, `number`, `number`, `string` (ISO date) |

**Input Schema (for the replay function):**

| Field | Type | Description |
|---|---|---|
| `transactions` | `array` | Array of `{ type: "BUY"\|"SELL", quantity: number, price: number, date: string }`, chronologically ordered |

**Output Schema (for the replay function):**

| Field | Type | Description |
|---|---|---|
| `currentQuantity` | `number` | Net shares held after replaying all transactions |
| `averageCostBasisPerShare` | `number` | Weighted average cost of currently-held shares |

**Expected Behaviour:**
- `currentQuantity` and `averageCostBasisPerShare` are derived entirely from the transaction list — never stored/updated as standalone mutable fields.
- BUY transactions increase quantity and are factored into the weighted average cost; SELL transactions decrease quantity without changing the average cost basis of remaining shares (standard average-cost accounting).

**Edge Cases / Constraints:**
- A SELL that reduces quantity to exactly 0 should result in `currentQuantity: 0` (and you should decide/document what `averageCostBasisPerShare` means at that point, e.g. `0` or `null`).
- A SELL for more shares than currently held is invalid input — decide and document how you handle it (reject/error vs. allow negative position), rather than silently producing a nonsensical result.
- Transactions provided out of chronological order should not be assumed pre-sorted — sort by `date` before replaying, or document that the caller must guarantee order.

**Definition of Done:**
- Schema (ERD or table definitions) is documented, showing relationships between clients, portfolios, holdings, and transactions.
- Replay function correctly computes quantity and average cost basis for a multi-transaction history (multiple buys at different prices, at least one partial sell).
- Verified against the zero-quantity-after-sell edge case and the oversell edge case (your documented handling, at minimum not silently wrong).
