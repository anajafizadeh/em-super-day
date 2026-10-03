"""Deterministic pure-unit and HTTP tests for the performance-history API."""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from portfolio.performance import (
    InvalidHistory,
    InvalidRange,
    filter_performance_history,
)
from utils import ApiError


def snapshots(*dates):
    return [{"date": day, "marketValue": 100.25} for day in dates]


class PerformanceFilteringTests(TestCase):
    """No Django setup, database, network, or fixture files are required."""

    def assert_dates(self, rows, expected, range_name="All", today=date(2026, 3, 31)):
        actual = filter_performance_history(rows, range_name, today=today)
        self.assertEqual([row["date"] for row in actual], expected)

    def test_all_supported_ranges_include_their_boundaries(self):
        days = [
            "2025-03-30", "2025-03-31", "2025-12-31", "2026-01-01",
            "2026-02-27", "2026-02-28", "2026-03-30", "2026-03-31",
            "2026-04-01",
        ]
        expected = {
            "All": days[:-1],
            "1Y": days[1:-1],
            "YTD": days[3:-1],
            "1M": days[5:-1],
            "1D": ["2026-03-31"],
        }
        for range_name, included in expected.items():
            with self.subTest(range_name=range_name):
                self.assert_dates(snapshots(*reversed(days)), included, range_name)

    def test_month_clamps_to_leap_february_end(self):
        self.assert_dates(
            snapshots("2024-02-28", "2024-02-29", "2024-03-31"),
            ["2024-02-29", "2024-03-31"], "1M", date(2024, 3, 31),
        )

    def test_month_crosses_year_boundary(self):
        self.assert_dates(
            snapshots("2025-12-30", "2025-12-31", "2026-01-31"),
            ["2025-12-31", "2026-01-31"], "1M", date(2026, 1, 31),
        )

    def test_year_clamps_february_29(self):
        self.assert_dates(
            snapshots("2023-02-27", "2023-02-28", "2024-02-29"),
            ["2023-02-28", "2024-02-29"], "1Y", date(2024, 2, 29),
        )

    def test_year_uses_calendar_date_instead_of_365_days(self):
        self.assert_dates(
            snapshots("2024-02-27", "2024-02-28", "2024-02-29", "2025-02-28"),
            ["2024-02-28", "2024-02-29", "2025-02-28"], "1Y", date(2025, 2, 28),
        )

    def test_ytd_on_january_first(self):
        self.assert_dates(
            snapshots("2025-12-31", "2026-01-01", "2026-01-02"),
            ["2026-01-01"], "YTD", date(2026, 1, 1),
        )

    def test_stale_history_does_not_move_range_back_to_latest_snapshot(self):
        rows = snapshots("2024-01-01", "2025-01-01")
        for range_name in ("1D", "1M", "YTD", "1Y"):
            with self.subTest(range_name=range_name):
                self.assert_dates(rows, [], range_name)

    def test_short_history_and_gaps_are_returned_without_padding(self):
        days = ["2026-01-02", "2026-02-18", "2026-03-31"]
        self.assert_dates(snapshots(*days), days, "1Y")

    def test_empty_history_for_every_range(self):
        for range_name in ("1D", "1M", "YTD", "1Y", "All"):
            with self.subTest(range_name=range_name):
                self.assert_dates([], [], range_name)

    def test_all_still_excludes_future_dates(self):
        self.assert_dates(snapshots("2026-04-01", "2027-01-01"), [])

    def test_input_is_not_mutated_and_output_is_schema_limited(self):
        rows = [
            {"date": "2026-03-31", "marketValue": Decimal("100.01"), "source": "test"},
            {"date": "2026-03-30", "marketValue": 0.1},
        ]
        original = deepcopy(rows)
        result = filter_performance_history(rows, today=date(2026, 3, 31))
        self.assertEqual(rows, original)
        self.assertEqual(result, [
            {"date": "2026-03-30", "marketValue": Decimal("0.1")},
            {"date": "2026-03-31", "marketValue": Decimal("100.01")},
        ])
        result[0]["marketValue"] = Decimal("999")
        self.assertEqual(rows, original)

    def test_zero_and_negative_market_values_are_valid_numbers(self):
        rows = [
            {"date": "2026-03-30", "marketValue": 0},
            {"date": "2026-03-31", "marketValue": -10.25},
        ]
        result = filter_performance_history(rows, today=date(2026, 3, 31))
        self.assertEqual([row["marketValue"] for row in result], [Decimal(0), Decimal("-10.25")])

    def test_invalid_ranges_are_rejected(self):
        for range_name in ("", "all", "1d", "1W", " All", None, 1, []):
            with self.subTest(range_name=range_name), self.assertRaises(InvalidRange):
                filter_performance_history([], range_name, today=date(2026, 3, 31))

    def test_invalid_dates_are_rejected_including_outside_range(self):
        for value in (None, 123, "2026-02-30", "20260331", "2026-W14-2", "2026-3-1", "2026-03-31T00:00:00Z"):
            with self.subTest(value=value), self.assertRaises(InvalidHistory):
                filter_performance_history(
                    [{"date": value, "marketValue": 1}], "1D", today=date(2026, 3, 31)
                )

    def test_invalid_numbers_are_rejected(self):
        for value in (None, True, False, "100", [], {}, float("nan"), float("inf"),
                      float("-inf"), Decimal("NaN"), Decimal("Infinity"), Decimal("1e999")):
            with self.subTest(value=value), self.assertRaises(InvalidHistory):
                filter_performance_history(
                    [{"date": "2026-03-31", "marketValue": value}], today=date(2026, 3, 31)
                )

    def test_missing_fields_and_malformed_rows_are_rejected(self):
        for row in (None, [], "snapshot", {}, {"date": "2026-03-31"}, {"marketValue": 1}):
            with self.subTest(row=row), self.assertRaises(InvalidHistory):
                filter_performance_history([row], today=date(2026, 3, 31))

    def test_non_array_history_is_rejected(self):
        for rows in (None, {}, "history", ()):
            with self.subTest(rows=rows), self.assertRaises(InvalidHistory):
                filter_performance_history(rows, today=date(2026, 3, 31))

    def test_duplicate_daily_snapshots_are_rejected(self):
        with self.assertRaises(InvalidHistory):
            filter_performance_history(
                snapshots("2026-03-31", "2026-03-31"), today=date(2026, 3, 31)
            )


