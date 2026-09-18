from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F5CoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f5_equity_fund_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_total_instrument_and_components_are_distinct(self) -> None:
        self.assertEqual(self.contract["instrument_structure"]["identity"], "F5 = F51 + F52")
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["F51_must_not_substitute_for_F5"])
        self.assertTrue(rules["F52_must_not_substitute_for_F5"])

    def test_source_dimensions_and_valuation_remain_explicit(self) -> None:
        self.assertEqual(self.contract["source_dimensions"]["valuation"], "V")
        self.assertTrue(self.contract["hard_rules"]["valuation_dimension_must_remain_explicit"])

    def test_f5_uses_not_applicable_maturity_and_expenditure(self) -> None:
        dims = self.contract["source_dimensions"]
        self.assertEqual(dims["maturity"], "not_applicable__Z")
        self.assertEqual(dims["expenditure"], "_Z")
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["F5_maturity_dimension_must_be_not_applicable__Z"])
        self.assertTrue(rules["F5_expenditure_dimension_must_be_not_applicable__Z"])

    def test_no_synthetic_allocation_or_materialization(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_materialization_in_coverage_phase"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
