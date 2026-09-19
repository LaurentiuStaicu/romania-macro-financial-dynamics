from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FiscalReactionAmecoPromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "fiscal_reaction_ameco_source_vintage_promotion_review.json"
            ).read_text(encoding="utf-8")
        )

    def test_review_freezes_exact_artifact_and_coverage(self) -> None:
        self.assertEqual(
            self.review["reviewed_workflow"]["artifact_id"],
            10580819452,
        )
        self.assertEqual(
            self.review["reviewed_workflow"]["artifact_zip_sha256"],
            "4827c71d166996a07237cc550461e5cf4d5077424ac72f9402280808fe5c6df6",
        )
        self.assertEqual(self.review["coverage"]["rows"], 30)
        self.assertEqual(self.review["coverage"]["first_year"], 1995)
        self.assertEqual(self.review["coverage"]["last_year"], 2024)
        self.assertFalse(self.review["coverage"]["forecast_years_present"])

    def test_review_does_not_authorize_estimation(self) -> None:
        self.assertFalse(self.review["estimation_authorized"])
        hard = self.review["hard_boundaries"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
