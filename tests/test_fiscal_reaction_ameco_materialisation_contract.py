from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FiscalReactionAmecoMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fiscal_reaction_ameco_materialisation_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_romania_rows_are_frozen(self) -> None:
        by_id = {
            item["id"]: item for item in self.contract["sources"]
        }
        self.assertEqual(
            by_id["output_gap"]["code"],
            "ROM.1.0.0.0.AVGDGP",
        )
        self.assertEqual(
            by_id["primary_balance"]["code"],
            "ROM.1.0.319.0.UBLGI",
        )
        self.assertEqual(
            by_id["debt"]["code"],
            "ROM.1.0.319.0.UDGG",
        )

    def test_only_completed_years_are_admissible(self) -> None:
        release = self.contract["source_release"]
        self.assertEqual(release["actual_only_last_year"], 2024)
        self.assertEqual(
            release["forecast_years_excluded"],
            [2025, 2026, 2027],
        )
        gate = self.contract["coverage_gate"]
        self.assertEqual(
            gate["first_expected_common_actual_year"],
            1995,
        )
        self.assertEqual(
            gate["last_expected_common_actual_year"],
            2024,
        )
        self.assertEqual(
            gate["expected_common_actual_observations"],
            30,
        )

    def test_materialisation_does_not_authorize_model_fit(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_debt_gap_construction"])
        self.assertTrue(hard["no_regime_dummy_construction"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])
        self.assertFalse(
            self.contract["result_effect"]["calibration_cycle_open"]
        )


if __name__ == "__main__":
    unittest.main()
