from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CorporateInvestmentSourceVintagePromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "corporate_investment_source_vintage_promotion_review.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_artifact_and_coverages_are_frozen(self) -> None:
        workflow = self.review["reviewed_workflow"]
        self.assertEqual(workflow["artifact_id"], 10581133050)
        self.assertEqual(
            workflow["artifact_zip_sha256"],
            "0902a9a575cc1f322341a93e72422dd4cf06ce966b719103d9442f8d6c2f93e6",
        )
        coverage = self.review["coverage"]
        self.assertEqual(coverage["nfc_gfcf"]["rows"], 109)
        self.assertEqual(
            coverage["nfc_new_business_lending_rate"]["first_period"],
            "2017-09",
        )

    def test_review_does_not_choose_target_or_authorize_fit(self) -> None:
        hard = self.review["hard_boundaries"]
        self.assertFalse(hard["target_selected"])
        self.assertFalse(hard["cross_frequency_join_performed"])
        self.assertFalse(hard["rate_aggregation_performed"])
        self.assertFalse(hard["growth_or_deflation_transform_performed"])
        self.assertTrue(hard["no_eu_origin_inference"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
