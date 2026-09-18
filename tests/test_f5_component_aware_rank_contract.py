from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F5ComponentAwareRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f5_component_aware_rank_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_rank_uses_component_variables(self) -> None:
        self.assertEqual(
            self.contract["component_variables"],
            ["F511", "F512", "F519", "F52"],
        )
        self.assertEqual(
            self.contract["expected_variable_count_per_measure"],
            140,
        )

    def test_total_uniqueness_uses_nullspace_linear_form(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["exact_rational_coefficient_rank"])
        self.assertTrue(
            rules["total_F5_unique_only_if_linear_form_annihilates_every_nullspace_basis_vector"]
        )
        self.assertTrue(
            rules["F51_unique_only_if_F511_F512_F519_linear_form_annihilates_every_nullspace_basis_vector"]
        )

    def test_source_and_structural_boundaries(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["direct_F511_equations_only_from_phase_C_resolved_cells"])
        self.assertTrue(rules["F52_equations_only_from_phase_C_resolved_or_structural_cells"])
        self.assertTrue(rules["F52_structural_scope_must_not_expand"])
        self.assertTrue(rules["zero_aggregate_flow_must_not_create_bilateral_zero_equations"])

    def test_no_materialization_or_behavioural_change(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_materialization_in_phase_D"])
        self.assertFalse(rules["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
