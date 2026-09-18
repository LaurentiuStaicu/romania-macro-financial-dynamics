from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F21CurrencyCoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f21_currency_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_audit_cannot_mutate_benchmark_or_total_f2(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_F21_relabelled_as_total_F2"])
        self.assertTrue(rules["no_F2M_plus_F21_total_F2_promotion_in_this_audit"])

    def test_no_synthetic_currency_allocation(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_synthetic_holder_allocation"])
        self.assertTrue(rules["no_synthetic_issuer_allocation"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_structural_zero_without_source_or_formal_identity"])

    def test_bnr_only_issuer_is_not_assumed(self) -> None:
        self.assertTrue(self.contract["hard_rules"]["no_BNR_only_issuer_assumption"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
