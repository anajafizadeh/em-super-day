"""Shared, non-secret constants from the spec.

Examples: placeholders, supported values (currencies, ranges), timeouts and
retry policy. Secrets and environment-specific config belong in .env.local.
"""

from decimal import Decimal

# CRM integration (Task 1). Retries apply only to timeouts, connection errors and 5xx.
CRM_TIMEOUT_SECONDS = 2
CRM_MAX_RETRIES = 1
CRM_PORTFOLIO_PATH = '/crm/portfolios/{portfolio_id}'

# Portfolio ids are stripped and uppercased before this check.
PORTFOLIO_ID_PATTERN = r'^[A-Z0-9_-]{1,64}$'

# Every portfolio is held in CAD; SUPPORTED_CURRENCIES are the display currencies (Task 7).
NATIVE_CURRENCY = 'CAD'
SUPPORTED_CURRENCIES = ('CAD', 'USD')

# ExchangeRate-API (Task 7). Rates refresh daily; retries apply only to timeouts,
# connection errors and 5xx. After a failed refresh, wait before calling again.
FX_BASE_URL = 'https://v6.exchangerate-api.com/v6'
FX_PAIR_PATH = '/{key}/pair/{base}/{target}'
FX_TIMEOUT_SECONDS = 2
FX_MAX_RETRIES = 1
FX_FAILURE_COOLDOWN_SECONDS = 300

# Converted money is rounded to cents (ROUND_HALF_UP).
MONEY_QUANTUM = Decimal('0.01')

PERFORMANCE_RANGES = ('1D', '1M', 'YTD', '1Y', 'All')
