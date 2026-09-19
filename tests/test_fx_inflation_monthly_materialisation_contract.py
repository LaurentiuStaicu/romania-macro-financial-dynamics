from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FxInflationMonthlyMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fx_inflation_monthly_materialisation_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_provider_boundaries_are_frozen(self) -> None:
        sources = self.contract["sources"]
        self.assertEqual(
            sources["exchange_rate"]["series_key"],
            "EXR.M.RON.EUR.SP00.A",
        )
        self.assertEqual(
            sources["hicp"]["exact_dimensions"],
            {
                "lang": "en",
                "freq": "M",
                "unit": "I25",
                "coicop18": "TOTAL",
                "geo": "RO",
            },
        )
        self.assertEqual(
            sources["external_price"]["exact_dimensions"]["indic_et"],
            "IVU",
        )
        self.assertEqual(
            sources["external_price"]["exact_dimensions"]["bclas_bec"],
            "TOTAL",
        )
        self.assertEqual(
            sources["external_price"]["exact_dimensions"]["partner"],
            "WORLD",
        )

    def test_materialisation_is_level_only_and_not_estimation(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["level_only_materialisation"])
        self.assertTrue(hard["no_log_difference"])
        self.assertTrue(hard["no_monthly_or_annual_inflation_transform"])
        self.assertTrue(hard["no_lag_selection"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])

    def test_no_gap_filling_is_allowed(self) -> None:
        gate = self.contract["completeness_gate"]
        self.assertEqual(gate["expected_first_common_period"], "2002-01")
        self.assertTrue(gate["finite_common_months_only"])
        self.assertTrue(gate["no_interpolation"])
        self.assertTrue(gate["no_backfill"])
        self.assertTrue(gate["no_forward_fill"])
        self.assertTrue(gate["no_missing_to_zero"])


if __name__ == "__main__":
    unittest.main()
