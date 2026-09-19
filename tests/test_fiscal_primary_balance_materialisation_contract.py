from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_fiscal_primary_balance_materialisation import (
    normalise_quarter,
    parse_eurostat,
    primary_balance,
)

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class FiscalPrimaryBalanceMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/calibration_validation/"
            "fiscal_primary_balance_materialisation_contract.json"
        )

    def test_matched_source_boundary_is_nsa_percent_gdp(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["dataset"], "gov_10q_ggnfa")
        self.assertEqual(source["geo"], "RO")
        self.assertEqual(source["sector"], "S13")
        self.assertEqual(source["seasonal_adjustment"], "NSA")
        self.assertEqual(source["unit"], "PC_GDP")
        self.assertEqual(
            source["items"]["overall_balance"]["na_item"],
            "B9",
        )
        self.assertEqual(
            source["items"]["interest_expenditure"]["na_item"],
            "D41PAY",
        )

    def test_primary_balance_identity_preserves_sign(self) -> None:
        self.assertAlmostEqual(primary_balance(-8.0, 2.5), -5.5)
        self.assertAlmostEqual(primary_balance(1.0, 2.0), 3.0)
        identity = self.contract["measurement_identity"]
        self.assertTrue(identity["same_boundary_required"])
        self.assertTrue(identity["same_dataset_update_required"])
        self.assertTrue(identity["no_sign_flip"])

    def test_eurostat_parser_is_offline_and_exact(self) -> None:
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
            "value": {"0": -7.0, "1": -6.0},
            "updated": "2026-07-21T11:00:00+0200",
            "label": "test",
        }
        observations, metadata = parse_eurostat(
            json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(
            observations,
            {"2025-Q1": -7.0, "2025-Q2": -6.0},
        )
        self.assertEqual(
            metadata["updated"],
            "2026-07-21T11:00:00+0200",
        )
        self.assertEqual(normalise_quarter("2025-Q3"), "2025-Q3")

    def test_materialisation_does_not_open_reaction_function(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_output_gap_construction"])
        self.assertTrue(rules["no_debt_gap_construction"])
        self.assertTrue(rules["no_regime_inference"])
        self.assertTrue(rules["no_parameter_estimation"])
        self.assertFalse(
            self.contract["result_effect"]["calibration_cycle_open"]
        )
        self.assertEqual(
            self.contract["result_effect"]["mechanism_classification"],
            "DEFERRED",
        )


if __name__ == "__main__":
    unittest.main()
