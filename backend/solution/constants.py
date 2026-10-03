"""Shared, non-secret constants from the spec.

Examples: placeholders, supported values (currencies, ranges), timeouts and
retry policy. Secrets and environment-specific config belong in .env.local.
"""

PERFORMANCE_RANGES = ('1D', '1M', 'YTD', '1Y', 'All')
