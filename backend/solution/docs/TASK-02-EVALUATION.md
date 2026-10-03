# Task 2 Evaluation Report: Holdings Endpoint

**Result:** All 36 collected tests and all 98 subtests passed. The tested
standalone Task 2 implementation meets the holdings acceptance criteria covered
below. This result verifies local calculations, fixture access, and Django
request/response behavior; it does not establish live Task 1 CRM integration.

## Evaluation record

| Item | Verified value |
| --- | --- |
| Evaluation date | October 3, 2026 |
| Branch | `EM-XW-002-T02` |
| Application commit evaluated | `4916e48bd98e7f3b9259798995d46b83d8866df4` |
| Platform | Windows, Python 3.14.8 |
| Framework | Django 5.2.17 |
| Test tools | pytest 9.1.1, pytest-django 4.14.0 |
| Scope | Full Python suite discovered in this branch's `backend/solution/` |
| Collected tests | 36: 13 calculation, 12 holdings endpoint, 11 shared |
| Subtests | 98 passed within the collected test methods |
| Failures / errors / skipped tests | 0 / 0 / 0 |
| Recorded pytest duration | 0.22 seconds; local run only, not a performance benchmark |

Recorded pytest summary:

```text
collected 36 items
36 passed, 98 subtests passed in 0.22s
```

The 98 subtests are individual cases inside existing test methods, not an
additional 98 separately collected tests. pytest 9 executes and reports these
`unittest.subTest` cases. No test was excluded by a selection expression.

## Acceptance criteria and evidence

The requirements are defined in [backend/REQUIREMENTS.md, Task 2](../../REQUIREMENTS.md).
The tests reside in [test_holdings.py](../portfolio/test_holdings.py) and
[test_shared.py](../portfolio/test_shared.py).

| Requirement or boundary | Observed behavior | Test evidence | Result |
| --- | --- | --- | --- |
| Valid portfolio returns all required fields | `P-9001` returns AAPL, BND, and ZERO; each item has exactly the 12 specified fields and numeric JSON values | `test_success_has_exact_schema_json_numbers_and_correct_seed_values` | Pass |
| Derived values are computed on the server | Seed valuations match independent expected values; supplied stale derived fields are ignored | `test_supplied_seed_values_match_hand_calculations`, `test_derived_fields_are_recomputed_and_source_is_unchanged` | Pass |
| Weights use current total holdings value | Weights use the sum of current positions; changing one price changes both positions' weights on the next request | `test_updated_price_recomputes_values_and_all_weights`, `test_seed_file_is_read_again_and_derived_values_are_recalculated` | Pass |
| Known portfolio without holdings | Returns HTTP 200 and `[]` | `test_empty_portfolio_returns_200_empty_array` | Pass |
| Zero quantity | Market value, weight, unrealized gain/loss, and daily monetary change are zero; the security price-change ratio remains formula-based | `test_zero_quantity_has_zero_amounts_but_keeps_security_price_ratio` | Pass |
| Zero previous close | Daily change ratio returns `0`; the amount still follows its formula | `test_zero_previous_close_uses_zero_ratio_and_keeps_amount`, `test_other_portfolio_is_isolated_and_zero_previous_close_is_safe` | Pass |
| Zero portfolio value | Zero prices and offsetting positive/negative positions produce zero weights without division errors | `test_zero_prices_do_not_divide_by_zero_total`, `test_offsetting_positions_with_zero_total_have_zero_weights` | Pass |
| Unknown portfolio | Returns structured HTTP 404 before loading holdings | `test_unknown_portfolio_returns_structured_404_before_loading_holdings` | Pass |
| Portfolio isolation and single position | Only the requested portfolio's holdings are returned; one nonzero position has weight `1` | `test_other_portfolio_is_isolated_and_zero_previous_close_is_safe`, `test_single_position_has_full_weight` | Pass |
| Decimal calculations and source immutability | Fractional values retain the expected decimal result; calculation does not modify the source | `test_fractional_quantity_and_decimal_prices_remain_exact`, `test_derived_fields_are_recomputed_and_source_is_unchanged` | Pass |
| Invalid input and unavailable files | Missing, malformed, nonfinite, and out-of-range data produces explicit errors; endpoint failures use HTTP 503 | Numeric/metadata validation tests, `test_invalid_holdings_source_returns_structured_503`, `test_missing_and_malformed_json_files_return_structured_503`, `test_numbers_outside_json_encoder_range_return_structured_503` | Pass |
| HTTP method contract | HEAD returns an empty body; unsupported methods return structured HTTP 405 and `Allow: GET, HEAD`, including with CSRF enforcement | `test_head_returns_success_without_response_body`, `test_unsupported_methods_return_json_405_even_with_csrf_enforced` | Pass |
| Shared error and metadata adapter contract | Errors have `error` and `message`; mocked Task 1 output is accepted only for the requested identity; expected provider errors retain their status | `SharedResponseTests`, `FixtureTests`, `test_metadata_provider_failure_is_preserved` | Pass |

## Formula review and reference values

All calculations use `Decimal` with 28 significant digits internally. The JSON
encoder emits numbers. Ratios are decimal fractions: `0.2` represents 20%.
There is no forced correction that makes rounded weights sum to exactly one.

