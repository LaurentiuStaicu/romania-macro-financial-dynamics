from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"corporate_investment_financing_rate_source_screening_result.json"

class CorporateInvestmentFinancingRateSourceScreeningResultTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_alternative_passes_only_preregistered_source_continuity_gate(self):
        self.assertTrue(self.r["preregistered_rule"]["alternative_passed"])
        self.assertFalse(self.r["model_outcomes_used"])
        a=self.r["source_continuity"]["total_fixation"]
        b=self.r["source_continuity"]["up_to_one_year_fixation"]
        self.assertAlmostEqual(a["complete_quarter_coverage_fraction"],19/35)
        self.assertEqual(b["complete_quarter_coverage_fraction"],1.0)
        self.assertEqual(b["longest_consecutive_month_run"],108)

    def test_exact_artifact_is_frozen(self):
        w=self.r["reviewed_workflow"]
        self.assertEqual(w["artifact_id"],10582283925)
        self.assertEqual(w["artifact_zip_sha256"],"cf63ce2efa2622bb9ac40a232f4c5a477b124e07565653df5a5f7e964e6b5203")
        self.assertEqual(len(self.r["expected_files"]),3)

    def test_result_does_not_admit_a_behavioural_form(self):
        h=self.r["hard_boundaries"]
        self.assertFalse(h["automatic_behavioural_admission"])
        self.assertTrue(h["no_parameter_estimation"])
        self.assertTrue(h["no_model_selection"])
        self.assertTrue(h["no_investment_outcome_access"])
        self.assertTrue(h["no_system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
