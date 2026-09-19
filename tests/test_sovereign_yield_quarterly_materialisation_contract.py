from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SovereignYieldQuarterlyMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/calibration_validation/"
            "sovereign_yield_quarterly_materialisation_contract.json"
        )

    def test_estimation_is_not_authorized(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_regression_or_parameter_estimation"])
        self.assertTrue(rules["no_lag_selection"])
        self.assertTrue(rules["no_system_dynamics_activation"])

    def test_target_and_benchmark_require_complete_three_month_quarters(self) -> None:
        self.assertEqual(
            self.contract["target"]["series_key"],
            "IRS.M.RO.L.L40.CI.0000.RON.N.Z",
        )
        self.assertEqual(
            self.contract["common_long_rate_control"]["series_key"],
            "IRS.M.DE.L.L40.CI.0000.EUR.N.Z",
        )
        self.assertIn(
            "all three calendar months",
            self.contract["target"]["completeness_rule"].lower(),
        )
        self.assertIn(
            "same three calendar months",
            self.contract["common_long_rate_control"]["completeness_rule"].lower(),
        )

    def test_ciss_months_are_equal_weighted_before_quarterly_mean(self) -> None:
        ciss = self.contract["financial_stress_control"]
        self.assertEqual(
            ciss["series_key"],
            "CISS.D.U2.Z0Z.4F.EC.SS_CIN.IDX",
        )
        self.assertIn("equal-weight", ciss["aggregation_rule"])
        self.assertIn("not interpolated", ciss["completeness_rule"])

    def test_fiscal_inputs_remain_direct_quarterly_observations(self) -> None:
        fiscal = self.contract["fiscal_controls"]
        self.assertEqual(fiscal["debt_to_gdp"]["series"], "PC_GDP")
        self.assertEqual(
            fiscal["net_lending_borrowing_to_gdp"]["item"],
            "B9 net lending (+) / net borrowing (-)",
        )
        self.assertEqual(
            fiscal["net_lending_borrowing_to_gdp"]["adjustment"],
            "calendar and seasonally adjusted",
        )
        self.assertTrue(
            self.contract["hard_rules"]["no_monthly_forward_fill_of_fiscal_data"]
        )

    def test_pure_spread_label_is_still_prohibited(self) -> None:
        self.assertTrue(self.contract["hard_rules"]["no_spread_relabeling"])
        self.assertIn(
            "not labelled a pure credit spread",
            self.contract["common_long_rate_control"]["interpretation"],
        )


if __name__ == "__main__":
    unittest.main()
