from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"corporate_investment_measurement_panel_promotion_review.json"

class CorporateInvestmentMeasurementPanelPromotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_exact_reviewed_artifact_is_frozen(self):
        w=self.r["reviewed_workflow"]
        self.assertEqual(w["artifact_id"],10582279137)
        self.assertEqual(
            w["artifact_zip_sha256"],
            "52b6cf33101d80b2ed868d15cbc63a8ed9cc319a4eb7803e77d8742a26d92e6f",
        )
        self.assertEqual(len(self.r["expected_files"]),2)

    def test_panel_is_exactly_contiguous_and_unestimated(self):
        p=self.r["complete_panel"]
        self.assertEqual(p["rows"],34)
        self.assertEqual(p["first_period"],"2017-Q4")
        self.assertEqual(p["last_period"],"2026-Q1")
        self.assertTrue(p["quarterly_contiguous"])
        h=self.r["hard_boundaries"]
        self.assertFalse(h["parameter_estimation_performed"])
        self.assertFalse(h["model_selection_performed"])
        self.assertFalse(h["holdout_opened"])
        self.assertFalse(h["system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
