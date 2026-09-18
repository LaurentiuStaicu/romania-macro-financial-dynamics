from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F8OtherAccountsCoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f8_other_accounts_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_total_f8_not_trade_credit_proxy(self) -> None:
        self.assertEqual(
            self.contract["instrument_boundary"]["identity"],
            "F8 = F81 + F89",
        )
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["F81_must_not_substitute_for_F8"])
        self.assertTrue(rules["F8_F81_F89_identity_must_be_tested_where_components_are_available"])

    def test_total_custom_breakdown_only(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["custom_breakdown_total_must_be_used"])
        self.assertTrue(rules["direct_investment_breakdown_must_not_substitute_for_total"])

    def test_coverage_phase_cannot_materialize(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_materialization_in_coverage_phase"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
