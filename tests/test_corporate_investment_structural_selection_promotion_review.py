from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"corporate_investment_structural_selection_promotion_review.json"

class CorporateInvestmentStructuralSelectionPromotionReviewTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_exact_failed_artifact_is_frozen(self):
        self.assertEqual(self.r["verdict"],"FAIL_BEFORE_HOLDOUT")
        w=self.r["reviewed_workflow"]
        self.assertEqual(w["artifact_id"],10582335814)
        self.assertEqual(
            w["artifact_zip_sha256"],
            "011b4c3fdd64744476691b28671af01af1b7f6df12beda9303eeaa4c4a6ab0a1",
        )
        self.assertEqual(
            self.r["expected_file"]["sha256"],
            "bf5f0b601028641568ba784134a3ed47ab857dcb92dbeb6ddc29fa932385cf05",
        )

    def test_holdout_is_explicitly_unopened(self):
        s=self.r["selection_summary"]
        self.assertFalse(s["final_evaluation_opened"])
        self.assertIsNone(s["selected_form_for_final_evaluation"])
        self.assertFalse(s["primary_passes_all_gates"])
        self.assertEqual(s["core_parameter_domain_fractions"]["beta_r"],0.0)

if __name__=="__main__":
    unittest.main()
