"""One real call to ExchangeRate-API (uses quota). Run explicitly: pytest -m fx_live"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from portfolio.fx_client import fetch_pair_rate

pytestmark = pytest.mark.fx_live


def test_live_cad_usd_rate_has_expected_shape():
    result = fetch_pair_rate('CAD', 'USD')
    assert isinstance(result['rate'], Decimal)
    assert Decimal('0.3') < result['rate'] < Decimal('1.5')
    assert result['as_of'].endswith('Z')
    assert result['next_update'] > datetime(2020, 1, 1, tzinfo=timezone.utc)
