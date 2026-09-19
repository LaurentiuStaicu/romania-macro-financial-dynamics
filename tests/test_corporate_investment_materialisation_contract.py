from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CorporateInvestmentMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "corporate_investment_materialisation_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_sector_specific_source_keys_are_frozen(self) -> None:
        by_id = {item["id"]: item for item in self.contract["sources"]}
        self.assertEqual(
            by_id["nfc_gfcf"]["series_key"],
            "QSA.Q.N.RO.W0.S11.S1.N.D.P51G._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertEqual(
            by_id["nfc_investment_grants"]["series_key"],
            "QSA.Q.N.RO.W0.S11.S1.N.C.D92._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertEqual(
            by_id["nfc_new_business_lending_rate"]["series_key"],
            "MIR.M.RO.B.A2A.A.R.A.2240.RON.N",
        )

    def test_materialisation_does_not_choose_target_or_transform(self) -> None:
        self.assertFalse(self.contract["estimation_authorized"])
        rules = self.contract["materialisation_rules"]
        self.assertTrue(rules["no_cross_frequency_join"])
        self.assertTrue(rules["no_monthly_to_quarterly_aggregation"])
        self.assertTrue(rules["no_seasonal_adjustment"])
        self.assertTrue(rules["no_deflation"])
        self.assertTrue(rules["no_growth_transformation"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_target_choice"])
        self.assertTrue(hard["no_rate_aggregation_choice"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])

    def test_semantic_shortcuts_are_prohibited(self) -> None:
        semantic = self.contract["semantic_boundaries"]
        self.assertFalse(semantic["total_economy_gfcf_substitution_allowed"])
        self.assertFalse(semantic["d92_may_be_labelled_eu_fund_impulse"])
        self.assertFalse(
            semantic["investment_rate_may_replace_growth_target_without_new_contract"]
        )
        self.assertFalse(
            semantic["new_business_rate_may_be_labelled_effective_debt_cost"]
        )


if __name__ == "__main__":
    unittest.main()
