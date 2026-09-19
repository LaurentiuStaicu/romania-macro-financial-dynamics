from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_semantic_mapping_audit.json"
)


class BNRBLSMissingRoundSemanticMappingResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    def test_exact_three_rounds_pass(self) -> None:
        self.assertEqual(
            self.audit["status"],
            "PASS_MISSING_ROUND_SEMANTIC_COORDINATE_MAPPING_WITH_EXPLICIT_ROUND_IDENTITY_BRIDGES",
        )
        self.assertEqual(
            self.audit["passed_rounds"],
            ["2023-Q2", "2023-Q3", "2024-Q2"],
        )
        self.assertTrue(
            all(item["all_six_observables_passed"] for item in self.audit["results"])
        )

    def test_exact_values_are_retained(self) -> None:
        rows = {
            item["target_quarter"]: item["row"]
            for item in self.audit["results"]
        }
        self.assertEqual(
            [
                rows["2023-Q2"]["nfc_credit_standards"],
                rows["2023-Q2"]["nfc_loan_demand"],
                rows["2023-Q2"]["household_mortgage_credit_standards"],
                rows["2023-Q2"]["household_consumer_credit_standards"],
                rows["2023-Q2"]["household_mortgage_loan_demand"],
                rows["2023-Q2"]["household_consumer_loan_demand"],
            ],
            [15.54, 16.49, -4.28, 3.64, -23.36, 50.76],
        )
        self.assertEqual(
            [
                rows["2023-Q3"]["nfc_credit_standards"],
                rows["2023-Q3"]["nfc_loan_demand"],
                rows["2023-Q3"]["household_mortgage_credit_standards"],
                rows["2023-Q3"]["household_consumer_credit_standards"],
                rows["2023-Q3"]["household_mortgage_loan_demand"],
                rows["2023-Q3"]["household_consumer_loan_demand"],
            ],
            [0.0, -29.52, -38.15, 1.36, 34.62, 27.04],
        )
        self.assertEqual(
            [
                rows["2024-Q2"]["nfc_credit_standards"],
                rows["2024-Q2"]["nfc_loan_demand"],
                rows["2024-Q2"]["household_mortgage_credit_standards"],
                rows["2024-Q2"]["household_consumer_credit_standards"],
                rows["2024-Q2"]["household_mortgage_loan_demand"],
                rows["2024-Q2"]["household_consumer_loan_demand"],
            ],
            [0.0, 20.36, 12.89, -14.16, 13.34, 70.06],
        )

    def test_round_identity_bridges_preserve_raw_headers(self) -> None:
        by_quarter = {
            item["target_quarter"]: item["round_identity"]
            for item in self.audit["results"]
        }
        self.assertEqual(by_quarter["2023-Q2"]["raw_workbook_header"], "31/03/2023")
        self.assertEqual(
            by_quarter["2023-Q2"]["authority"],
            "OFFICIAL_BNR_PUBLICATION_QUARTER",
        )
        self.assertFalse(
            by_quarter["2023-Q2"]["silent_date_normalisation_performed"]
        )
        self.assertEqual(by_quarter["2024-Q2"]["raw_workbook_header"], "31/06/2024")
        self.assertEqual(
            by_quarter["2024-Q2"]["authority"],
            "OFFICIAL_BNR_PUBLICATION_QUARTER",
        )
        self.assertFalse(
            by_quarter["2024-Q2"]["silent_date_normalisation_performed"]
        )
        self.assertEqual(
            by_quarter["2023-Q3"]["authority"],
            "WORKBOOK_COMPANIES_A1",
        )

    def test_review_has_no_model_facing_side_effects(self) -> None:
        self.assertFalse(self.audit["canonical_panel_modified"])
        self.assertFalse(self.audit["interpolation_performed"])
        self.assertFalse(self.audit["synthetic_quarters_created"])
        self.assertFalse(self.audit["parameter_estimation_performed"])
        self.assertFalse(self.audit["model_selection_performed"])
        self.assertFalse(self.audit["holdout_opened"])
        self.assertFalse(self.audit["system_dynamics_activation"])
        self.assertFalse(self.audit["behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
