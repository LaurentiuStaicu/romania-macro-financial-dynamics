from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F21F2ExternalBridgeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f21_f2_external_bridge_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_instrument_identity_only(self) -> None:
        self.assertIn("F2 = F21 + F2M", self.contract["identity"])
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["external_F21_must_be_exact_F2_minus_F2M"])
        self.assertTrue(rules["F2_F21_F2M_dimensions_must_match"])

    def test_no_allocation_or_promotion(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_total_F2_promotion"])
        self.assertTrue(rules["no_holder_share_allocation"])
        self.assertTrue(rules["no_residual_allocation_across_holders"])

    def test_independent_controls_required(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["external_F21_sum_must_reconcile_to_published_W1_F21"])
        self.assertTrue(rules["holder_W1_F2_sum_must_reconcile_to_published_total_W1_F2"])
        self.assertTrue(rules["implied_domestic_F21_sum_must_reconcile_to_resident_F21_liability_control"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
