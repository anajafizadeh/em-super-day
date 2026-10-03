import copy
import json
from decimal import Decimal

import pytest

from portfolio.normalizers import normalize_crm_portfolio, normalize_portfolio_id
from utils import ApiError


def _payload():
    """Standard CRM shape (as the mock sends it), parsed the same way the client parses it."""
    raw = {
        'client_record': {
            'client_id': 'abc123',
            'full_name': 'Jane Doe',
            'accounts': [
                {
                    'acct_ref': 'P-9001',
                    'acct_nickname': 'Taxable Brokerage',
                    'curr_val': {'amt': 48930, 'ccy': 'CAD'},
                    'chg_1d': {'amt': 30, 'pct': 0.0006134969325153374},
                    'since_inception_pct': 0.187,
                },
                {
                    'acct_ref': 'P-9002',
                    'acct_nickname': 'Retirement Account',
                    'curr_val': {'amt': 500, 'ccy': 'CAD'},
                    'chg_1d': {'amt': 500, 'pct': 0},
                    'since_inception_pct': 0.25,
                },
            ],
        },
        'meta': {'retrieved_at': '2026-10-03T16:52:06.123Z', 'source': 'legacy-crm-v2'},
    }
    return json.loads(json.dumps(raw), parse_float=Decimal)


def _account(payload, ref='P-9001'):
    return next(a for a in payload['client_record']['accounts'] if a['acct_ref'] == ref)


def _assert_api_error(exc_info, status, error):
    assert exc_info.value.status == status
    assert exc_info.value.error == error


# --- normalize_portfolio_id ---

@pytest.mark.parametrize('raw, expected', [
    ('P-9001', 'P-9001'),
    ('  p-9002 ', 'P-9002'),
    ('p_empty', 'P_EMPTY'),
])
def test_portfolio_id_is_stripped_and_uppercased(raw, expected):
    assert normalize_portfolio_id(raw) == expected


@pytest.mark.parametrize('raw', ['', '   ', 'bad!id', 'P 9001', 'A' * 65, '../etc', None])
def test_invalid_portfolio_id_is_rejected(raw):
    with pytest.raises(ApiError) as exc_info:
        normalize_portfolio_id(raw)
    _assert_api_error(exc_info, 400, 'invalid_portfolio_id')
    assert exc_info.value.message == 'Invalid ID provided.'


# --- normalize_crm_portfolio: shapes ---

def test_standard_shape_maps_to_schema():
    result = normalize_crm_portfolio(_payload(), 'P-9001')
    assert result == {
        'portfolioId': 'P-9001',
        'clientId': 'abc123',
        'label': 'Taxable Brokerage',
        'currency': 'CAD',
        'totalMarketValue': Decimal('48930'),
        'dayChangeAmount': Decimal('30'),
        'dayChangePercent': Decimal('0.0006134969325153374'),
        'totalReturnSinceInception': Decimal('0.187'),
        'asOf': '2026-10-03T16:52:06.123Z',
    }


def test_selects_requested_account_not_first():
    result = normalize_crm_portfolio(_payload(), 'P-9002')
    assert result['portfolioId'] == 'P-9002'
    assert result['label'] == 'Retirement Account'
    assert result['dayChangePercent'] == Decimal('0')


def test_nested_accounts_shape_is_supported():
    payload = _payload()
    accounts = payload['client_record'].pop('accounts')
    payload['client_record']['relationships'] = {'accounts': accounts}
    assert normalize_crm_portfolio(payload, 'P-9001') == normalize_crm_portfolio(_payload(), 'P-9001')


def test_missing_values_become_null():
    payload = _payload()
    account = _account(payload)
    account['curr_val']['amt'] = None
    del account['acct_nickname']
    del account['chg_1d']
    del account['since_inception_pct']
    del payload['meta']

    result = normalize_crm_portfolio(payload, 'P-9001')
    assert result['label'] is None
    assert result['totalMarketValue'] is None
    assert result['dayChangeAmount'] is None
    assert result['dayChangePercent'] is None
    assert result['totalReturnSinceInception'] is None
    assert result['asOf'] is None
    assert result['currency'] == 'CAD'


