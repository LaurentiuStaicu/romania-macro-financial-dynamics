from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_corporate_investment_measurement_panel.py"
spec = importlib.util.spec_from_file_location("investment_panel", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class CorporateInvestmentMeasurementPanelLogicTests(unittest.TestCase):
    def test_real_gdp_yoy_uses_exact_four_quarter_lag(self) -> None:
        data = {
            "2020-Q1": 100.0,
            "2020-Q2": 105.0,
            "2020-Q3": 110.0,
            "2020-Q4": 115.0,
            "2021-Q1": 120.0,
        }
        out = module.derive_real_gdp_yoy(data)
        self.assertEqual(set(out), {"2021-Q1"})
        self.assertAlmostEqual(out["2021-Q1"], 20.0)

    def test_support_intensity_uses_four_consecutive_quarters(self) -> None:
        grants = {
            "2020-Q1": 1.0,
            "2020-Q2": 2.0,
            "2020-Q3": 3.0,
            "2020-Q4": 4.0,
        }
        gva = {
            "2020-Q1": 10.0,
            "2020-Q2": 20.0,
            "2020-Q3": 30.0,
            "2020-Q4": 40.0,
        }
        out = module.derive_support_intensity(grants, gva)
        self.assertAlmostEqual(out["2020-Q4"], 10.0)

    def test_quarterly_rate_requires_all_three_months(self) -> None:
        monthly = {
            "2020-01": 3.0,
            "2020-02": 6.0,
            "2020-03": 9.0,
            "2020-04": 12.0,
            "2020-06": 18.0,
        }
        out = module.derive_quarterly_rate(monthly)
        self.assertAlmostEqual(out["2020-Q1"], 6.0)
        self.assertNotIn("2020-Q2", out)

    def test_lag_quarter_crosses_year_boundary(self) -> None:
        self.assertEqual(module.lag_quarter("2021-Q1", 1), "2020-Q4")
        self.assertEqual(module.lag_quarter("2021-Q1", 4), "2020-Q1")


if __name__ == "__main__":
    unittest.main()
