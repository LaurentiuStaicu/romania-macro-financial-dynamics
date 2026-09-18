from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F4ExactComplementRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f4_exact_complement_rank_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_phase_b_cannot_materialize(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_materialization_in_phase_B"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_rank_uniqueness_is_exact(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["rank_and_nullity_must_use_exact_rational_coefficient_arithmetic"])
        self.assertTrue(rules["unique_cell_status_requires_zero_loading_on_every_nullspace_basis_vector"])

    def test_bnr_zero_is_stock_only_and_explicit(self) -> None:
        scenario = self.contract["stock_BNR_zero_scenario"]
        self.assertEqual(scenario["scope"], "stock only")
        self.assertIn("do not imply", scenario["prohibited_extension"].lower())
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["zero_BNR_aggregate_flow_must_not_create_bilateral_flow_zeros"])
        self.assertTrue(rules["BNR_asset_row_6_1_million_RON_must_not_be_allocated_without_counterpart_evidence"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
