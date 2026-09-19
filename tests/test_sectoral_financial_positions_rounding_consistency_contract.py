from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SectoralFinancialPositionsRoundingConsistencyContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/dynamics/sectoral_financial_positions_rounding_consistency_contract.json"
        )
        self.phase_b = load(
            "model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"
        )

    def test_phase_c_is_downstream_of_failed_phase_b_without_residual_tuning(self) -> None:
        prereq = self.contract["prerequisites"]
        self.assertEqual(
            prereq["required_phase_B_verdict"],
            "AGGREGATE_IDENTITY_GATE_FAILED_STRICT_STOCK_RECONCILIATION_NO_PROMOTION",
        )
        self.assertEqual(
            self.phase_b["verdict"],
            prereq["required_phase_B_verdict"],
        )
        self.assertFalse(prereq["phase_B_residual_values_may_tune_phase_C_rule"])

    def test_rounding_rule_is_metadata_derived_not_fixed(self) -> None:
        rounding = self.contract["rounding_model"]
        self.assertEqual(
            rounding["per_series_half_rounding_width_formula"],
            "0.5 * 10^(-DECIMALS)",
        )
        self.assertTrue(rounding["no_fixed_tolerance_replacement"])
        self.assertTrue(rounding["no_use_of_phase_B_max_residual"])
        self.assertEqual(
            rounding["pass_condition"],
            "abs(system_residual) <= rounding_envelope + computational_epsilon",
        )

    def test_algebraic_identity_cancels_s121_before_precision_envelope(self) -> None:
        identity = self.contract["algebraic_system_identity"]
        self.assertEqual(
            identity["resident_sectors_after_F_plus_BNR_cancellation"],
            ["S1M", "S11", "S12", "S13"],
        )
        self.assertIn("cancel exactly", identity["note"])

    def test_decimals_metadata_is_mandatory_for_used_series(self) -> None:
        source = self.contract["source_requirements"]
        self.assertTrue(source["mandatory_DECIMALS_for_every_available_mandatory_series"])
        self.assertTrue(source["DECIMALS_must_be_single_nonnegative_integer_per_series"])
        self.assertEqual(source["minimum_common_observation_count"], 40)
        self.assertEqual(
            source["required_benchmark_periods"],
            ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"],
        )

    def test_phase_c_cannot_mutate_accounting_or_behaviour(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_phase_B_threshold_relaxation"])
        self.assertTrue(rules["no_new_fixed_residual_tolerance"])
        self.assertTrue(rules["no_phase_B_residual_based_parameter_choice"])
        self.assertTrue(rules["no_missing_DECIMALS_imputation"])
        self.assertTrue(rules["no_missing_source_to_zero"])
        self.assertTrue(rules["no_bilateral_allocation"])
        self.assertTrue(rules["no_accounting_readiness_change"])
        self.assertTrue(rules["no_behavioural_activation"])


if __name__ == "__main__":
    unittest.main()
