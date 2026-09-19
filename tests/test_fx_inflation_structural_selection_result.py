from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "calibration_validation"
            / name
        ).read_text(encoding="utf-8")
    )


class FxInflationStructuralSelectionResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = load(
            "fx_inflation_structural_selection_result.json"
        )
        self.gate = load(
            "fx_inflation_selection_execution_gate.json"
        )

    def test_failed_before_holdout_is_frozen(self) -> None:
        self.assertEqual(
            self.result["selection_verdict"],
            "FAIL_BEFORE_HOLDOUT",
        )
        self.assertFalse(self.result["passes_all_selection_gates"])
        self.assertFalse(self.result["final_evaluation_opened"])
        self.assertFalse(self.gate["final_evaluation_authorized"])
        self.assertTrue(self.gate["selection_execution_consumed"])
        self.assertFalse(self.gate["selection_execution_authorized"])

    def test_candidate_failed_incremental_predictive_gates(self) -> None:
        gates = self.result["gates"]
        self.assertFalse(gates["rmse_vs_external_price_baseline"])
        self.assertFalse(gates["rmse_vs_ar2_seasonal"])
        self.assertFalse(gates["mae_vs_external_price_baseline"])
        self.assertTrue(gates["rmse_vs_persistence"])
        self.assertTrue(gates["cumulative_0_3_sign_consistency"])
        self.assertTrue(gates["cumulative_0_12_sign_consistency"])
        self.assertTrue(gates["condition_number_path"])

    def test_failure_never_activates_causal_or_sd_feedback(self) -> None:
        self.assertFalse(self.result["causal_claim_allowed"])
        self.assertFalse(self.result["system_dynamics_activation"])
        self.assertFalse(self.result["behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
