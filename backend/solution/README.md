# Backend solution (Django)

Python 3.14, Django 5.2 LTS.

This checkout combines Task 1 CRM metadata and Task 2 holdings from `main` with
Task 3 performance history on `EM-XW-004-T03`. All three endpoints can run in one
Django service. Task-specific behavior, examples, and evaluation reports are in
`docs/`. Authentication (Task 4), currency conversion (Task 7), and ledger replay
(Task 10) remain outside these tasks.

## Setup

```sh
cd backend/solution
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local   # then set DJANGO_SECRET_KEY
```

The app fails fast with `ImproperlyConfigured` if a required variable is missing.

On Windows PowerShell, from `backend/solution/`:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env.local
# Set DJANGO_SECRET_KEY in .env.local to a local development secret.
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:3000
```

## Run

```sh
node backend/mock-crm.mjs          # from the repo root, in another terminal
python manage.py runserver 3000
```

Tasks 2/3 use the supplied local JSON data by default and do not require a running
CRM. `CRM_BASE_URL` remains required by the shared project configuration. For
Task 3, first generate the history fixture **from the repository root**:

```sh
node backend/fixtures/generate-history.mjs
```

Regenerate when needed to keep sample dates current. The generated file is
gitignored. The endpoint only reads stored snapshots; it never invents or pads
history. An absent or malformed data file produces a structured HTTP 503.

## Task 1 integration

The teammate's helper is available as `portfolio.services.get_crm_data`.
`GET /portfolios/{portfolioId}` calls it directly. To use it for Task 2/3
portfolio identity checks as well, set
`GET_CRM_DATA_CALLABLE=portfolio.services.get_crm_data` in `.env.local` and start
the mock CRM. Restart the Django server after changing configuration.

The synchronous function accepts one portfolio ID and returns the mapped Task 1
dictionary (`portfolioId`, `clientId`, `label`, `currency`, `totalMarketValue`,
`dayChangeAmount`, `dayChangePercent`, `totalReturnSinceInception`, `asOf`). It
should raise the shared `utils.ApiError(status, error, message)` for expected
failures, including unknown portfolio IDs. Task 1 owns CRM timeouts and retries.

The shared adapter checks the requested portfolio identity. Task 2 still computes
the weight denominator from the current holdings. Task 3 reads historical values
from the separate history store: the Task 1 schema contains no holdings or daily
snapshots. A blank `GET_CRM_DATA_CALLABLE` retains the local portfolio registry in
`backend/fixtures/seed.json` for independent Task 2/3 demos.

## Validation and tests

English evaluation reports:

- [Task 2 evaluation](docs/TASK-02-EVALUATION.md)
- [Task 3 evaluation](docs/TASK-03-EVALUATION.md)

With the virtual environment active and `.env.local` configured, run from
`backend/solution/`:

```sh
python -m pip install -r requirements-dev.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python -m pytest -v
python -m pip check
```

The suite exercises all three tasks: pure calculations, storage, CRM mapping,
transport errors, and Django HTTP responses. Task 1 integration tests require a
running mock CRM at `CRM_BASE_URL` and otherwise skip; use a dedicated mock for
testing because they change its failure mode. All other tests use test doubles
or temporary files. Run `python -m pytest -m "not integration" -v` for the offline
suite. Generated history is not required by the tests. No new database tables or
migrations are required for these endpoints. Monetary calculations use `Decimal`
internally and serialize as JSON numbers; values remain in native CAD and
percentages are decimal ratios.

Run the supplied mock regression tests from the repository root:

```sh
node --test support/*.test.mjs
```

Run these checks locally using Python 3.14 and Node.js 24. The optional local
`.github/workflows/backend.yml` file is excluded from version control.

## Layout

- `config/`: project settings and root URLconf
- `portfolio/`: the portfolio app; its routes are in `portfolio/urls.py`, mounted at `/`
- `constants.py`: shared non-secret constants from the spec
- `utils.py`: shared API errors, Decimal JSON encoding, and JSON error handlers
- `portfolio/data.py`: fixture loading and the configurable Task 1 adapter
- `portfolio/views.py`: thin HTTP adapters that call task services
- `portfolio/holdings*` or `portfolio/performance*`: task calculations, service,
  and URL modules, depending on the branch
