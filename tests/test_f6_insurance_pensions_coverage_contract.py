from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F6CoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f6_insurance_pensions_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_esa_decomposition_is_explicit(self) -> None:
        dec = self.contract["esa_decomposition"]
        self.assertEqual(dec["full"], "F6 = F61 + F62 + F63 + F64 + F65 + F66")
        self.assertEqual(
            dec["transmission_block"],
            "F6 = F61 + F62 + F63_F64_F65 + F66",
        )

    def test_no_issuer_assumption_or_missing_to_zero(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_issuer_applicability_assumption_in_phase_A"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_component_controls_are_conditional_on_coverage(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["full_six_component_identity_used_only_when_all_six_are_available"])
        self.assertTrue(rules["combined_pension_block_identity_used_only_when_required_series_are_available"])

    def test_no_materialization_or_behavioural_change(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_materialization_in_phase_A"])
        self.assertFalse(rules["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
