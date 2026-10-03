# Mock CRM guide

Base URL: `http://localhost:4002`. This service supplies Task 1's external CRM data. Your own backend exposes the routes in the requirements.

## Get portfolio metadata

`GET /crm/portfolios/P-9001`

The normal response matches Task 1's legacy shape: `client_record` contains `client_id`, `full_name`, and `accounts`; `meta` contains `retrieved_at` and `source`. Each account uses `acct_ref`, `acct_nickname`, `curr_val`, `chg_1d`, and `since_inception_pct`.

The response includes **all accounts for that client**. Find the requested account by `acct_ref`; do not assume it is the first one. Try `P-9002` to check this. Known IDs are `P-9001`, `P-9002`, `P-EMPTY`, and `P-SINGLE`. Unknown IDs return 404 on a successful CRM call. All amounts are CAD; percentages are decimals.

## Failures and edge cases

By default, every fifth CRM request fails: request 5 returns 503, request 10 waits 10 seconds then returns 504, and the pattern repeats. Health/stats/control calls do not count. Set a timeout in your own backend so it does not wait the full 10 seconds.

Add `?mode=...` to a CRM request to force one case:

| Mode | Response |
| --- | --- |
| `auto` | The default failure pattern |
| `ok` | Normal successful response |
| `error` | Immediate HTTP 503 |
| `timeout` | Wait 10 seconds, then HTTP 504 |
| `missing` | Requested account has `curr_val.amt: null` and no `acct_nickname` |
| `nested` | Accounts are under `client_record.relationships.accounts` instead of `client_record.accounts` |

For example, open <http://localhost:4002/crm/portfolios/P-9001?mode=missing>. The nested fixture is an explicit version of the inconsistent nesting mentioned in Task 1. The `ok` mode always uses the standard shape.

## Check your cache

To change the default for all calls from your backend, send:

```http
POST http://localhost:4002/__control
Content-Type: application/json

{ "mode": "ok" }
```

Use an HTTP client or the control requests in [requests.http](requests.http). In macOS/Linux Terminal you can also run:

```sh
curl -X POST http://localhost:4002/__control -H 'Content-Type: application/json' -d '{"mode":"ok"}'
```

1. Set mode to `ok`. Call **your backend** for `P-9001` twice within your cache TTL.
2. Open <http://localhost:4002/__stats>. The CRM count should have increased only once.
3. Change mode to `error`. Wait for your TTL to expire and call your backend again. It should serve the stale cached value as required in Task 9.
4. While still in `error` mode, request a portfolio your backend has never cached. Check its cold-cache error response.
5. Change mode back to `ok`. Request again after expiry and check your documented cache refresh behavior.

`GET /__stats` returns the mode, total `calls`, and `callsByPortfolio`. The terminal also logs each CRM call. Restarting the mock resets its counters and mode; it does not reset your backend's cache. A URL's `?mode=` overrides the global mode, so omit that query in your backend when testing global controls.

The CRM has no authentication. Your backend must implement its own authentication. The mock does not map, cache, convert currencies, or serve your required endpoints.
