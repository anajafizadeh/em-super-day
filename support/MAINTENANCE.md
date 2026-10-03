# Maintaining the supplied mocks

From the repository root, run:

```sh
node --test support/*.test.mjs
```

The tests start their own servers on free ports and stop them when finished. They cover dataset consistency, edge datasets, HTTP errors, browser access, and CRM controls/timeouts. They test the supplied materials, not candidates' solutions.

- `frontend/mock-server.mjs` and `mobile/mock-server.mjs` start the shared portfolio API on different ports.
- `support/portfolio-data.mjs` contains fictional UI datasets. It is not the backend track's solution.
- `backend/crm-service.mjs` serves legacy CRM fixtures. Its controls make failures repeatable.
- `backend/fixtures/seed.json` supplies optional raw inputs for backend candidates.
- `*/REQUIREMENTS.md` are the original challenge requirements.

Keep the `support/` folder when sharing any track. The mocks have no third-party dependencies. A candidate's solution should have its own project configuration and tests.
