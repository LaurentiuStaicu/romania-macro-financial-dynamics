from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SectoralFinancialPositionsSourceDiscrepancyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/dynamics/sectoral_financial_positions_source_discrepancy_contract.json"
        )
        self.phase_c = load(
            "model/dynamics/sectoral_financial_positions_rounding_consistency_assessment.json"
        )

    def test_phase_d_is_downstream_of_failed_phase_c(self) -> None:
        prereq = self.contract["prerequisites"]
        self.assertEqual(
            prereq["required_phase_C_verdict"],
            "SOURCE_PRECISION_GATE_FAILED_NO_PROMOTION",
        )
        self.assertEqual(
            self.phase_c["verdict"],
            prereq["required_phase_C_verdict"],
        )

    def test_phase_d_is_diagnostic_only(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["diagnostic_only"])
        self.assertTrue(rules["no_reference_mode_promotion"])
        self.assertTrue(rules["no_readiness_count_change"])
        self.assertTrue(rules["no_new_tolerance"])
        self.assertTrue(rules["no_residual_balancing"])
        self.assertTrue(rules["no_sector_dropping"])
        self.assertTrue(rules["no_accounting_readiness_change"])
        self.assertTrue(rules["no_behavioural_activation"])

    def test_residual_decomposition_is_exactly_declared(self) -> None:
        identities = self.contract["identities"]
        self.assertEqual(
            identities["resident_additivity_residual"],
            "domestic_sector_sum_net - direct_total_economy_net",
        )
        self.assertEqual(
            identities["total_economy_external_residual"],
            "direct_total_economy_net + X_net",
        )
        self.assertIn(
            "must equal the six-sector residual",
            identities["six_sector_residual_decomposition"],
        )

    def test_direct_total_economy_cannot_replace_sector_histories(self) -> None:
        rule = self.contract["interpretation_rule"]
        self.assertIn("may not replace", rule)
        self.assertIn("no discrepancy may be allocated", rule)


if __name__ == "__main__":
    unittest.main()
