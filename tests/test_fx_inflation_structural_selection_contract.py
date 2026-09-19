from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FxInflationStructuralSelectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fx_inflation_structural_selection_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_contract_does_not_authorize_estimation_or_holdout(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_holdout_peeking_before_selection_pass"])
        self.assertTrue(hard["no_regularization_rescue"])
        self.assertTrue(hard["no_causal_claim"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])

    def test_candidate_must_beat_external_price_baseline(self) -> None:
        gates = self.contract["structural_selection_gates"]
        self.assertGreater(
            gates[
                "candidate_rmse_improvement_vs_external_price_baseline_fraction_min"
            ],
            0,
        )
        self.assertEqual(
            gates[
                "candidate_mae_may_not_exceed_external_price_baseline_by_more_than_fraction"
            ],
            0,
        )
        self.assertTrue(gates["all_sign_consistency_gates_must_pass"])

    def test_sign_gate_is_cumulative_not_each_block(self) -> None:
        sign = self.contract["sign_consistency_gates"]
        self.assertEqual(
            sign["cumulative_0_12"],
            "gamma0 + gamma13 + gamma46 + gamma712",
        )
        self.assertFalse(sign["individual_block_signs_are_hard_gates"])
        self.assertEqual(
            sign["cumulative_0_12_nonnegative_fraction_min"],
            0.70,
        )

    def test_selection_and_final_windows_are_separate(self) -> None:
        windows = self.contract["windows"]
        self.assertEqual(windows["structural_selection"], "2015-01..2020-12")
        self.assertEqual(windows["final_evaluation"], "2021-01..2026-06")
        self.assertEqual(
            windows["minimum_training_observations_per_origin"],
            113,
        )


if __name__ == "__main__":
    unittest.main()
