# Portfolio mock API (frontend and mobile)

Use `http://localhost:4000` for frontend or `http://localhost:4001` for mobile on your computer. See the [mobile setup guide](../mobile/START-HERE.md) for device addresses. Both services return the same fictional data. They run independently and need no authentication.

## Routes

| GET route | Returns |
| --- | --- |
| `/health` | `{ "status": "ok", "service": "..." }` |
| `/accounts` | Array of `{ accountId, label, totalMarketValue }` |
| `/portfolios/P-9001` | Portfolio data object described below |
| `/portfolios/P-9002` | A second, smaller portfolio |
| `/holdings/AAPL/detail` | Holding detail with purchase date, cost basis, sector, dividend yield, 52-week low/high, and `priceHistory` |
| `/exchange-rate` | `{ "CADtoUSD": 0.73 }` (fixed fictional rate) |
| `/notification` | Example notification payload; no notification is sent |
| `/scenarios` | Available scenarios and routes |

An account ID and portfolio ID identify the same account: pass the selected `accountId` to `/portfolios/:id`. Unknown routes and IDs return HTTP 404 with `{ error, message }`. Invalid scenarios/delays return 400. Data responses are not cached by the mock.

## Portfolio response

```js
{
  asOf: "...",                 // Time this response was made, in UTC
  portfolio: {
    portfolioId: "P-9001",
    accountId: "P-9001",
    clientId: "abc123",
    label: "Taxable Brokerage",
    currency: "CAD",
    totalMarketValue: 65680,
    dayChangeAmount: 397.25,
    dayChangePercent: 0.61,
    totalReturnSinceInception: 0.187
  },
  holdings: [/* ticker, name, quantity, price, marketValue,
               weightPercent, gainLoss, dayChangeAmount,
               dayChangePercent, assetClass, sector, costBasisPerShare */],
  allocation: [/* { assetClass, value } */],
  performanceHistory: [/* { date: "YYYY-MM-DD", marketValue } */]
}
```

The comments above describe the shape; fetch the endpoint for valid JSON. Use `portfolio` for your summary, `holdings` for your table/list, `allocation` for the allocation chart, and `performanceHistory` for the value chart.

All monetary fields, including holding details and price history, are CAD. Apply the exchange rate in your frontend for the currency task. This mock does not perform date-range filtering or currency conversion. The backend track has its own, different endpoint contract.

### Percentage units

The frontend/mobile examples mix percentage units. These mocks follow those examples:

| Field | Value meaning |
| --- | --- |
| `dayChangePercent` (summary or holding) | `2.4` means **2.4%** |
| `weightPercent` | `5.66` means **5.66%** |
| `totalReturnSinceInception` | `0.187` means **18.7%** |
| `dividendYield` | `0.005` means **0.5%**; `null` means no dividend |

`gainLoss` is a money amount. Allocation entries contain values, not percentages. Do not reuse the backend track's decimal-percentage convention here.

### Holding details and dates

Fetch `/holdings/:ticker/detail` for any ticker in the selected dataset. `TSLA` has no dividend; `CASH` has no dividend or price history. The large dataset uses `DEMO01` through `DEMO60`, all with detail responses and no dividend.

History ends on the current UTC date and normally covers 401 daily points. This keeps YTD and recent ranges usable. Prices and histories are fictional; `asOf` advances on refresh, but prices stay the same within a scenario. The second portfolio has different holdings and values. Detail responses contain security information; use the selected portfolio's holding row for account-specific quantity, weight, and gain/loss.

## Test datasets

Add `?scenario=NAME` to an endpoint. Apply the **same scenario** to account, portfolio, and detail requests so the data stays consistent. Remove it for the normal dataset.

Example: `http://localhost:4000/portfolios/P-9001?scenario=large`

| Scenario | What to check |
| --- | --- |
| `default` | Two accounts; first has five holdings across four asset classes |
| `empty` | No holdings; zero-value summary |
| `large` | 60 holdings and working details for each |
| `zero` | Neutral day change and total return |
| `negative` | Negative day changes and total return |
| `large-value` | Very large values remain readable |
| `single-account` | Only `P-9001` is available |
| `single-class` | Equity only |
| `tiny-allocation` | Equity below 1% |
| `few-holdings` | Two holdings, fewer than three movers |
| `all-gainers` / `all-losers` | No entries for the opposite direction |
| `one-point` / `two-points` | Short chart histories |
| `gaps` | Missing dates in history |
| `short-history` | Only the last 60 days |

Add `delayMs=2000` for a loading state or `fail=true` for an HTTP 503 error. Combine parameters with `&`, for example `/portfolios/P-9001?scenario=large&delayMs=2000`. Delays can be 0–10000 milliseconds. Remove `fail=true` to recover. To test an actual network failure, stop the mock and restart it.
