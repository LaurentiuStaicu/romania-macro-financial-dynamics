from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_panel_regeneration_candidate_contract.json"
)


class BNRBLSPanelRegenerationCandidateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_current_and_candidate_coverage_are_frozen(self) -> None:
        current = self.contract["expected_current_state"]
        candidate = self.contract["expected_candidate_state"]
        self.assertEqual(current["observed_round_count"], 8)
        self.assertEqual(
            current["missing_quarters"],
            ["2023-Q2", "2023-Q3", "2024-Q2", "2025-Q2"],
        )
        self.assertEqual(
            self.contract["authorized_additions"],
            ["2023-Q2", "2023-Q3", "2024-Q2"],
        )
        self.assertEqual(candidate["observed_round_count"], 11)
        self.assertEqual(candidate["missing_quarters"], ["2025-Q2"])
        self.assertAlmostEqual(candidate["coverage_fraction"], 11 / 12)

    def test_exact_day_is_not_fabricated_for_publication_quarter_authority(self) -> None:
        policy = self.contract["reference_date_policy"]
        self.assertTrue(policy["quarter_is_primary_period_identifier"])
        self.assertTrue(policy["no_synthetic_quarter_end_date"])
        self.assertTrue(policy["no_silent_date_normalisation"])
        self.assertTrue(policy["blank_reference_date_is_missing_exact_day_not_missing_quarter"])
        self.assertIn("leave reference_date empty", policy["publication_quarter_authority"])

    def test_candidate_gate_cannot_mutate_or_fit_model(self) -> None:
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_canonical_panel_mutation"])
        self.assertTrue(hard["no_interpolation"])
        self.assertTrue(hard["no_forward_fill"])
        self.assertTrue(hard["no_synthetic_quarter_creation"])
        self.assertTrue(hard["no_synthetic_reference_date"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_nfc_household_signal_aggregation"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])

    def test_pass_only_authorizes_promotion_review(self) -> None:
        self.assertEqual(
            self.contract["pass_effect"],
            "ELEVEN_OF_TWELVE_BLS_ROUNDS_READY_FOR_EXPLICIT_CANONICAL_PROMOTION_REVIEW_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
