from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F7CoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f7_financial_derivatives_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_official_qsa_dimensions_are_explicit(self) -> None:
        dims = self.contract["official_dimension_evidence"]
        self.assertEqual(dims["maturity"], "T")
        self.assertEqual(dims["expenditure"], "_Z")
        self.assertEqual(dims["unit"], "XDC")
        self.assertIn(".F7.T._Z.XDC.", dims["example_series_key"])

    def test_no_missing_zero_or_synthetic_allocation(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])
        self.assertTrue(rules["zero_aggregate_does_not_imply_bilateral_zeros"])

    def test_phase_a_does_not_invent_materiality_threshold(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["small_aggregate_does_not_imply_immateriality"])
        self.assertTrue(rules["materiality_threshold_may_not_be_invented_in_phase_A"])
        self.assertTrue(rules["no_materialization_in_phase_A"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
