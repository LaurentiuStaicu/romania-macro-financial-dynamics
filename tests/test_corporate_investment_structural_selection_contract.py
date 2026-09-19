from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"corporate_investment_structural_selection_contract.json"

class CorporateInvestmentStructuralSelectionContractTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(P.read_text(encoding="utf-8"))

    def test_exact_panel_and_windows_are_frozen(self):
        p=self.c["prerequisite_measurement_panel"]
        self.assertEqual(p["rows"],34)
        self.assertEqual(p["csv_sha256"],"d8d3765fe9e83bd29620de1d02e914626a5f5e1b4071e005ff138b55f127ba69")
        w=self.c["windows"]
        self.assertEqual(w["initial_calibration"],"2018-Q1..2021-Q4")
        self.assertEqual(w["structural_selection"],"2022-Q1..2023-Q4")
        self.assertEqual(w["final_evaluation"],"2024-Q1..2026-Q1")

    def test_all_candidate_drivers_are_lagged(self):
        for key,item in self.c["predictors"].items():
            self.assertEqual(item["lag_quarters"],1,key)
        self.assertFalse(self.c["information_timing"]["same_quarter_predictors_allowed"])

    def test_hierarchical_candidate_design_is_frozen(self):
        by={m["id"]:m for m in self.c["candidate_models"]}
        self.assertEqual(by["core_lagged_drivers_ar"]["estimated_parameters"],4)
        self.assertEqual(by["support_augmented_lagged_drivers_ar"]["estimated_parameters"],5)
        self.assertTrue(self.c["augmented_extension_gates"]["evaluated_only_if_primary_passes"])

    def test_contract_does_not_authorize_estimation_or_activation(self):
        self.assertFalse(self.c["estimation_authorization"]["authorized_by_this_contract"])
        h=self.c["hard_rules"]
        self.assertTrue(h["no_alternative_lag_search"])
        self.assertTrue(h["no_holdout_peeking_before_primary_selection_pass"])
        self.assertTrue(h["no_causal_claim"])
        self.assertTrue(h["no_system_dynamics_activation"])
        self.assertTrue(h["no_behavioural_closure_change"])

if __name__=="__main__":
    unittest.main()