def test_acct_ref_is_matched_case_and_whitespace_insensitively():
    payload = _payload()
    _account(payload)['acct_ref'] = ' p-9001 '
    assert normalize_crm_portfolio(payload, 'P-9001')['portfolioId'] == 'P-9001'


def test_int_values_become_decimal():
    result = normalize_crm_portfolio(_payload(), 'P-9001')
    assert isinstance(result['totalMarketValue'], Decimal)


# --- normalize_crm_portfolio: errors ---

def test_unknown_account_is_404():
    with pytest.raises(ApiError) as exc_info:
        normalize_crm_portfolio(_payload(), 'P-0000')
    _assert_api_error(exc_info, 404, 'portfolio_not_found')


def test_duplicate_account_is_bad_response():
    payload = _payload()
    payload['client_record']['accounts'].append(copy.deepcopy(_account(payload)))
    with pytest.raises(ApiError) as exc_info:
        normalize_crm_portfolio(payload, 'P-9001')
    _assert_api_error(exc_info, 400, 'crm_bad_response')


@pytest.mark.parametrize('mutate', [
    lambda p: p.pop('client_record'),
    lambda p: p['client_record'].pop('accounts'),
    lambda p: p['client_record'].update(accounts='not-a-list'),
    lambda p: p['client_record']['accounts'].append('not-an-object'),
    lambda p: p['client_record'].pop('client_id'),
    lambda p: p['client_record'].update(client_id='  '),
    lambda p: _account(p).pop('acct_ref'),
    lambda p: _account(p)['curr_val'].pop('ccy'),
    lambda p: _account(p).pop('curr_val'),
], ids=[
    'no-client-record', 'no-accounts', 'accounts-not-list', 'account-not-object',
    'no-client-id', 'blank-client-id', 'no-acct-ref', 'no-currency', 'no-curr-val',
])
def test_missing_required_fields_are_bad_response(mutate):
    payload = _payload()
    mutate(payload)
    with pytest.raises(ApiError) as exc_info:
        normalize_crm_portfolio(payload, 'P-9001')
    _assert_api_error(exc_info, 400, 'crm_bad_response')


@pytest.mark.parametrize('ccy', ['EUR', 'USD'])
def test_non_native_currency_is_bad_response(ccy):
    payload = _payload()
    _account(payload)['curr_val']['ccy'] = ccy
    with pytest.raises(ApiError) as exc_info:
        normalize_crm_portfolio(payload, 'P-9001')
    _assert_api_error(exc_info, 400, 'crm_bad_response')


def test_lowercase_currency_is_normalized():
    payload = _payload()
    _account(payload)['curr_val']['ccy'] = ' cad '
    assert normalize_crm_portfolio(payload, 'P-9001')['currency'] == 'CAD'


@pytest.mark.parametrize('field_path, value', [
    (('curr_val', 'amt'), True),
    (('curr_val', 'amt'), '48930'),
    (('chg_1d', 'pct'), [0.1]),
    (('acct_nickname',), 42),
    (('acct_nickname',), '   '),
])
def test_wrong_types_are_bad_response(field_path, value):
    payload = _payload()
    target = _account(payload)
    for key in field_path[:-1]:
        target = target[key]
    target[field_path[-1]] = value
    with pytest.raises(ApiError) as exc_info:
        normalize_crm_portfolio(payload, 'P-9001')
    _assert_api_error(exc_info, 400, 'crm_bad_response')


# --- asOf ---

@pytest.mark.parametrize('retrieved_at, expected', [
    ('2026-10-03T16:52:06.123Z', '2026-10-03T16:52:06.123Z'),
    ('2026-10-03T16:52:06Z', '2026-10-03T16:52:06.000Z'),
    ('2026-10-03T12:52:06.123-04:00', '2026-10-03T16:52:06.123Z'),
    ('2026-10-03T16:52:06', None),
    ('not a date', None),
    (12345, None),
    (None, None),
])
def test_as_of_is_normalized_to_utc_milliseconds(retrieved_at, expected):
    payload = _payload()
    payload['meta']['retrieved_at'] = retrieved_at
    assert normalize_crm_portfolio(payload, 'P-9001')['asOf'] == expected