| Field | Formula |
| --- | --- |
| `marketValue` | `quantity * price` |
| `weightPercent` | `marketValue / sum(current portfolio holding market values)`; `0` if the total is zero |
| `unrealizedGainLoss` | `(price - costBasisPerShare) * quantity` |
| `dayChangeAmount` | `(price - previousClosePrice) * quantity` |
| `dayChangePercent` | `(price - previousClosePrice) / previousClosePrice`; `0` if the previous close is zero |

The agreed weight denominator is the current holdings total, not a potentially
different total supplied by portfolio metadata. The endpoint tests deliberately
substitute metadata with a different total to verify this rule.

| Supplied `P-9001` holding | Market value | Unrealized gain/loss | Daily amount change | Weight |
| --- | ---: | ---: | ---: | --- |
| AAPL | 27,300 | 3,300 | 300 | `27300 / 48930` |
| BND | 21,630 | -570 | -270 | `21630 / 48930` |
| ZERO | 0 | 0 | 0 | `0` |

The portfolio total is `48930`. ZERO retains `dayChangePercent = 0.2` because
this field measures security price movement, independently of held quantity.

## Structure and integration boundary

The call path is:

```text
URL -> portfolio.views.holdings
    -> holdings_service.get_holdings
    -> data.require_portfolio / data.load_seed
    -> holdings.calculate_holdings
    -> JSON response
```

The view delegates orchestration to the service. The calculation module has no
Django, HTTP, or storage imports. Shared response helpers preserve structured
errors and serialize Decimal values. The fixture loader reads the file on each
request, which is checked by changing a temporary fixture between requests.

This standalone branch uses local seed IDs when `GET_CRM_DATA_CALLABLE` is blank.
The adapter can call a configured synchronous `get_crm_data(portfolio_id)`
function returning the mapped Task 1 dictionary. These tests substitute that
function and its errors; they do not call the teammate's actual CRM client.

## Reproduce the evaluation

The following is the exact PowerShell invocation used for the recorded test run.
It needs no running Django server, CRM server, database migration, or generated
history fixture. Environment values apply to the test shell and its child
process, without changing configuration files or existing server processes.

```powershell
Set-Location 'C:\Users\wangx\Desktop\Electric Mind\EM-XW-002-T02\backend\solution'
$env:DJANGO_SECRET_KEY = 'pytest-local-evaluation-only'
$env:CRM_BASE_URL = 'http://127.0.0.1:4002'
$env:DJANGO_ALLOWED_HOSTS = 'testserver,localhost,127.0.0.1'
$env:DJANGO_DEBUG = 'False'
$env:GET_CRM_DATA_CALLABLE = ''
& 'C:\Users\wangx\Desktop\Electric Mind\.venv314\Scripts\python.exe' -m pytest --ds=config.settings -v
```

For another checkout, use its `backend/solution/` directory and a Python 3.14
virtual environment. Install the existing runtime requirements plus the test
tools before running the same pytest command:

```powershell
python -m pip install -r requirements.txt 'pytest==9.1.1' 'pytest-django==4.14.0'
python -m pytest --ds=config.settings -v
```

Set the environment variables shown above in that shell first. Run each task
branch in a separate Python process: the branches use the same package names.

## Separate integration regression

The integration owner also validated a combined working tree on
`EM-XW-004-T03`, based on Task 3 commit `2b596f3` and `main` commit `01430a2`,
on October 3, 2026. That tree includes the teammate's Task 1 implementation and
the shared modules after conflict resolution. This is separate evidence; those
Task 1 files are not present in the standalone Task 2 branch evaluated above.

| Combined-tree check | Reported result |
| --- | --- |
| Full pytest suite | 138 tests and 169 subtests passed in 5.33 seconds, no skipped tests |
| Test composition | 25 holdings, 35 performance, 11 shared, 67 Task 1 tests; Task 1 includes six tests against a real local mock CRM server |
| Integrated GET/HEAD checks | All three endpoint routes passed through `portfolio.services.get_crm_data`, with six requests reaching an isolated local mock CRM on port 54031 |
| HTTP error behavior | Twelve unsupported-method cases returned JSON 405; unknown route and unknown portfolio IDs returned JSON 404 |
| Data consistency | Holdings total was `48930`; 401 history entries were date-sorted, with latest value `48930` |
| Supplied Node mock regression suite | Five passed on Node.js 22.19.0; the repository recommends Node.js 24, so that requested runtime was not validated by this check |
| Django system and migration checks | No system-check issues and no migration changes |

The integrated route checks used Django's test client with the real local mock
CRM dependency. They do not demonstrate access to an external production CRM
or a deployed Django service. The merged working tree was evaluated on the
feature branch; these results do not imply a merge into `main`.

## Limits of this evaluation

- Endpoint tests use Django's in-process test client. This pytest run did not
  exercise a deployed server, Postman, or network transport.
- Actual Task 1 CRM integration, remote CRM failure behavior, authentication,
  currency conversion, and transaction replay are outside this standalone
  Task 2 result.
- JSON-number serialization has normal binary floating-point representation
  limits for clients. The implementation does not promise arbitrary-precision
  decimal transport or perform currency-specific rounding.
- Fixtures are read-only local JSON storage. Concurrent file writers, database
  transactions, production load, and deployment behavior were not evaluated.
- No line/branch coverage percentage was measured. Passing the recorded suite
  supports the criteria above; it is not a claim that every possible input has
  been tested.
- This evaluation made no application changes and did not merge anything into
  `main`.
