from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F8AggregateRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f8_aggregate_rank_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_rank_rule(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["rank_and_nullity_must_use_exact_rational_coefficient_arithmetic"])
        self.assertTrue(rules["unique_cell_status_requires_zero_loading_on_every_nullspace_basis_vector"])

    def test_aggregate_equations_do_not_become_allocations(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_unconditional_bilateral_value_from_aggregate_equations_unless_rank_unique"])
        self.assertTrue(rules["no_synthetic_allocation"])
        self.assertTrue(rules["no_materialization_in_phase_C"])

    def test_bnr_scenario_is_stock_only_and_not_promoted(self) -> None:
        scenario = self.contract["stock_BNR_zero_scenario"]
        self.assertEqual(scenario["scope"], "stock only")
        self.assertFalse(scenario["promotion"])
        self.assertTrue(self.contract["hard_rules"]["conditional_BNR_zero_stock_cells_must_not_be_promoted"])
        self.assertTrue(self.contract["hard_rules"]["zero_BNR_aggregate_flow_must_not_create_bilateral_flow_zeros"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
