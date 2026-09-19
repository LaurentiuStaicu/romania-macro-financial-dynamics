from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_measurement_panel_contract.json"
)


class CorporateInvestmentMeasurementPanelContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_retained_source_vintages_are_frozen(self) -> None:
        vintages = self.c["retained_source_vintages"]
        self.assertEqual(
            vintages["core"],
            "data/source_vintages/corporate-investment-source-family-vintage-2026-09-19",
        )
        self.assertEqual(
            vintages["supplemental"],
            "data/source_vintages/corporate-investment-supplemental-source-vintage-2026-09-19",
        )

    def test_only_preregistered_measurements_are_derived(self) -> None:
        t = self.c["transformations"]
        self.assertIn("t-4", t["real_gdp_yoy_growth"])
        self.assertIn("SUM(grants", t["investment_grants_support_intensity"])
        self.assertIn(
            "EXACTLY_THREE",
            t["nfc_new_business_lending_rate_quarterly_mean"],
        )
        self.assertEqual(
            t["target_investment_rate"],
            "USE_PROVIDER_PUBLISHED_LEVEL_UNCHANGED",
        )

    def test_no_fit_or_selection_is_authorized(self) -> None:
        hard = self.c["hard_rules"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_lag_selection"])
        self.assertTrue(hard["no_autoregressive_order_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["offline_only"])


if __name__ == "__main__":
    unittest.main()
