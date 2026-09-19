from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ExternalFxRefinancingSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/calibration_validation/"
            "external_fx_refinancing_source_boundary_review.json"
        )

    def test_reporting_unit_is_not_currency_denomination(self) -> None:
        examples = self.review["exact_source_examples"]
        self.assertEqual(
            examples[0]["series_key"],
            "BPS.Q.N.RO.W1.S13.S1.LE.L.FA.TXD.FGED.L.EUR._T._X.N.ALL",
        )
        self.assertEqual(examples[0]["currency_denominator"], "All currencies (_T)")
        self.assertEqual(
            examples[2]["series_key"],
            "BPS.Q.N.RO.W1.S1.S1.LE.L.FA._T.FGED._Z.RON._T._X.N.ALL",
        )
        self.assertEqual(examples[2]["currency_denominator"], "All currencies (_T)")
        self.assertTrue(
            self.review["scientific_distinctions"][
                "reporting_unit_is_not_currency_denomination"
            ]
        )

    def test_original_maturity_is_not_refinancing_schedule(self) -> None:
        findings = self.review["source_boundary_findings"]
        self.assertTrue(findings["original_maturity_breakdown_available"])
        self.assertFalse(findings["residual_maturity_schedule_available"])
        self.assertTrue(
            self.review["scientific_distinctions"][
                "original_maturity_is_not_residual_maturity"
            ]
        )
        prohibited = " ".join(self.review["prohibited_shortcuts"]).lower()
        self.assertIn("short-term original maturity", prohibited)
        self.assertIn("stock changes as refinancing flows", prohibited)

    def test_mechanism_remains_deferred_and_open_chain(self) -> None:
        self.assertEqual(
            self.review["disposition"]["mechanism_classification"],
            "DEFERRED",
        )
        self.assertFalse(
            self.review["disposition"]["estimation_or_refit_allowed"]
        )
        self.assertFalse(self.review["disposition"]["central_feedback"])
        self.assertEqual(
            self.review["disposition"]["feedback_topology"],
            "OPEN_CHAIN",
        )
        model = load("model/registries/model_contract.json")
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])


if __name__ == "__main__":
    unittest.main()
