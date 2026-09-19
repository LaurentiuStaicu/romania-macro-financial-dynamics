from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "model" / "calibration_validation" / "bnr_bls_publication_text_bridge.json"
CONTRACT = ROOT / "model" / "calibration_validation" / "bnr_bls_publication_text_bridge_contract.json"
PANEL = ROOT / "data" / "processed" / "bnr_bls_realised_rounds.csv"


class BNRBLSPublicationTextBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        with PANEL.open("r", encoding="utf-8", newline="") as handle:
            self.panel = list(csv.DictReader(handle))

    def test_bridge_does_not_fill_canonical_panel(self) -> None:
        self.assertFalse(self.bridge["canonical_panel_modified"])
        self.assertFalse(
            self.contract["precision_rule"]["canonical_panel_substitution_allowed"]
        )
        self.assertTrue(self.contract["hard_rules"]["no_canonical_panel_overwrite"])
        self.assertEqual(len(self.panel), 8)
        self.assertEqual(
            [row["quarter"] for row in self.panel],
            [
                "2022-Q4",
                "2023-Q1",
                "2023-Q4",
                "2024-Q1",
                "2024-Q3",
                "2024-Q4",
                "2025-Q1",
                "2025-Q3",
            ],
        )

    def test_three_rounds_have_complete_publication_text_evidence(self) -> None:
        by_quarter = {
            item["quarter"]: item for item in self.bridge["source_rounds"]
        }
        for quarter in ("2023-Q3", "2024-Q2", "2025-Q2"):
            self.assertEqual(by_quarter[quarter]["exact_text_value_count"], 6)
            self.assertEqual(by_quarter[quarter]["unresolved_text_value_count"], 0)

        self.assertEqual(
            by_quarter["2023-Q3"]["evidence"]["household_mortgage_credit_standards"]["value"],
            -38.2,
        )
        self.assertEqual(
            by_quarter["2024-Q2"]["evidence"]["household_consumer_credit_standards"]["value"],
            -14.2,
        )
        self.assertEqual(
            by_quarter["2025-Q2"]["evidence"]["household_consumer_loan_demand"]["value"],
            37.0,
        )

    def test_2023_q2_household_values_remain_noncanonical_or_unresolved(self) -> None:
        q2 = next(
            item for item in self.bridge["source_rounds"]
            if item["quarter"] == "2023-Q2"
        )
        self.assertEqual(q2["exact_text_value_count"], 2)
        self.assertEqual(q2["unresolved_text_value_count"], 4)
        for key in (
            "household_mortgage_credit_standards",
            "household_consumer_credit_standards",
            "household_mortgage_loan_demand",
            "household_consumer_loan_demand",
        ):
            self.assertIsNone(q2["evidence"][key]["value"])
        consumer = q2["evidence"]["household_consumer_loan_demand"]
        self.assertEqual(consumer["rounded_share_balance_candidate"], 50.8)
        self.assertFalse(consumer["canonical_candidate_allowed"])

    def test_precision_and_modelling_boundaries_remain_closed(self) -> None:
        boundary = self.bridge["methodology_boundary"]
        self.assertFalse(boundary["chart_digitisation_performed"])
        self.assertFalse(boundary["ocr_performed"])
        self.assertFalse(boundary["interpolation_performed"])
        self.assertFalse(boundary["canonical_panel_substitution_performed"])
        self.assertFalse(boundary["parameter_estimation_performed"])
        self.assertFalse(boundary["model_selection_performed"])
        self.assertFalse(boundary["behavioural_closure_change"])

        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])

    def test_dsti_level_discovery_is_kept_separate(self) -> None:
        q2_2025 = next(
            item for item in self.bridge["source_rounds"]
            if item["quarter"] == "2025-Q2"
        )
        dsti = q2_2025["related_household_dsti_level_evidence"]
        self.assertEqual(
            dsti["status"],
            "SEPARATE_SOURCE_DISCOVERY_NOT_USED_IN_THIS_BRIDGE",
        )
        self.assertEqual(dsti["new_loans_percent"], 37.0)
        self.assertEqual(dsti["outstanding_loans_percent"], 42.0)


if __name__ == "__main__":
    unittest.main()
