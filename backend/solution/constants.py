"""Shared, non-secret constants from the spec.

Examples: placeholders, supported values (currencies, ranges), timeouts and
retry policy. Secrets and environment-specific config belong in .env.local.
"""

# CRM integration (Task 1). Retries apply only to timeouts, connection errors and 5xx.
CRM_TIMEOUT_SECONDS = 2
CRM_MAX_RETRIES = 1
CRM_PORTFOLIO_PATH = '/crm/portfolios/{portfolio_id}'

# Portfolio ids are stripped and uppercased before this check.
PORTFOLIO_ID_PATTERN = r'^[A-Z0-9_-]{1,64}$'

# Currencies we can serve (Task 7 converts between them).
SUPPORTED_CURRENCIES = ('CAD', 'USD')
