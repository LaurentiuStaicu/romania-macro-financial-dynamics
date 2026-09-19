from __future__ import annotations

import json
import unittest

from scripts.audit_sovereign_yield_quarterly_materialisation import (
    complete_quarterly_monthly_mean,
    equal_weight_daily_to_quarter,
    normalize_quarter,
    parse_ecb_csv,
    parse_eurostat_json,
    quarter_from_month,
)


class SovereignYieldMaterialiserLogicTests(unittest.TestCase):
    def test_quarter_normalization_accepts_both_provider_spellings(self) -> None:
        self.assertEqual(normalize_quarter("2025Q1"), "2025-Q1")
        self.assertEqual(normalize_quarter("2025-Q1"), "2025-Q1")
        with self.assertRaises(ValueError):
            normalize_quarter("2025--Q1")

    def test_month_to_quarter_mapping(self) -> None:
        self.assertEqual(quarter_from_month("2025-01"), "2025-Q1")
        self.assertEqual(quarter_from_month("2025-06"), "2025-Q2")
        self.assertEqual(quarter_from_month("2025-12"), "2025-Q4")

    def test_monthly_quarter_requires_all_three_months(self) -> None:
        rows = [
            ("2025-01", 1.0),
            ("2025-02", 2.0),
            ("2025-03", 3.0),
            ("2025-04", 10.0),
            ("2025-06", 30.0),
        ]
        result = complete_quarterly_monthly_mean(rows)
        self.assertEqual(result, {"2025-Q1": 2.0})

    def test_daily_ciss_equal_weights_months_not_business_days(self) -> None:
        rows = [
            ("2025-01-02", 0.0),
            ("2025-01-03", 2.0),
            ("2025-02-03", 10.0),
            ("2025-03-03", 20.0),
        ]
        result = equal_weight_daily_to_quarter(rows)
        self.assertEqual(result["2025-Q1"], (1.0 + 10.0 + 20.0) / 3.0)

    def test_ecb_csv_parser_requires_time_and_value(self) -> None:
        body = (
            b"KEY,TIME_PERIOD,OBS_VALUE\n"
            b"IRS.M.RO.L.L40.CI.0000.RON.N.Z,2025-01,7.25\n"
        )
        self.assertEqual(parse_ecb_csv(body), [("2025-01", 7.25)])

    def test_eurostat_json_parser_keeps_b9_sign(self) -> None:
        payload = {
            "class": "dataset",
            "id": ["freq", "unit", "s_adj", "sector", "na_item", "geo", "time"],
            "size": [1, 1, 1, 1, 1, 1, 2],
            "dimension": {
                "time": {
                    "category": {
                        "index": {"2025Q1": 0, "2025Q2": 1}
                    }
                }
            },
            "value": {"0": -7.5, "1": -6.0},
            "updated": "2026-01-01T00:00:00Z",
            "label": "test",
        }
        rows, meta = parse_eurostat_json(
            json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(
            rows,
            [("2025-Q1", -7.5), ("2025-Q2", -6.0)],
        )
        self.assertEqual(meta["updated"], "2026-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
