from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class HouseholdConsumptionSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/calibration_validation/"
            "household_consumption_source_boundary_review.json"
        )

    def test_core_qsa_series_are_exact_but_registered_form_is_blocked(self) -> None:
        sources = self.review["exact_primary_sources"]
        self.assertEqual(
            sources["household_final_consumption"]["series_key"],
            "QSA.Q.N.RO.W0.S1M.S1.N.D.P3._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertEqual(
            sources["household_gross_disposable_income"]["series_key"],
            "QSA.Q.N.RO.W0.S1M.S1._Z.B.B6G._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertFalse(
            self.review["source_admissibility"]["registered_full_form_admissible"]
        )
        self.assertFalse(
            self.review["disposition"]["estimation_or_refit_allowed"]
        )

    def test_debt_to_income_and_prudential_caps_are_not_dsr(self) -> None:
        boundary = self.review["debt_service_boundary"]
        proxy = boundary["available_non_equivalent_Romania_measure"]
        self.assertEqual(proxy["status"], "OBSERVED_BUT_NOT_DSR")
        self.assertIn("stock-to-income", proxy["reason"])
        self.assertIn(
            "not an observed aggregate household DSR history",
            boundary["historical_microprudential_thresholds"]["interpretation"],
        )
        prohibited = " ".join(self.review["prohibited_shortcuts"]).lower()
        self.assertIn("loans-to-disposable-income", prohibited)
        self.assertIn("regulatory debt-service cap", prohibited)

    def test_bnr_housing_dsti_alternative_is_observed_but_narrower(self) -> None:
        alt = self.review["debt_service_boundary"]["bnr_dsti_alternative"]
        self.assertEqual(
            alt["status"],
            "OFFICIAL_HOUSING_LOAN_DSTI_LEVEL_OBSERVATIONS_CONFIRMED_MACHINE_READABLE_LONGITUDINAL_HISTORY_NOT_RETAINED",
        )
        self.assertIn("housing-loan", alt["concept"].lower())
        self.assertIn("must remain separate", alt["semantic_limit"])
        coverage = alt["publication_text_coverage"]
        self.assertEqual(coverage["directly_observed_quarters"], 10)
        self.assertEqual(coverage["missing_quarters"], [])
        self.assertEqual(coverage["coverage_fraction"], 1.0)
        self.assertEqual(
            alt["publication_level_boundary_review"],
            "model/calibration_validation/bnr_household_dsti_level_publication_boundary_review.json",
        )
        self.assertFalse(
            self.review["source_admissibility"]["registered_full_form_admissible"]
        )

    def test_housing_dsti_cannot_enter_aggregate_s1m_without_population_bridge(self) -> None:
        admissibility = self.review["source_admissibility"]
        self.assertEqual(admissibility["population_alignment_status"], "BLOCKED")
        self.assertFalse(
            admissibility["housing_dsti_directly_admissible_as_registered_debt_service_ratio"]
        )
        self.assertEqual(
            self.review["borrower_burden_population_alignment_review"],
            "model/calibration_validation/household_consumption_borrower_burden_alignment_review.json",
        )

    def test_borrowing_rate_family_cannot_be_selected_post_hoc(self) -> None:
        rate = self.review["borrowing_rate_boundary"]
        keys = {item["series_key"] for item in rate["examples"]}
        self.assertIn("MIR.M.RO.B.A2B.A.C.A.2250.RON.N", keys)
        self.assertIn("MIR.M.RO.B.A2C.A.R.A.2250.RON.P", keys)
        self.assertIn("after inspecting", rate["rule"])

    def test_missing_dsr_does_not_authorize_nested_form(self) -> None:
        admissibility = self.review["source_admissibility"]
        self.assertFalse(admissibility["nested_form_automatically_authorized"])
        self.assertIn(
            "new preregistered candidate-family contract",
            admissibility["nested_form_rule"],
        )
        self.assertEqual(
            self.review["disposition"]["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
