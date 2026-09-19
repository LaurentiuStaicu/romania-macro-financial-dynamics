from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_household_dsti_workbook_promotion_review.json"

class BnrHouseholdDstiWorkbookPromotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_exact_workbook_set_is_frozen(self):
        files=self.r["expected_files"]
        self.assertEqual(len(files),8)
        xls=[x for x in files if x["path"].endswith(".xls")]
        self.assertEqual(len(xls),7)
        self.assertTrue(all(x["sha256"] for x in xls))
        self.assertEqual(self.r["access_summary"]["accessible_workbooks"],7)

    def test_promotion_is_raw_evidence_only(self):
        self.assertFalse(self.r["estimation_authorized"])
        self.assertFalse(self.r["parser_boundary"]["canonical_value_extraction_ready"])
        self.assertFalse(self.r["access_summary"]["value_extraction_performed"])
        h=self.r["hard_boundaries"]
        self.assertTrue(h["no_dsti_semantic_substitution"])
        self.assertTrue(h["no_chart_digitisation"])
        self.assertTrue(h["no_system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
