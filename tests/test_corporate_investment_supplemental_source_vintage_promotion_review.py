from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_supplemental_source_vintage_promotion_review.json"
)


class CorporateInvestmentSupplementalSourceVintagePromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.r = json.loads(REVIEW.read_text(encoding="utf-8"))

    def test_exact_artifact_is_frozen(self) -> None:
        workflow = self.r["reviewed_workflow"]
        self.assertEqual(workflow["artifact_id"], 10581859400)
        self.assertEqual(
            workflow["artifact_zip_sha256"],
            "e32ebf8edab4e72e9b6cbfa491411df553e7d96229852ea6645658882bd0f491",
        )
        self.assertEqual(len(self.r["expected_files"]), 6)

    def test_coverages_and_source_semantics_are_frozen(self) -> None:
        self.assertEqual(self.r["coverage"]["nfc_gva"]["rows"], 109)
        self.assertEqual(self.r["coverage"]["real_gdp"]["rows"], 126)
        self.assertEqual(self.r["source_semantics"]["nfc_gva_adjustment"], "N")
        self.assertEqual(self.r["source_semantics"]["real_gdp_adjustment"], "Y")
        self.assertEqual(self.r["source_semantics"]["real_gdp_prices"], "LR")

    def test_review_authorizes_no_fit_or_activation(self) -> None:
        self.assertFalse(self.r["estimation_authorized"])
        hard = self.r["hard_boundaries"]
        self.assertFalse(hard["cross_source_join_performed"])
        self.assertFalse(hard["growth_transformation_performed"])
        self.assertFalse(hard["support_intensity_performed"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_lag_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
