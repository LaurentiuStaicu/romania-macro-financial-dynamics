from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "calibration_validation"
    / "credit_risk_mortgage_portfolio_source_screening.json"
)


class CreditRiskMortgagePortfolioSourceScreeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(P.read_text(encoding="utf-8"))

    def test_mortgage_npl_is_observed_in_official_publication_text(self) -> None:
        obs = {
            item["reference_period"]: item
            for item in self.review["official_mortgage_npl_evidence"]
        }
        self.assertEqual(obs["2023-09"]["mortgage_npl_percent"], 1.7)
        self.assertEqual(obs["2024-03"]["mortgage_npl_percent"], 1.7)
        self.assertEqual(obs["2024-03"]["consumer_npl_percent"], 5.9)
        self.assertFalse(obs["2024-03"]["chart_digitisation"])

    def test_dti_o_is_not_promoted_to_debt_service(self) -> None:
        dti = self.review["dti_at_origination_evidence"]
        self.assertEqual(
            dti["status"],
            "OBSERVED_BUT_NOT_DEBT_SERVICE_BURDEN",
        )
        self.assertEqual(
            dti["mortgage_exposure_value_coverage_percent_reported_for_indicator"],
            25,
        )
        self.assertFalse(dti["substitution_for_dsti_allowed"])

    def test_mortgage_npl_and_dsti_are_not_assumed_jointly_reconciled(self) -> None:
        alignment = self.review["portfolio_alignment_assessment"]
        self.assertTrue(
            alignment["mortgage_npl_and_outstanding_dsti_same_broad_instrument_family"]
        )
        self.assertFalse(alignment["exact_reporting_population_match_demonstrated"])
        self.assertFalse(alignment["exact_bank_coverage_match_demonstrated"])
        self.assertFalse(alignment["exact_denominator_weighting_match_demonstrated"])
        self.assertFalse(alignment["exact_machine_readable_joint_history_retained"])

    def test_future_sector_target_is_not_selected_or_estimated(self) -> None:
        registered = self.review["registered_mechanism_boundary"]
        disposition = self.review["disposition"]
        hard = self.review["hard_rules"]
        self.assertFalse(registered["target_change_authorized"])
        self.assertEqual(self.review["future_candidate_gate"]["status"], "NOT_OPEN")
        self.assertFalse(disposition["registered_full_form_source_admissible"])
        self.assertFalse(disposition["estimation_or_refit_allowed"])
        self.assertTrue(hard["no_target_switch"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertEqual(
            disposition["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
