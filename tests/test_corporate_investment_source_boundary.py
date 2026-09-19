from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class CorporateInvestmentSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/calibration_validation/"
            "corporate_investment_source_boundary_review.json"
        )

    def test_exact_aggregate_gfcf_and_nfc_rate_do_not_make_full_form_admissible(self) -> None:
        sources = self.review["exact_sources"]
        self.assertEqual(
            sources["aggregate_gfcf"]["series_key"],
            "MNA.Q.Y.RO.W0.S1.S1.D.P51G.N11G._T._Z.EUR.V.N",
        )
        self.assertEqual(
            sources["nfc_lending_rate"]["series_key"],
            "MIR.M.RO.B.A2A.A.R.A.2240.RON.N",
        )
        self.assertFalse(
            self.review["source_admissibility"]["registered_full_form_admissible"]
        )
        self.assertFalse(
            self.review["disposition"]["estimation_or_refit_allowed"]
        )

        self.assertEqual(
            sources["nfc_investment_grants"]["series_key"],
            "QSA.Q.N.RO.W0.S11.S1.N.C.D92._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertIn(
            "not an automatic replacement",
            sources["nfc_investment_grants"]["role"],
        )

        self.assertEqual(
            sources["nfc_investment_rate"]["series_key"],
            "QSA.Q.N.RO.W0.S11.S1.N.D.P51G._Z._Z._Z.XDC_R_B1G_CY._T.S.V.C4._T",
        )
        self.assertIn(
            "not the registered gI",
            sources["nfc_investment_rate"]["semantic_limit"],
        )

        self.assertEqual(
            sources["nfc_gfcf"]["series_key"],
            "QSA.Q.N.RO.W0.S11.S1.N.D.P51G._Z._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertEqual(
            sources["nfc_gfcf"]["coverage"],
            "1999-Q1 to 2025-Q4",
        )
        self.assertEqual(
            self.review["sector_specific_investment_boundary"][
                "qsa_family_status"
            ],
            "EXACT_ROMANIA_NFC_GFCF_SERIES_CONFIRMED",
        )

    def test_aggregate_gfcf_cannot_be_relabelled_corporate(self) -> None:
        self.assertIn(
            "not be relabelled corporate investment",
            self.review["exact_sources"]["aggregate_gfcf"]["semantic_limit"],
        )
        self.assertIn(
            "Do not substitute total-economy GFCF",
            self.review["sector_specific_investment_boundary"]["rule"],
        )
        self.assertIn(
            "not yet frozen",
            self.review["exact_sources"]["nfc_gfcf"]["semantic_limit"],
        )

    def test_eu_payments_are_not_investment_impulse_by_construction(self) -> None:
        eu = self.review["eu_fund_impulse_boundary"]
        self.assertTrue(eu["no_difference_of_cumulative_payments_as_investment"])
        self.assertEqual(
            eu["current_status"],
            "EU_SPECIFIC_IMPULSE_UNRESOLVED_BUT_EXACT_S11_D92_INVESTMENT_GRANTS_AVAILABLE",
        )
        alternative = eu["observed_sector_consistent_alternative"]
        self.assertEqual(
            alternative["status"],
            "EXACT_SOURCE_AVAILABLE_BUT_ORIGIN_NOT_EU_IDENTIFIED",
        )
        self.assertIn("does not identify the payer", alternative["limitation"])
        prohibited = " ".join(self.review["prohibited_shortcuts"]).lower()
        self.assertIn("cumulative eu programme payments", prohibited)
        self.assertIn("heterogeneous rrf", prohibited)

    def test_direct_investment_rate_is_alternative_not_post_hoc_substitute(self) -> None:
        alternative = self.review["alternative_target_boundary"]
        self.assertEqual(
            alternative["status"],
            "EXACT_INVESTMENT_RATE_TARGET_AVAILABLE_NOT_SELECTED",
        )
        self.assertIn("different behavioural questions", alternative["non_equivalence"])
        self.assertIn(
            "new preregistered candidate-family contract",
            alternative["future_gate"],
        )

    def test_missing_eu_bridge_does_not_authorize_reduced_form(self) -> None:
        admissibility = self.review["source_admissibility"]
        self.assertFalse(admissibility["reduced_form_automatically_authorized"])
        self.assertIn(
            "new preregistered candidate-family contract",
            admissibility["reduced_form_rule"],
        )
        self.assertEqual(
            self.review["disposition"]["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
