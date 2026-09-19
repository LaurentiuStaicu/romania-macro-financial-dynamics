from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SectoralFinancialPositionsAggregateIdentityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/dynamics/sectoral_financial_positions_aggregate_identity_contract.json"
        )
        self.phase_a = load(
            "model/dynamics/sectoral_financial_positions_strict_gate_assessment.json"
        )

    def test_phase_b_is_explicitly_downstream_of_failed_phase_a(self) -> None:
        prerequisite = self.contract["prerequisite"]
        self.assertEqual(
            prerequisite["phase_A_verdict_required"],
            "STRICT_F2_F8_AGGREGATE_GATE_FAILED_NO_PROMOTION",
        )
        self.assertEqual(
            self.phase_a["verdict"],
            prerequisite["phase_A_verdict_required"],
        )
        self.assertFalse(prerequisite["phase_A_values_may_tune_phase_B_thresholds"])

    def test_exact_identity_is_total_F_minus_F1(self) -> None:
        basis = self.contract["methodological_basis"]
        self.assertEqual(
            basis["exact_identity"],
            "represented_F2_to_F8 = total_financial_instruments_F - F1",
        )
        self.assertEqual(
            set(self.contract["source"]["required_instruments"]),
            {"F", "F1"},
        )

    def test_only_H_and_C_receive_structural_F1_applicability_rule(self) -> None:
        applicability = self.contract["methodological_basis"][
            "structural_applicability"
        ]
        self.assertEqual(applicability["H"]["F1_rule"], "STRUCTURAL_NOT_APPLICABLE")
        self.assertEqual(applicability["C"]["F1_rule"], "STRUCTURAL_NOT_APPLICABLE")
        self.assertEqual(
            applicability["F"]["F1_rule"],
            "SOURCE_REQUIRED_FOR_BOTH_S12_AND_S121",
        )
        self.assertEqual(applicability["G"]["F1_rule"], "SOURCE_REQUIRED")
        self.assertEqual(applicability["BNR"]["F1_rule"], "SOURCE_REQUIRED")
        self.assertEqual(applicability["X"]["F1_rule"], "SOURCE_REQUIRED")
        self.assertTrue(
            self.contract["hard_rules"][
                "no_structural_zero_beyond_preregistered_H_and_C_F1_rule"
            ]
        )

    def test_promotion_gate_preserves_accounting_and_behavioural_boundaries(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_phase_A_missing_component_to_zero"])
        self.assertTrue(rules["no_bilateral_allocation"])
        self.assertTrue(rules["no_accounting_benchmark_mutation"])
        self.assertTrue(rules["no_accounting_readiness_promotion"])
        self.assertTrue(rules["no_stock_difference_flow_proxy"])
        self.assertTrue(rules["no_behavioural_activation"])
        promotion = self.contract["promotion_rule"]
        self.assertIn("bilateral Accounting Spine readiness", promotion)
        self.assertIn("behavioural closure remain unchanged", promotion)

    def test_thresholds_are_frozen_before_source_audit(self) -> None:
        gates = self.contract["consistency_gates"]
        self.assertEqual(gates["minimum_common_observation_count"], 40)
        self.assertEqual(
            gates["required_benchmark_periods"],
            ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"],
        )
        self.assertEqual(gates["system_stock_residual_max_abs_million_RON"], 0.1)
        self.assertEqual(gates["system_flow_residual_max_abs_million_RON"], 0.1)
        self.assertEqual(
            gates["H_C_F1_if_published_must_be_zero_within_million_RON"],
            0.1,
        )


if __name__ == "__main__":
    unittest.main()
