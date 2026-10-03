# Task 3 validation record

Validated locally on October 3, 2026 using Python 3.14.8 and Django 5.2.17.

| Check | Result |
| --- | --- |
| Full Django suite | 46 passed: 18 filtering, 17 history HTTP, 11 shared |
| Standalone filtering suite without Django settings | 18 passed |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Installed dependency compatibility | Passed |
| Real Django server requests over a local TCP socket | 13 passed |
| Supplied mock regression suite | 5 passed on Node.js 22.19.0 |
| Git whitespace validation | Passed |

The live HTTP checks used the supplied history generator and covered the default
401-point history, all five explicit ranges, a 60-point short history requested
as 1Y, empty history, invalid range (400), unknown portfolio (404), HEAD,
unsupported POST (405), and an unknown route (JSON 404). The temporary development
server was stopped after verification. Deterministic tests additionally cover
month ends, leap years, YTD, stale data, future dates, gaps, malformed files,
per-request clock evaluation, and exact output schemas.

Reproduce the automated checks using the commands in `../README.md` and
`TASK-03.md`. Generate sample history before manual server checks. The GitHub
Actions workflow repeats the automated suite with Python 3.14 and the
repository's requested Node.js 24 runtime.

The teammate's actual `get_crm_data` function was not available. Its documented
Task 1 dictionary and error contract are covered with test substitutes, and the
live local requests used seed portfolio IDs. Live CRM integration is pending
the teammate's module path and implementation. Tasks 1 and 4-10 are not claimed
as completed by this branch. No changes were merged to `main`.
