"""Task 2 calculation tests and HTTP contract tests, without a database."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from portfolio.holdings import calculate_holdings


SEED_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "seed.json"
OUTPUT_FIELDS = {
    "ticker", "name", "assetClass", "quantity", "costBasisPerShare", "price",
    "previousClosePrice", "marketValue", "weightPercent", "unrealizedGainLoss",
    "dayChangeAmount", "dayChangePercent",
}
NUMBER_FIELDS = OUTPUT_FIELDS - {"ticker", "name", "assetClass"}
CURRENCY_FIELDS = {"currency", "exchangeRate", "exchangeRateAsOf"}  # Task 7 metadata


def seed_data():
    return json.loads(SEED_PATH.read_text(encoding="utf-8"), parse_float=Decimal)


def example_holding(**changes):
    holding = {
        "portfolioId": "P-TEST", "ticker": "TEST", "name": "Test Security",
        "assetClass": "Equity", "quantity": 2, "costBasisPerShare": 8,
        "price": 12, "previousClosePrice": 10,
    }
    holding.update(changes)
    return holding


class HoldingsCalculationTests(unittest.TestCase):
    """These tests can run with unittest without configuring Django settings."""

    def test_supplied_seed_values_match_hand_calculations(self):
        positions = [h for h in seed_data()["holdings"] if h["portfolioId"] == "P-9001"]
        apple, bond, closed = calculate_holdings(positions)
        self.assertEqual(apple["marketValue"], Decimal("27300"))
        self.assertEqual(apple["unrealizedGainLoss"], Decimal("3300"))
        self.assertEqual(apple["dayChangeAmount"], Decimal("300"))
        self.assertEqual(apple["weightPercent"], Decimal("27300") / Decimal("48930"))
        self.assertEqual(apple["dayChangePercent"], Decimal("2.5") / Decimal("225"))
        self.assertEqual(bond["marketValue"], Decimal("21630"))
        self.assertEqual(bond["unrealizedGainLoss"], Decimal("-570"))
        self.assertEqual(bond["dayChangeAmount"], Decimal("-270"))
        self.assertEqual(bond["weightPercent"], Decimal("21630") / Decimal("48930"))
        self.assertEqual(bond["dayChangePercent"], Decimal("-0.9") / Decimal("73"))
        self.assertEqual(closed["dayChangePercent"], Decimal("0.2"))
        for position in (apple, bond, closed):
            self.assertEqual(set(position), OUTPUT_FIELDS)
            for field in NUMBER_FIELDS:
                self.assertIsInstance(position[field], Decimal)

    def test_fractional_quantity_and_decimal_prices_remain_exact(self):
        result = calculate_holdings([example_holding(
            quantity=Decimal("0.125"), price=0.3,
            costBasisPerShare=0.2, previousClosePrice=0.25,
        )])[0]
        self.assertEqual(result["marketValue"], Decimal("0.0375"))
        self.assertEqual(result["unrealizedGainLoss"], Decimal("0.0125"))
        self.assertEqual(result["dayChangeAmount"], Decimal("0.00625"))
        self.assertEqual(result["dayChangePercent"], Decimal("0.2"))
        self.assertEqual(result["weightPercent"], 1)

    def test_empty_portfolio_returns_empty_list(self):
        self.assertEqual(calculate_holdings([]), [])

    def test_zero_quantity_has_zero_amounts_but_keeps_security_price_ratio(self):
        result = calculate_holdings([example_holding(quantity=0)])[0]
        for field in ("marketValue", "weightPercent", "unrealizedGainLoss", "dayChangeAmount"):
            self.assertEqual(result[field], 0, field)
        self.assertEqual(result["dayChangePercent"], Decimal("0.2"))

    def test_zero_previous_close_uses_zero_ratio_and_keeps_amount(self):
        result = calculate_holdings([example_holding(previousClosePrice=0)])[0]
        self.assertEqual(result["dayChangePercent"], 0)
        self.assertEqual(result["dayChangeAmount"], 24)

    def test_zero_prices_do_not_divide_by_zero_total(self):
        result = calculate_holdings([example_holding(price=0)])[0]
        self.assertEqual(result["marketValue"], 0)
        self.assertEqual(result["weightPercent"], 0)
        self.assertEqual(result["unrealizedGainLoss"], -16)
        self.assertEqual(result["dayChangeAmount"], -20)
        self.assertEqual(result["dayChangePercent"], -1)

    def test_offsetting_positions_with_zero_total_have_zero_weights(self):
        result = calculate_holdings([
            example_holding(quantity=2), example_holding(quantity=-2),
        ])
        self.assertEqual([h["weightPercent"] for h in result], [0, 0])
        self.assertEqual([h["marketValue"] for h in result], [24, -24])

    def test_updated_price_recomputes_values_and_all_weights(self):
        source = [example_holding(quantity=1, price=10), example_holding(quantity=1, price=10)]
        before = calculate_holdings(source)
        source[0]["price"] = 30
        after = calculate_holdings(source)
        self.assertEqual([h["weightPercent"] for h in before], [Decimal("0.5")] * 2)
        self.assertEqual([h["weightPercent"] for h in after], [Decimal("0.75"), Decimal("0.25")])
        self.assertEqual(after[0]["marketValue"], 30)
        self.assertEqual(after[0]["unrealizedGainLoss"], 22)
        self.assertEqual(after[0]["dayChangeAmount"], 20)

    def test_derived_fields_are_recomputed_and_source_is_unchanged(self):
        source = [example_holding(
            holdingId="private-id", marketValue=999, weightPercent=999,
            unrealizedGainLoss=999, dayChangeAmount=999, dayChangePercent=999,
        )]
        saved = deepcopy(source)
        result = calculate_holdings(source)[0]
        self.assertEqual(source, saved)
        self.assertEqual(set(result), OUTPUT_FIELDS)
        self.assertEqual(result["marketValue"], 24)
        self.assertEqual(result["weightPercent"], 1)
        self.assertEqual(result["unrealizedGainLoss"], 8)
        self.assertEqual(result["dayChangeAmount"], 4)
        self.assertEqual(result["dayChangePercent"], Decimal("0.2"))

    def test_required_numeric_fields_reject_missing_null_boolean_string_and_nonfinite(self):
        invalid_values = [None, True, False, "12", [], {}, float("nan"), float("inf"),
                          Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity")]
        for field in ("quantity", "price", "costBasisPerShare", "previousClosePrice"):
            missing = example_holding()
            del missing[field]
            with self.subTest(field=field, case="missing"), self.assertRaises(ValueError):
                calculate_holdings([missing])
            for value in invalid_values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate_holdings([example_holding(**{field: value})])

    def test_required_metadata_rejects_missing_blank_and_nonstring(self):
        for field in ("ticker", "name", "assetClass"):
            missing = example_holding()
            del missing[field]
            with self.subTest(field=field, case="missing"), self.assertRaises(ValueError):
                calculate_holdings([missing])
            for value in (None, "", "  ", 12, True, []):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    calculate_holdings([example_holding(**{field: value})])

    def test_invalid_collection_and_items_raise_clear_value_error(self):
        for source in (None, {}, "holdings", [None], [1], [[]]):
            with self.subTest(source=source), self.assertRaises(ValueError):
                calculate_holdings(source)

    def test_decimal_overflow_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_holdings([example_holding(quantity=Decimal("1e999999"), price=100)])


@override_settings(ROOT_URLCONF="portfolio.holdings_urls", ALLOWED_HOSTS=["testserver"])
class HoldingsEndpointTests(SimpleTestCase):
    def setUp(self):
        self.seed = seed_data()
        metadata_patch = patch(
            "portfolio.holdings_service.require_portfolio", side_effect=self._metadata
        )
        self.metadata_lookup = metadata_patch.start()
        self.addCleanup(metadata_patch.stop)

    def _metadata(self, portfolio_id):
        from utils import ApiError

        for portfolio in self.seed["portfolios"]:
            if portfolio["portfolioId"] == portfolio_id:
                return {**portfolio, "totalMarketValue": Decimal("482350.12")}
        raise ApiError(404, "not_found", "Portfolio not found.")

    def get(self, portfolio_id="P-9001", **kwargs):
        return self.client.get(f"/portfolios/{portfolio_id}/holdings", **kwargs)

    def assert_error(self, response, status, error=None):
        self.assertEqual(response.status_code, status)
        self.assertEqual(set(response.json()), {"error", "message"})
        self.assertIsInstance(response.json()["message"], str)
        if error is not None:
            self.assertEqual(response.json()["error"], error)

    def test_success_has_exact_schema_json_numbers_and_correct_seed_values(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([h["ticker"] for h in body], ["AAPL", "BND", "ZERO"])
        self.assertEqual([h["marketValue"] for h in body], [27300, 21630, 0])
        self.assertEqual([h["unrealizedGainLoss"] for h in body], [3300, -570, 0])
        self.assertEqual([h["dayChangeAmount"] for h in body], [300, -270, 0])
        self.assertAlmostEqual(body[0]["weightPercent"], 27300 / 48930)
        self.assertEqual(body[2]["dayChangePercent"], 0.2)
        for holding in body:
            self.assertEqual(set(holding), OUTPUT_FIELDS | CURRENCY_FIELDS)
            for field in NUMBER_FIELDS:
                self.assertIn(type(holding[field]), (int, float))
        self.metadata_lookup.assert_called_once_with("P-9001")

    def test_empty_portfolio_returns_200_empty_array(self):
        response = self.get("P-EMPTY")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_unknown_portfolio_returns_structured_404_before_loading_holdings(self):
        with patch("portfolio.holdings_service.load_seed") as loader:
            self.assert_error(self.get("missing"), 404)
        loader.assert_not_called()

    def test_other_portfolio_is_isolated_and_zero_previous_close_is_safe(self):
        response = self.get("P-9002")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["ticker"], "NEW")
        self.assertEqual(body[0]["marketValue"], 500)
        self.assertEqual(body[0]["weightPercent"], 1)
        self.assertEqual(body[0]["unrealizedGainLoss"], 100)
        self.assertEqual(body[0]["dayChangeAmount"], 500)
        self.assertEqual(body[0]["dayChangePercent"], 0)

    def test_single_position_has_full_weight(self):
        response = self.get("P-SINGLE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["weightPercent"], 1)

    def test_unsupported_methods_return_json_405_even_with_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        for method in ("post", "put", "patch", "delete", "options"):
            with self.subTest(method=method):
                response = getattr(client, method)("/portfolios/P-9001/holdings")
                self.assert_error(response, 405)
                self.assertEqual(response.headers["Allow"], "GET, HEAD")
        self.metadata_lookup.assert_not_called()

    def test_head_returns_success_without_response_body(self):
        response = self.client.head("/portfolios/P-9001/holdings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_invalid_holdings_source_returns_structured_503(self):
        invalid_sources = [None, [], {}, {"holdings": None}, {"holdings": {}},
                           {"holdings": [None]}, {"holdings": [{}]},
                           {"holdings": [example_holding(portfolioId=None)]},
                           {"holdings": [example_holding(portfolioId="")]},
                           {"holdings": [example_holding(portfolioId="P-9001", price=None)]}]
        for source in invalid_sources:
            with self.subTest(source=source), patch(
                "portfolio.holdings_service.load_seed", return_value=source
            ):
                self.assert_error(self.get(), 503, "data_unavailable")

    def test_seed_file_is_read_again_and_derived_values_are_recalculated(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            path.write_text(json.dumps(seed), encoding="utf-8")
            with override_settings(PORTFOLIO_SEED_PATH=path):
                before = self.get().json()
                seed["holdings"][0]["price"] = 250
                seed["holdings"][0]["marketValue"] = 999
                path.write_text(json.dumps(seed), encoding="utf-8")
                after = self.get().json()
        self.assertEqual(before[0]["marketValue"], 27300)
        self.assertEqual(after[0]["marketValue"], 30000)
        self.assertAlmostEqual(after[0]["weightPercent"], 30000 / 51630)
        self.assertAlmostEqual(after[1]["weightPercent"], 21630 / 51630)

    def test_missing_and_malformed_json_files_return_structured_503(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "seed.json"
            with override_settings(PORTFOLIO_SEED_PATH=path):
                self.assert_error(self.get(), 503, "data_unavailable")
                path.write_text("{invalid json", encoding="utf-8")
                self.assert_error(self.get(), 503, "data_unavailable")

    def test_metadata_provider_failure_is_preserved(self):
        from utils import ApiError

        self.metadata_lookup.side_effect = ApiError(
            503, "crm_unavailable", "Portfolio metadata is temporarily unavailable."
        )
        self.assert_error(self.get(), 503, "crm_unavailable")

    def test_numbers_outside_json_encoder_range_return_structured_503(self):
        source = {"holdings": [example_holding(
            portfolioId="P-9001", quantity=Decimal("1e200"), price=Decimal("1e200")
        )]}
        with patch("portfolio.holdings_service.load_seed", return_value=source):
            self.assert_error(self.get(), 503, "data_unavailable")
