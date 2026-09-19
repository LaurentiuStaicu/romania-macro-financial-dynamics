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


class FiscalReactionAnnualSelectionResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = load(
            "fiscal_reaction_annual_structural_selection_result.json"
        )
        self.gate = load(
            "fiscal_reaction_annual_selection_execution_gate.json"
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

    def test_candidate_failed_persistence_and_output_gap_domain_gates(self) -> None:
        self.assertFalse(self.result["gates"]["rmse_vs_persistence"])
        self.assertTrue(
            self.result[
                "candidate_rmse_improvement_vs_baselines"
            ]["persistence"] < 0
        )
        self.assertEqual(
            self.result[
                "candidate_parameter_domain_fractions"
            ]["beta_y"],
            0,
        )
        self.assertFalse(self.result["gates"]["all_parameter_domains"])

    def test_failure_never_activates_fiscal_feedback(self) -> None:
        self.assertFalse(self.result["causal_claim_allowed"])
        self.assertFalse(self.result["debt_sustainability_claim_allowed"])
        self.assertFalse(self.result["system_dynamics_activation"])
        self.assertFalse(self.result["behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
