# Task 2 validation record

Validated locally on October 3, 2026 using Python 3.14.8 and Django 5.2.17.

| Check | Result |
| --- | --- |
| Full Django suite | 36 passed: 13 calculation, 12 holdings HTTP, 11 shared |
| Standalone calculation suite without Django settings | 13 passed |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Installed dependency compatibility | Passed |
| Real Django server requests over a local TCP socket | 7 passed |
| Supplied mock regression suite | 5 passed on Node.js 22.19.0 |
| Git whitespace validation | Passed |

The live HTTP checks covered the successful P-9001 response and its independently
calculated values, empty holdings, zero previous close, unknown portfolio (404),
HEAD, unsupported POST (405), and an unknown route (JSON 404). The temporary
development server was stopped after verification. Unit/HTTP tests additionally
cover invalid data, zero quantities/totals, precision, updated prices, and errors.

Reproduce the automated checks using the commands in `../README.md` and
`TASK-02.md`, using Python 3.14 and the repository's requested Node.js 24 runtime.
The optional local workflow file is excluded from version control.

The teammate's actual `get_crm_data` function was not available. Its documented
Task 1 dictionary and error contract are covered with test substitutes, and the
live local requests used seed portfolio IDs. Live CRM integration is pending
the teammate's module path and implementation. Tasks 1 and 4-10 are not claimed
as completed by this branch. No changes were merged to `main`.
