from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"debt_service_source_screening.json"

class DebtServiceSourceScreeningTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_romania_is_not_in_bis_sectoral_dsr_breakdown(self):
        bis=self.r["bis_sectoral_dsr"]
        self.assertFalse(bis["romania_in_sectoral_breakdown"])
        self.assertEqual(len(bis["documented_17_country_sectoral_breakdown"]),17)
        self.assertNotIn("Romania",bis["documented_17_country_sectoral_breakdown"])

    def test_bnr_dsti_is_kept_semantically_separate(self):
        bnr=self.r["bnr_household_dsti"]
        self.assertFalse(bnr["exact_machine_readable_history_retained"])
        self.assertTrue(any("not the BIS macro" in x for x in bnr["semantic_boundary"]))
        self.assertTrue(any("New-loan DSTI" in x for x in bnr["semantic_boundary"]))

    def test_bnr_housing_dsti_levels_are_observed_but_not_macro_dsr(self):
        bnr=self.r["bnr_household_dsti"]
        self.assertTrue(bnr["official_quarterly_level_observations_confirmed"])
        self.assertEqual(
            bnr["publication_level_boundary_review"],
            "model/calibration_validation/bnr_household_dsti_level_publication_boundary_review.json",
        )
        obs={item["quarter"]:item for item in bnr["confirmed_publication_text_observations"]}
        self.assertEqual(obs["2024-Q2"]["new_housing_loans_dsti_percent"],34.6)
        self.assertEqual(obs["2025-Q2"]["outstanding_housing_loans_dsti_percent"],42.0)
        self.assertFalse(bnr["exact_machine_readable_history_retained"])

    def test_screening_does_not_authorize_estimation(self):
        d=self.r["dispositions"]
        self.assertFalse(d["household_consumption_response"]["estimation_authorized"])
        self.assertFalse(d["credit_risk_npl_response"]["estimation_authorized"])
        self.assertFalse(self.r["global_effect"]["active_calibration_cycle_open"])
        self.assertFalse(self.r["global_effect"]["behavioural_closure_change"])

if __name__=="__main__":
    unittest.main()
