from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F4LoansCoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f4_loans_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_coverage_phase_cannot_materialize(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_materialization_in_coverage_phase"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_exact_sector_and_maturity_derivations_only(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["F_composite_only_by_exact_S12_minus_S121"])
        self.assertTrue(rules["maturity_T_may_be_derived_only_as_exact_S_plus_L"])
        self.assertTrue(rules["maturity_conflict_blocks_cell"])

    def test_dual_orientation_gate(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["dual_W2_orientations_must_be_probed"])
        self.assertTrue(rules["orientation_conflict_blocks_cell"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