class PerformanceHistoryApiTests(SimpleTestCase):
    """Exercise Django routing and real JSON storage with temporary fixtures."""

    url = "/portfolios/P-TEST/performance-history"

    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.history_path = Path(temporary.name) / "performance-history.json"
        seed_path = Path(temporary.name) / "seed.json"
        seed_path.write_text(json.dumps({"portfolios": [
            {"portfolioId": "P-TEST"}, {"portfolioId": "P-EMPTY"},
        ]}), encoding="utf-8")
        self.rows = snapshots(
            "2026-04-01", "2026-03-31", "2026-02-28", "2026-01-01",
            "2025-12-31", "2025-03-31", "2025-03-30",
        )
        self.write_history({"P-TEST": self.rows, "P-EMPTY": []})
        settings_override = override_settings(
            PORTFOLIO_SEED_PATH=seed_path,
            PORTFOLIO_HISTORY_PATH=self.history_path,
            GET_CRM_DATA_CALLABLE="",
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        clock = patch("portfolio.performance_service.utc_today", return_value=date(2026, 3, 31))
        self.clock = clock.start()
        self.addCleanup(clock.stop)

    def write_history(self, data):
        self.history_path.write_text(json.dumps(data), encoding="utf-8")

    def assert_error(self, response, status):
        self.assertEqual(response.status_code, status)
        self.assertEqual(set(response.json()), {"error", "message"})
        self.assertIsInstance(response.json()["error"], str)
        self.assertIsInstance(response.json()["message"], str)

    def test_default_all_schema_and_json_number(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        expected = sorted(row["date"] for row in self.rows if row["date"] <= "2026-03-31")
        self.assertEqual([row["date"] for row in response.json()], expected)
        for row in response.json():
            self.assertEqual(set(row), {"date", "marketValue"})
            self.assertIsInstance(row["marketValue"], (int, float))
            self.assertEqual(row["marketValue"], 100.25)

    def test_every_range_is_filtered_over_http(self):
        expected = {
            "1D": ["2026-03-31"],
            "1M": ["2026-02-28", "2026-03-31"],
            "YTD": ["2026-01-01", "2026-02-28", "2026-03-31"],
            "1Y": ["2025-03-31", "2025-12-31", "2026-01-01", "2026-02-28", "2026-03-31"],
            "All": ["2025-03-30", "2025-03-31", "2025-12-31", "2026-01-01", "2026-02-28", "2026-03-31"],
        }
        for range_name, included in expected.items():
            with self.subTest(range_name=range_name):
                response = self.client.get(self.url, {"range": range_name})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([row["date"] for row in response.json()], included)

    def test_invalid_range_returns_structured_400(self):
        for range_name in ("", "1W", "all", "1d", " All"):
            with self.subTest(range_name=range_name):
                response = self.client.get(self.url, {"range": range_name})
                self.assert_error(response, 400)
                self.assertEqual(response.json()["error"], "invalid_range")

    def test_unknown_portfolio_returns_structured_404(self):
        self.assert_error(self.client.get("/portfolios/UNKNOWN/performance-history"), 404)

    def test_empty_portfolio_returns_empty_array(self):
        response = self.client.get("/portfolios/P-EMPTY/performance-history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_short_history_is_returned_without_padding(self):
        rows = snapshots("2026-01-01", "2026-02-28", "2026-03-31")
        self.write_history({"P-TEST": rows})
        response = self.client.get(self.url, {"range": "1Y"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), rows)

    def test_missing_file_returns_structured_503(self):
        self.history_path.unlink()
        self.assert_error(self.client.get(self.url), 503)

    def test_invalid_json_returns_structured_503(self):
        self.history_path.write_text("{broken", encoding="utf-8")
        self.assert_error(self.client.get(self.url), 503)

    def test_oversized_json_number_returns_structured_503(self):
        self.history_path.write_text(
            '{"P-TEST": [{"date": "2026-03-31", "marketValue": 1e999}]}',
            encoding="utf-8",
        )
        self.assert_error(self.client.get(self.url), 503)

    def test_incomplete_history_does_not_look_like_empty_history(self):
        self.write_history({"P-EMPTY": []})
        self.assert_error(self.client.get(self.url), 503)

    def test_malformed_history_returns_structured_503(self):
        cases = [[], None, {"P-TEST": None}, {"P-TEST": [{"date": "wrong", "marketValue": 1}]},
                 {"P-TEST": [{"date": "2026-03-31", "marketValue": "100"}]},
                 {"P-TEST": snapshots("2026-03-31", "2026-03-31")}]
        for data in cases:
            with self.subTest(data=data):
                self.write_history(data)
                self.assert_error(self.client.get(self.url), 503)

    def test_updated_file_is_read_on_next_request(self):
        self.assertEqual(len(self.client.get(self.url, {"range": "1D"}).json()), 1)
        self.write_history({"P-TEST": [{"date": "2026-03-31", "marketValue": 999.99}]})
        response = self.client.get(self.url, {"range": "1D"})
        self.assertEqual(response.json(), [{"date": "2026-03-31", "marketValue": 999.99}])

    def test_today_is_evaluated_for_each_request(self):
        self.clock.side_effect = [date(2026, 3, 31), date(2026, 4, 1)]
        first = self.client.get(self.url, {"range": "1D"})
        second = self.client.get(self.url, {"range": "1D"})
        self.assertEqual([row["date"] for row in first.json()], ["2026-03-31"])
        self.assertEqual([row["date"] for row in second.json()], ["2026-04-01"])

    def test_head_is_supported(self):
        response = self.client.head(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_post_returns_structured_405(self):
        self.assert_error(self.client.post(self.url), 405)

    def test_unsafe_methods_return_json_with_real_csrf_checks(self):
        client = Client(enforce_csrf_checks=True)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(client, method)(self.url)
                self.assert_error(response, 405)
                self.assertEqual(response.headers["Allow"], "GET, HEAD")

    def test_metadata_provider_failure_is_not_hidden(self):
        with patch("portfolio.performance_service.require_portfolio", side_effect=ApiError(
            503, "crm_unavailable", "Portfolio metadata is unavailable."
        )):
            response = self.client.get(self.url)
        self.assert_error(response, 503)
        self.assertEqual(response.json()["error"], "crm_unavailable")
