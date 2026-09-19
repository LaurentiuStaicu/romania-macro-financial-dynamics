from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bank_credit_prudential_coverage_promotion_review.json"

class BankCreditPrudentialCoveragePromotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_exact_three_quarterly_series_are_frozen(self):
        exact=self.r["exact_series"]
        self.assertEqual(set(exact),{"npl_ratio","solvency_ratio","cet1_ratio"})
        for item in exact.values():
            self.assertEqual(item["rows"],46)
            self.assertEqual(item["first_period"],"2014-Q4")
            self.assertEqual(item["last_period"],"2026-Q1")

    def test_artifact_identity_is_exact(self):
        w=self.r["reviewed_workflow"]
        self.assertEqual(w["artifact_id"],10582377035)
        self.assertEqual(w["artifact_zip_sha256"],"4168935ee09b3449b76907f92c40aff945190bdc2c581c7a76f4ba29697ea87b")
        self.assertEqual(len(self.r["expected_files"]),4)

    def test_population_bridge_and_model_fit_remain_closed(self):
        self.assertFalse(self.r["estimation_authorized"])
        h=self.r["hard_boundaries"]
        self.assertTrue(h["no_calibration_or_refit"])
        self.assertTrue(h["no_cet1_substitution_for_solvency_after_outcomes"])
        self.assertTrue(h["no_population_bridge_by_numeric_similarity"])
        self.assertTrue(h["no_system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
