from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_structural_selection_contract.json"
)


class SovereignYieldStructuralSelectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_does_not_authorize_estimation_or_activation(self) -> None:
        self.assertFalse(
            self.contract["estimation_authorization"]["authorized_by_this_contract"]
        )
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_holdout_peeking_before_selection_pass"])
        self.assertTrue(rules["no_system_dynamics_activation"])
        self.assertTrue(rules["no_behavioural_closure_change"])

    def test_exact_retained_source_vintage_is_required(self) -> None:
        source = self.contract["prerequisite_source_vintage"]
        self.assertEqual(source["rows"], 84)
        self.assertEqual(source["first_period"], "2005-Q2")
        self.assertEqual(source["last_period"], "2026-Q1")
        self.assertTrue(source["exact_raw_reproducibility_required"])

    def test_fiscal_inputs_are_lagged_and_b9_sign_is_not_flipped(self) -> None:
        timing = self.contract["information_timing"]
        self.assertIn("t-1", timing["fiscal_controls"])
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_same_quarter_fiscal_controls"])
        self.assertTrue(rules["no_sign_flip_of_b9_source"])

    def test_policy_rate_is_excluded_for_provenance_reason(self) -> None:
        decision = self.contract["domestic_policy_rate_decision"]
        self.assertFalse(decision["included_in_first_cycle"])
        self.assertIn("raw", decision["reason"].lower())
        self.assertTrue(self.contract["hard_rules"]["no_policy_rate_added_inside_cycle"])

    def test_candidate_must_beat_common_market_baseline(self) -> None:
        baseline_ids = {
            item["id"] for item in self.contract["baseline_models"]
        }
        candidate_ids = {
            item["id"] for item in self.contract["candidate_models"]
        }
        self.assertEqual(
            baseline_ids,
            {"persistence", "common_market_ar"},
        )
        self.assertEqual(
            candidate_ids,
            {"fiscal_augmented_common_market_ar"},
        )
        gates = self.contract["structural_selection_gates"]
        self.assertGreater(
            gates["candidate_rmse_improvement_vs_common_market_ar_fraction_min"],
            0,
        )

    def test_windows_and_holdout_gate_are_frozen(self) -> None:
        windows = self.contract["windows"]
        self.assertEqual(windows["initial_calibration"], "2005-Q3..2016-Q4")
        self.assertEqual(windows["structural_selection"], "2017-Q1..2022-Q4")
        self.assertEqual(windows["final_evaluation"], "2023-Q1..2026-Q1")
        self.assertTrue(self.contract["hard_rules"]["no_alternative_lag_search"])
        self.assertIn(
            "only if",
            windows["final_evaluation_open_rule"].lower(),
        )


if __name__ == "__main__":
    unittest.main()
