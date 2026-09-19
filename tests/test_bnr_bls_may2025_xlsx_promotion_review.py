from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_bls_may2025_xlsx_promotion_review.json"

class BnrBlsMay2025XlsxPromotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_two_distinct_xlsx_files_are_frozen(self):
        files=self.r["expected_files"]
        xlsx=[x for x in files if x["path"].endswith(".xlsx")]
        self.assertEqual(len(xlsx),2)
        self.assertNotEqual(xlsx[0]["sha256"],xlsx[1]["sha256"])
        self.assertFalse(self.r["source_identity"]["byte_identical_aliases"])

    def test_exact_artifact_is_frozen(self):
        w=self.r["reviewed_workflow"]
        self.assertEqual(w["artifact_id"],10582926685)
        self.assertEqual(w["artifact_zip_sha256"],"29952b777efd05eadd5313b41a0ab87e36c4e45a41f615561010e1b5e1f891dd")

    def test_promotion_does_not_create_history_or_fit(self):
        self.assertFalse(self.r["estimation_authorized"])
        h=self.r["hard_boundaries"]
        self.assertTrue(h["no_historical_series_claim"])
        self.assertTrue(h["no_legacy_xls_conversion"])
        self.assertTrue(h["no_system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
