from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_household_dsti_level_publication_boundary_review.json"
)


class BNRHouseholdDSTILevelPublicationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(P.read_text(encoding="utf-8"))

    def test_semantic_scope_is_housing_loans_not_macro_household_dsr(self) -> None:
        identity = self.review["semantic_identity"]
        self.assertEqual(identity["instrument_scope"], "housing / mortgage loans")
        self.assertIn(
            "BIS household-sector debt service ratio",
            identity["not_equivalent_to"],
        )
        self.assertIn(
            "BNR BLS P0303/P1103 net percentages about changes in maximum DSTI lending terms",
            identity["not_equivalent_to"],
        )

    def test_direct_text_observations_are_retained_without_digitisation(self) -> None:
        rows = {
            item["quarter"]: item
            for item in self.review["explicit_publication_text_observations"]
        }
        self.assertEqual(rows["2024-Q1"]["new_housing_loans_dsti_percent"], 34.0)
        self.assertEqual(rows["2024-Q2"]["new_housing_loans_dsti_percent"], 34.6)
        self.assertEqual(rows["2024-Q3"]["outstanding_housing_loans_dsti_percent"], 40.9)
        self.assertEqual(rows["2025-Q2"]["outstanding_housing_loans_dsti_percent"], 42.0)
        for row in rows.values():
            self.assertEqual(row["extraction"], "DIRECT_REPORT_TEXT")
            self.assertFalse(row["chart_digitisation"])

    def test_chart_history_is_not_promoted_to_machine_readable_series(self) -> None:
        continuity = self.review["continuity_evidence"]
        machine = self.review["machine_readable_boundary"]
        self.assertTrue(continuity["chart_history_visible_but_not_digitised"])
        self.assertFalse(machine["exact_longitudinal_level_history_retained"])
        self.assertIn("does not authorize chart digitisation", continuity["interpretation"])

    def test_observed_alternative_does_not_open_estimation_or_closure(self) -> None:
        boundary = self.review["modelling_boundary"]
        self.assertTrue(boundary["alternative_borrower_burden_candidate_observed"])
        self.assertFalse(boundary["registered_macro_dsr_term_identified"])
        self.assertFalse(boundary["household_consumption_estimation_authorized"])
        self.assertFalse(boundary["credit_risk_estimation_authorized"])
        self.assertFalse(boundary["system_dynamics_activation"])
        self.assertFalse(boundary["behavioural_closure_change"])

    def test_prohibited_shortcuts_keep_new_and_outstanding_dstis_separate(self) -> None:
        prohibited = " ".join(self.review["prohibited_shortcuts"]).lower()
        self.assertIn("mix new-loan and outstanding-loan dsti", prohibited)
        self.assertIn("generalise housing-loan dsti", prohibited)
        self.assertIn("digitise chart points", prohibited)


if __name__ == "__main__":
    unittest.main()
