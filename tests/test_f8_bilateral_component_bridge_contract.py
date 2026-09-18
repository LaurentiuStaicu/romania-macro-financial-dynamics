from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F8BilateralComponentBridgeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f8_bilateral_component_bridge_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_total_requires_both_components(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["bilateral_F8_requires_both_F81_and_F89"])
        self.assertTrue(rules["F81_must_not_substitute_for_F8"])
        self.assertTrue(rules["F89_must_not_substitute_for_F8"])

    def test_no_synthetic_completion(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])
        self.assertTrue(rules["component_missingness_must_remain_explicit"])

    def test_orientation_conflicts_block(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["dual_W2_orientations_must_be_probed_for_each_component"])
        self.assertTrue(rules["component_orientation_conflict_blocks_component"])
        self.assertTrue(rules["component_conflict_blocks_total_F8_cell"])

    def test_rank_and_materialization_are_later_gates(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_materialization_in_phase_B"])
        self.assertTrue(rules["rank_must_be_computed_in_a_later_gate_before_materialization"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
