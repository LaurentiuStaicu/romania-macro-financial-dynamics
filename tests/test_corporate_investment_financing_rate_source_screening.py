from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"corporate_investment_financing_rate_source_screening_contract.json"

class CorporateInvestmentFinancingRateSourceScreeningTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(P.read_text(encoding="utf-8"))

    def test_only_exact_semantically_related_mir_families_are_screened(self):
        by={x["id"]:x for x in self.c["candidates"]}
        self.assertEqual(by["total_fixation"]["series_key"],"MIR.M.RO.B.A2A.A.R.A.2240.RON.N")
        self.assertEqual(by["up_to_one_year_fixation"]["series_key"],"MIR.M.RO.B.A2A.F.R.A.2240.RON.N")
        self.assertIn("S11",by["up_to_one_year_fixation"]["semantic_scope"])
        self.assertIn("RON",by["up_to_one_year_fixation"]["semantic_scope"])

    def test_eligibility_is_source_quality_only(self):
        rule=self.c["eligibility_rule"]
        self.assertEqual(rule["alternative_min_complete_quarter_coverage_fraction"],0.9)
        self.assertEqual(rule["alternative_min_advantage_over_total_fixation"],0.2)
        self.assertFalse(rule["use_model_outcomes"])
        self.assertFalse(rule["automatic_replacement"])

    def test_no_fit_is_authorized(self):
        h=self.c["hard_rules"]
        self.assertTrue(h["no_parameter_estimation"])
        self.assertTrue(h["no_model_selection"])
        self.assertTrue(h["no_investment_outcome_access"])
        self.assertTrue(h["no_holdout_opening"])
        self.assertTrue(h["no_system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
