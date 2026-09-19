from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "calibration_validation"
    / "household_consumption_borrower_burden_alignment_review.json"
)


class HouseholdConsumptionBorrowerBurdenAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(P.read_text(encoding="utf-8"))

    def test_registered_target_is_aggregate_s1m(self) -> None:
        mechanism = self.review["registered_mechanism"]
        self.assertEqual(mechanism["reference_sector_code"], "S1M")
        self.assertIn("S14 + S15", mechanism["reference_sector_definition"])
        self.assertIn("aggregate sector consumption", mechanism["target_scope"])

    def test_housing_dsti_is_observed_but_population_misaligned(self) -> None:
        candidate = self.review["candidate_burden_measure"]
        self.assertEqual(candidate["instrument_scope"], "housing/mortgage loans")
        variants = {item["id"]: item for item in candidate["variants"]}
        self.assertEqual(
            variants["new_housing_loan_dsti"]["alignment_to_current_consumption_target"],
            "MISALIGNED_SUBPOPULATION_AND_ORIGINATION_FLOW",
        )
        self.assertEqual(
            variants["outstanding_housing_loan_dsti"]["alignment_to_current_consumption_target"],
            "CLOSER_TO_STOCK_BURDEN_BUT_STILL_SUBPOPULATION_MISALIGNED",
        )

    def test_no_population_bridge_is_currently_observed(self) -> None:
        comparison = self.review["source_comparison"]
        self.assertFalse(comparison["sector_coverage_match"])
        self.assertFalse(comparison["borrower_status_match"])
        self.assertFalse(comparison["debt_instrument_coverage_match"])
        self.assertFalse(comparison["target_population_bridge_observed"])
        self.assertFalse(comparison["subgroup_consumption_target_observed"])

    def test_rate_selection_cannot_repair_population_mismatch(self) -> None:
        rates = self.review["borrowing_rate_alignment"]
        self.assertFalse(rates["post_fit_rate_selection_allowed"])
        self.assertIn(
            "population mismatch unresolved",
            rates["household_house_purchase_rate"],
        )
        self.assertIn(
            "Not authorized",
            rates["synthetic_weighted_rate"],
        )

    def test_gate_keeps_estimation_and_closure_closed(self) -> None:
        disposition = self.review["disposition"]
        self.assertEqual(disposition["population_alignment_status"], "BLOCKED")
        self.assertTrue(disposition["housing_dsti_observed"])
        self.assertFalse(
            disposition["housing_dsti_directly_admissible_in_registered_aggregate_consumption_form"]
        )
        self.assertFalse(disposition["registered_full_form_source_admissible"])
        self.assertFalse(disposition["estimation_or_refit_allowed"])
        self.assertEqual(disposition["behavioural_closure"], "UNCHANGED_INACTIVE")

        hard = self.review["hard_rules"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_synthetic_population_bridge"])
        self.assertTrue(hard["no_target_redefinition_without_new_contract"])


if __name__ == "__main__":
    unittest.main()
