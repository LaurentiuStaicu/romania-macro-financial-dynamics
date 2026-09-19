from __future__ import annotations

import unittest

from romania_macro_financial_dynamics.corporate_investment_selection import (
    build_lagged_rows,
    error_metrics,
    fit_ols,
    predict,
)


class CorporateInvestmentSelectionLogicTests(unittest.TestCase):
    def test_lagged_rows_use_only_prior_quarter_drivers(self):
        records = [
            {
                "period": "2020-Q1",
                "nfc_investment_rate": 20.0,
                "real_gdp_yoy_growth": 1.0,
                "investment_grants_support_intensity": 0.5,
                "nfc_new_business_lending_rate_up_to_one_year_quarterly_mean": 4.0,
            },
            {
                "period": "2020-Q2",
                "nfc_investment_rate": 21.0,
                "real_gdp_yoy_growth": 2.0,
                "investment_grants_support_intensity": 0.7,
                "nfc_new_business_lending_rate_up_to_one_year_quarterly_mean": 5.0,
            },
        ]
        row = build_lagged_rows(records)[0]
        self.assertEqual(row["period"], "2020-Q2")
        self.assertEqual(row["y"], 21.0)
        self.assertEqual(row["y_lag"], 20.0)
        self.assertEqual(row["gdp_lag"], 1.0)
        self.assertEqual(row["support_lag"], 0.5)
        self.assertEqual(row["rate_lag"], 4.0)

    def test_core_ols_recovers_known_coefficients(self):
        rows = []
        for i in range(20):
            ylag = 18.0 + 0.17 * i + 0.03 * (i % 3)
            gdp = -2.0 + 0.41 * i + 0.11 * (i % 2)
            rate = 3.0 + 0.09 * i + 0.07 * (i % 4)
            y = 2.0 + 0.7 * ylag + 0.25 * gdp - 0.4 * rate
            rows.append(
                {
                    "period": f"X{i}",
                    "y": y,
                    "y_lag": ylag,
                    "gdp_lag": gdp,
                    "rate_lag": rate,
                    "support_lag": 0.2 + 0.05 * (i % 5),
                }
            )
        fit = fit_ols(
            "core_lagged_drivers_ar",
            rows,
            condition_number_max=100.0,
        )
        self.assertAlmostEqual(fit.parameters["alpha"], 2.0, places=6)
        self.assertAlmostEqual(fit.parameters["rho"], 0.7, places=6)
        self.assertAlmostEqual(fit.parameters["beta_g"], 0.25, places=6)
        self.assertAlmostEqual(fit.parameters["beta_r"], -0.4, places=6)
        self.assertAlmostEqual(
            predict("core_lagged_drivers_ar", rows[-1], fit),
            rows[-1]["y"],
            places=6,
        )

    def test_augmented_ols_recovers_support_term(self):
        rows = []
        for i in range(24):
            ylag = 19.0 + 0.13 * i + 0.05 * (i % 4)
            gdp = -1.0 + 0.33 * i + 0.08 * (i % 3)
            rate = 3.5 + 0.07 * i + 0.04 * (i % 5)
            support = 0.3 + 0.06 * (i % 7) + 0.013 * i
            y = (
                1.0
                + 0.75 * ylag
                + 0.2 * gdp
                - 0.3 * rate
                + 0.6 * support
            )
            rows.append(
                {
                    "period": f"X{i}",
                    "y": y,
                    "y_lag": ylag,
                    "gdp_lag": gdp,
                    "rate_lag": rate,
                    "support_lag": support,
                }
            )
        fit = fit_ols(
            "support_augmented_lagged_drivers_ar",
            rows,
            condition_number_max=100.0,
        )
        self.assertAlmostEqual(fit.parameters["beta_s"], 0.6, places=6)

    def test_error_metrics_are_finite_and_directional(self):
        metrics = error_metrics([1.0, 2.0], [1.0, 1.5])
        self.assertGreater(metrics["rmse"], 0)
        self.assertGreater(metrics["bias_actual_minus_predicted"], 0)


if __name__ == "__main__":
    unittest.main()
