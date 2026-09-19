from __future__ import annotations

import unittest

from scripts.audit_eurostat_sectoral_financial_positions_counterpart_probe import (
    category_codes,
    inspect_json_stat,
    non_null_observation_count,
)


class EurostatSectoralFinancialPositionsCounterpartProbeLogicTests(unittest.TestCase):
    def test_category_codes_preserve_declared_order(self) -> None:
        self.assertEqual(
            category_codes(
                {
                    "category": {
                        "index": {
                            "S11": 1,
                            "S1": 0,
                            "S12": 2,
                        }
                    }
                }
            ),
            ["S1", "S11", "S12"],
        )
        self.assertEqual(
            category_codes({"category": {"index": ["RO", "DE"]}}),
            ["RO", "DE"],
        )

    def test_non_null_observation_count_supports_sparse_and_dense_values(self) -> None:
        self.assertEqual(
            non_null_observation_count({"0": 1.0, "2": None, "4": 3.0}),
            2,
        )
        self.assertEqual(
            non_null_observation_count([1.0, None, 2.0]),
            2,
        )

    def test_json_stat_inspection_freezes_schema_without_mapping(self) -> None:
        payload = {
            "id": ["unit", "sector", "sectpart", "geo", "time"],
            "size": [1, 2, 2, 1, 2],
            "dimension": {
                "unit": {"category": {"index": {"MIO_NAC": 0}}},
                "sector": {"category": {"index": {"S1": 0, "S11": 1}}},
                "sectpart": {"category": {"index": {"S1": 0, "S2": 1}}},
                "geo": {"category": {"index": {"RO": 0}}},
                "time": {
                    "category": {
                        "index": {
                            "2025-Q1": 0,
                            "2025-Q2": 1,
                        }
                    }
                },
            },
            "value": {"0": 100.0, "3": 200.0},
        }
        summary = inspect_json_stat(payload)
        self.assertEqual(
            summary["dimension_ids"],
            ["unit", "sector", "sectpart", "geo", "time"],
        )
        self.assertEqual(summary["geo_codes"], ["RO"])
        self.assertEqual(
            summary["time_codes"],
            ["2025-Q1", "2025-Q2"],
        )
        self.assertEqual(summary["non_null_observation_count"], 2)
        self.assertEqual(
            summary["category_codes_by_dimension"]["sectpart"],
            ["S1", "S2"],
        )

    def test_json_stat_missing_dimension_metadata_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            inspect_json_stat(
                {
                    "id": ["geo", "time"],
                    "size": [1, 1],
                    "dimension": {
                        "geo": {"category": {"index": {"RO": 0}}},
                    },
                    "value": {"0": 1.0},
                }
            )


if __name__ == "__main__":
    unittest.main()
