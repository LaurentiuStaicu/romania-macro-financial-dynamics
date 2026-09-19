from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GovernmentInterestBurdenReferenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "government_interest_burden_reference_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_official_concept_is_preregistered(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["institution"], "Eurostat")
        self.assertEqual(source["dataset"].split(" — ")[0], "gov_10q_ggnfa")
        self.assertEqual(source["geo"], "RO")
        self.assertEqual(source["sector"], "S13")
        self.assertEqual(source["seasonal_adjustment"], "NSA")
        self.assertEqual(source["na_item"], "D41PAY")
        self.assertEqual(set(source["units_to_probe"]), {"MIO_NAC", "PC_GDP"})

    def test_interest_expenditure_is_not_promoted_to_an_interest_rate(self) -> None:
        boundary = self.contract["concept_boundary"]
        self.assertTrue(boundary["D41PAY_is_ESA_interest_expenditure"])
        self.assertTrue(boundary["D41PAY_is_not_cash_interest_paid"])
        self.assertTrue(boundary["D41PAY_is_not_effective_interest_rate"])
        self.assertTrue(boundary["D41PAY_is_not_marginal_sovereign_yield"])
        self.assertTrue(boundary["D41PAY_does_not_identify_refinancing_share"])

    def test_behavioural_and_refinancing_boundaries_remain_closed(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["source_audit_only_no_behavioural_activation"])
        self.assertTrue(rules["no_government_refinancing_parameter_estimation"])
        self.assertTrue(rules["no_effective_rate_derivation_in_this_gate"])
        self.assertTrue(rules["no_cash_accrual_substitution"])
        self.assertFalse(rules["behavioural_closure_may_change"])

    def test_promotion_requires_retained_immutable_evidence(self) -> None:
        rule = self.contract["promotion_rule"]
        self.assertIn("workflow run", rule)
        self.assertIn("artifact identifier", rule)
        self.assertIn("SHA-256", rule)
        self.assertIn("does not activate any behavioural mechanism", rule)

    def test_2025_reference_window_is_explicit(self) -> None:
        required = self.contract["reference_mode"]["required_benchmark_periods"]
        self.assertEqual(
            required,
            ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"],
        )
        self.assertGreaterEqual(
            self.contract["reference_mode"][
                "minimum_observation_count_per_unit"
            ],
            40,
        )


if __name__ == "__main__":
    unittest.main()
