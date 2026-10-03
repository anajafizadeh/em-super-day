# Backend solution (Django)

Python 3.14, Django 5.2 LTS.

Task 2 is developed on `EM-XW-002-T02`; Task 3 is developed on
`EM-XW-004-T03`. Each branch can be run and tested independently. Task-specific
behavior, examples, and validation details are in this branch's `docs/` folder.
Neither branch implements Task 1, authentication (Task 4), currency conversion
(Task 7), or ledger replay (Task 10).

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

When the teammate's helper is available, set `GET_CRM_DATA_CALLABLE` in
`.env.local` to its real dotted Python path, for example
`portfolio.crm.get_crm_data` **if that is where it is implemented**. Restart the
server after changing configuration.

The synchronous function accepts one portfolio ID and returns the mapped Task 1
dictionary (`portfolioId`, `clientId`, `label`, `currency`, `totalMarketValue`,
`dayChangeAmount`, `dayChangePercent`, `totalReturnSinceInception`, `asOf`). It
should raise the shared `utils.ApiError(status, error, message)` for expected
failures, including unknown portfolio IDs. Task 1 owns CRM timeouts and retries.

The shared adapter checks the requested portfolio identity. Task 2 still computes
the weight denominator from the current holdings. Task 3 reads historical values
from the separate history store: the Task 1 schema contains no holdings or daily
snapshots. Until the helper exists, a blank `GET_CRM_DATA_CALLABLE` uses the
portfolio registry in `backend/fixtures/seed.json`. Contract tests substitute the
documented Task 1 output; live teammate integration remains to be verified.

## Validation and tests

See the [Task 2 pytest evaluation report](docs/TASK-02-EVALUATION.md) for the
verified results, acceptance criteria, limitations, and exact rerun command.

With the virtual environment active and `.env.local` configured, run from
`backend/solution/`:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity 2
python -m pip check
```

The suite exercises pure calculations, storage/metadata integration, and Django
HTTP responses. It uses fixed dates and temporary data files where appropriate;
it needs neither a running CRM nor generated history. No new database tables or
migrations are required. Monetary calculations use `Decimal` internally and
serialize as JSON numbers. All values remain in native CAD, and percentages are
decimal ratios.

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
