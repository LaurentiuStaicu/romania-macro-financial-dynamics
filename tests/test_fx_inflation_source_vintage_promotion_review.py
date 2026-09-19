from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FxInflationSourceVintagePromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fx_inflation_source_vintage_promotion_review.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_artifact_and_coverage_are_frozen(self) -> None:
        workflow = self.review["reviewed_workflow"]
        self.assertEqual(workflow["artifact_id"], 10581262018)
        self.assertEqual(
            workflow["artifact_zip_sha256"],
            "282b52fb29732d137d81cec6485e8bf1bab17002045ffc1fab01fca5f0bf6f65",
        )
        coverage = self.review["coverage"]
        self.assertEqual(coverage["rows"], 294)
        self.assertEqual(coverage["first_period"], "2002-01")
        self.assertEqual(coverage["last_period"], "2026-06")
        self.assertEqual(coverage["transformations_performed"], [])

    def test_promotion_review_does_not_authorize_estimation(self) -> None:
        self.assertFalse(self.review["estimation_authorized"])
        hard = self.review["hard_boundaries"]
        self.assertTrue(hard["level_only_materialisation"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
