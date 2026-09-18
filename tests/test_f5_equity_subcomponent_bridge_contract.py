from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F5EquitySubcomponentBridgeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f5_equity_subcomponent_bridge_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_equity_identity(self) -> None:
        self.assertEqual(
            self.contract["equity_identity"],
            "F51 = F511 + F512 + F519",
        )
        self.assertTrue(
            self.contract["hard_rules"]["F51_requires_F511_F512_F519"]
        )

    def test_no_proxy_or_new_structural_zero(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_F511_or_F512_proxy_for_F51"])
        self.assertTrue(rules["no_new_structural_issuer_zero_for_F511_F512_F519"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_f52_scope_is_retained_not_expanded(self) -> None:
        self.assertEqual(
            self.contract["retained_F52_rule"]["resident_nonfund_issuers"],
            ["H", "C", "G", "BNR"],
        )
        self.assertTrue(
            self.contract["hard_rules"]["F52_structural_scope_must_match_phase_B"]
        )

    def test_rank_and_materialization_are_later(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_materialization_in_phase_C"])
        self.assertTrue(rules["rank_must_be_computed_in_a_later_gate_before_materialization"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
