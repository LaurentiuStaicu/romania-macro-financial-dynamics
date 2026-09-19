from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_structural_selection_result.json"
)


class SovereignYieldStructuralSelectionResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_failed_before_holdout_is_frozen(self) -> None:
        self.assertEqual(
            self.result["selection_verdict"],
            "FAIL_BEFORE_HOLDOUT",
        )
        self.assertFalse(self.result["passes_all_selection_gates"])
        self.assertFalse(self.result["final_evaluation_opened"])

    def test_candidate_underperforms_both_preregistered_baselines(self) -> None:
        improvements = self.result["candidate_rmse_improvement_vs_baselines"]
        self.assertLess(improvements["persistence"], 0.0)
        self.assertLess(improvements["common_market_ar"], 0.0)
        self.assertFalse(self.result["gates"]["rmse_vs_persistence"])
        self.assertFalse(self.result["gates"]["rmse_vs_common_market_ar"])

    def test_fiscal_sign_consistency_gates_failed(self) -> None:
        fractions = self.result["candidate_parameter_domain_fractions"]
        self.assertLess(fractions["beta_d"], 0.75)
        self.assertLess(fractions["beta_b"], 0.75)
        self.assertFalse(
            self.result["gates"]["fiscal_beta_d_sign_consistency"]
        )
        self.assertFalse(
            self.result["gates"]["fiscal_beta_b_sign_consistency"]
        )

    def test_failed_selection_never_activates_behavioural_feedback(self) -> None:
        self.assertFalse(self.result["causal_claim_allowed"])
        self.assertFalse(self.result["system_dynamics_activation"])
        self.assertFalse(self.result["behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
