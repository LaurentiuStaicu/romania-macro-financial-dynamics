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
        self.executed = load(
            "model/dynamics/"
            "sectoral_financial_positions_aggregate_identity_contract_executed_2026-09-19.json"
        )
        self.phase_a = load(
            "model/dynamics/sectoral_financial_positions_strict_gate_assessment.json"
        )
        self.phase_b = load(
            "model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"
        )
        self.review = load(
            "model/dynamics/sectoral_financial_positions_esa_f1_applicability_review.json"
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

    def test_executed_phase_b_f1_rules_are_preserved_exactly(self) -> None:
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

    def test_thresholds_and_source_requirements_are_frozen_as_executed(self) -> None:
        gates = self.contract["consistency_gates"]
        self.assertEqual(gates["minimum_common_observation_count"], 40)
        self.assertEqual(
            gates["required_benchmark_periods"],
            ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"],
        )
        self.assertEqual(gates["system_stock_residual_max_abs_million_RON"], 0.1)
        self.assertEqual(gates["system_flow_residual_max_abs_million_RON"], 0.1)
        self.assertEqual(
            set(gates["mandatory_F1_for"]),
            {"S12", "S121", "S13", "W1_total_economy"},
        )
        self.assertEqual(
            gates["H_C_F1_if_published_must_be_zero_within_million_RON"],
            0.1,
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

    def test_current_historical_contract_matches_immutable_executed_snapshot(self) -> None:
        self.assertEqual(self.contract, self.executed)
        self.assertEqual(
            self.phase_b["executed_contract_snapshot"],
            "model/dynamics/"
            "sectoral_financial_positions_aggregate_identity_contract_executed_2026-09-19.json",
        )
        self.assertEqual(
            self.phase_b["executed_contract_workflow_head_sha"],
            "1fc8620c2981a82cf9bada147fbba9158aaf1461",
        )
        self.assertEqual(
            self.phase_b["executed_contract_blob_sha"],
            "20c1ae829cdfff6c77e46193a0d68edc8f94326d",
        )

    def test_post_run_esa_review_cannot_rewrite_a_d_history(self) -> None:
        self.assertEqual(
            self.review["status"],
            "FUTURE_METHODOLOGY_CORRECTION_NOT_RETROACTIVE",
        )
        nonretro = self.review["nonretroactivity"]
        self.assertFalse(nonretro["phase_A_reinterpreted"])
        self.assertFalse(nonretro["phase_B_reinterpreted"])
        self.assertFalse(nonretro["phase_C_reinterpreted"])
        self.assertFalse(nonretro["phase_D_reinterpreted"])
        self.assertFalse(nonretro["historical_readiness_changed"])
        self.assertFalse(nonretro["reference_mode_promoted"])
        self.assertEqual(
            self.review["next_action"]["status"],
            "NO_IMMEDIATE_SOURCE_RERUN",
        )
        self.assertIn(
            "new separately preregistered future phase/contract",
            self.review["next_action"]["rule"],
        )


if __name__ == "__main__":
    unittest.main()
