from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FxInflationTransformLagWindowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fx_inflation_transform_lag_window_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_transformations_and_regime_start_are_frozen(self) -> None:
        transforms = self.contract["transformations"]
        self.assertIn("ln(HICP_t)", transforms["target_monthly_hicp_inflation"]["formula"])
        self.assertIn("ln(RON_per_EUR_t)", transforms["fx_depreciation"]["formula"])
        self.assertIn("ln(UVI_t)", transforms["external_price_change"]["formula"])
        self.assertEqual(
            self.contract["regime_boundary"]["estimation_target_start"],
            "2005-08",
        )
        self.assertFalse(
            self.contract["regime_boundary"][
                "pre_start_target_observations_allowed"
            ]
        )

    def test_lag_blocks_cover_exactly_zero_to_twelve_months(self) -> None:
        blocks = self.contract["fx_lag_blocks"]
        months = [m for block in blocks for m in block["months"]]
        self.assertEqual(months, list(range(13)))
        self.assertEqual(len(blocks), 4)
        self.assertEqual(
            self.contract["persistence_boundary"]["inflation_lags_months"],
            [1, 2],
        )

    def test_seasonality_is_fixed_because_hicp_is_unadjusted(self) -> None:
        self.assertTrue(
            self.contract["source_methodology_boundary"][
                "hicp_is_not_seasonally_adjusted"
            ]
        )
        seasonal = self.contract["seasonal_treatment"]
        self.assertEqual(seasonal["dummy_count"], 11)
        self.assertTrue(
            seasonal["included_in_every_estimated_baseline_and_candidate"]
        )

    def test_recent_final_evaluation_is_locked(self) -> None:
        windows = self.contract["windows"]
        self.assertEqual(windows["initial_calibration"], "2005-08..2014-12")
        self.assertEqual(windows["structural_selection"], "2015-01..2020-12")
        self.assertEqual(windows["final_evaluation"], "2021-01..2026-06")
        self.assertIn("only if", windows["final_evaluation_open_rule"].lower())

    def test_contract_does_not_authorize_fit_or_closure(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_alternative_fx_lag_search"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection_execution"])
        self.assertTrue(hard["no_final_evaluation_access"])
        self.assertTrue(hard["no_causal_claim"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
