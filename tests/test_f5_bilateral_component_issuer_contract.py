from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F5ComponentIssuerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f5_bilateral_component_issuer_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_f52_issuer_scope_is_explicit(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["F52_structural_zero_only_for_resident_nonfund_issuers_H_C_G_BNR"])
        self.assertTrue(rules["F52_issuer_F_may_use_S12_directly_only_under_the_instrument_specific_nonissuer_rule_for_S121"])
        self.assertTrue(rules["F52_for_issuer_X_must_be_observed_or_exactly_derived_not_structurally_zero"])

    def test_f51_does_not_substitute_when_f52_applies(self) -> None:
        self.assertTrue(
            self.contract["hard_rules"]["F51_must_not_substitute_for_F5_when_F52_is_applicable"]
        )

    def test_no_allocation_or_materialization(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_materialization_in_phase_B"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
