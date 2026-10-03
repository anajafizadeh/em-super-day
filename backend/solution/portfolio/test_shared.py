"""Tests for shared errors, fixture loading, and the Task 1 integration contract."""

from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from portfolio.data import load_json, require_portfolio
from utils import ApiError, error_response, json_response


class SharedResponseTests(SimpleTestCase):
    def test_decimal_is_a_json_number(self):
        response = json_response([{'marketValue': Decimal('12.34')}])
        self.assertJSONEqual(response.content, [{'marketValue': 12.34}])

    def test_error_contract(self):
        response = error_response(ApiError(400, 'invalid_range', 'Unsupported range.'))
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {
            'error': 'invalid_range', 'message': 'Unsupported range.',
        })

    def test_nonfinite_output_is_rejected(self):
        for value in (Decimal('NaN'), Decimal('Infinity'), Decimal('1e10000')):
            with self.subTest(value=value):
                with self.assertRaises(ApiError) as raised:
                    json_response([value])
                self.assertEqual(raised.exception.status, 503)

    @override_settings(DEBUG=False)
    def test_unknown_route_has_a_json_error(self):
        response = self.client.get('/not-a-route')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error'], 'not_found')


class FixtureTests(SimpleTestCase):
    def test_file_numbers_preserve_decimal_precision(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'
            path.write_text('{"price": 0.1}', encoding='utf-8')
            self.assertEqual(load_json(path)['price'], Decimal('0.1'))

    def test_missing_malformed_and_nonfinite_data_are_explicit_errors(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.json'
            for payload in (None, '{', '[]', '{"price": NaN}', '{"price": Infinity}'):
                with self.subTest(payload=payload):
                    if payload is not None:
                        path.write_text(payload, encoding='utf-8')
                    with self.assertRaises(ApiError) as raised:
                        load_json(path)
                    self.assertEqual(raised.exception.status, 503)

    @override_settings(GET_CRM_DATA_CALLABLE='')
    def test_local_empty_portfolio_is_known(self):
        self.assertEqual(require_portfolio('P-EMPTY')['portfolioId'], 'P-EMPTY')

    @override_settings(GET_CRM_DATA_CALLABLE='')
    def test_unknown_portfolio_is_404(self):
        with self.assertRaises(ApiError) as raised:
            require_portfolio('UNKNOWN')
        self.assertEqual(raised.exception.status, 404)

    @override_settings(GET_CRM_DATA_CALLABLE='teammate.crm.get_crm_data')
    @patch('portfolio.data.import_string')
    def test_get_crm_data_receives_id_and_returns_task1_schema(self, import_provider):
        metadata = {
            'portfolioId': 'P-9001', 'clientId': 'abc123', 'label': 'Taxable Brokerage',
            'currency': 'CAD', 'totalMarketValue': 48930, 'dayChangeAmount': 30,
            'dayChangePercent': 0.0006, 'totalReturnSinceInception': 0.187,
            'asOf': '2026-10-03T00:00:00Z',
        }
        import_provider.return_value.return_value = metadata
        self.assertEqual(require_portfolio('P-9001'), metadata)
        import_provider.assert_called_once_with('teammate.crm.get_crm_data')
        import_provider.return_value.assert_called_once_with('P-9001')

    @override_settings(GET_CRM_DATA_CALLABLE='teammate.crm.get_crm_data')
    @patch('portfolio.data.import_string')
    def test_wrong_crm_portfolio_is_rejected(self, import_provider):
        import_provider.return_value.return_value = {'portfolioId': 'P-9002'}
        with self.assertRaises(ApiError) as raised:
            require_portfolio('P-9001')
        self.assertEqual(raised.exception.status, 502)

    @override_settings(GET_CRM_DATA_CALLABLE='teammate.crm.get_crm_data')
    @patch('portfolio.data.import_string')
    def test_crm_errors_keep_their_status(self, import_provider):
        import_provider.return_value.side_effect = ApiError(404, 'portfolio_not_found', 'Unknown portfolio.')
        with self.assertRaises(ApiError) as raised:
            require_portfolio('UNKNOWN')
        self.assertEqual(raised.exception.status, 404)
