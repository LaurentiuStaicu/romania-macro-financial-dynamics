from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_supplemental_materialisation_contract.json"
)


class CorporateInvestmentSupplementalMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_exact_verified_source_keys_are_frozen(self) -> None:
        sources = {item["id"]: item for item in self.c["sources"]}
        self.assertEqual(
            sources["nfc_gva"]["series_key"],
            "QSA.Q.N.RO.W0.S11.S1._Z.B.B1G._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertEqual(
            sources["real_gdp"]["series_key"],
            "MNA.Q.Y.RO.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N",
        )

    def test_live_gate_retains_levels_only(self) -> None:
        rules = self.c["materialisation_rules"]
        self.assertTrue(rules["retain_exact_raw_csv_bytes"])
        self.assertTrue(rules["no_cross_source_join"])
        self.assertTrue(rules["no_growth_transformation"])
        self.assertTrue(rules["no_trailing_sum_ratio"])
        self.assertTrue(rules["no_rate_aggregation"])

    def test_no_estimation_or_activation_is_authorized(self) -> None:
        self.assertFalse(self.c["estimation_authorized"])
        hard = self.c["hard_rules"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_lag_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
