from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_bls_may2025_xlsx_layout_review.json"

class BnrBlsMay2025XlsxLayoutReviewTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_realised_supply_and_demand_are_separate(self):
        s=self.r["realised_bls_semantics"]
        self.assertEqual(s["nfc_credit_standards"]["question_id"],"C01")
        self.assertEqual(s["nfc_loan_demand"]["question_id"],"C05")
        self.assertEqual(s["household_mortgage_loan_demand"]["question_id"],"P06")
        self.assertEqual(s["household_consumer_loan_demand"]["question_id"],"P13")
        self.assertAlmostEqual(s["nfc_credit_standards"]["net_percentage"],11.71)
        self.assertAlmostEqual(s["nfc_loan_demand"]["net_percentage"],22.55)

    def test_household_standards_are_not_synthetically_aggregated(self):
        s=self.r["realised_bls_semantics"]
        self.assertAlmostEqual(s["household_mortgage_credit_standards"]["net_percentage"],-19.74)
        self.assertAlmostEqual(s["household_consumer_credit_standards"]["net_percentage"],15.38)
        self.assertNotEqual(
            s["household_mortgage_credit_standards"]["net_percentage"],
            s["household_consumer_credit_standards"]["net_percentage"],
        )

    def test_dsti_term_questions_are_not_dsti_levels(self):
        d=self.r["dsti_semantic_check"]
        self.assertIn("not levels",d["conclusion"])
        self.assertEqual(d["mortgage_term_question"]["response_type"],"change in a lending term, reported as bank-response distribution/net percentage")
        self.assertEqual(d["consumer_term_question"]["response_type"],"change in a lending term, reported as bank-response distribution/net percentage")

    def test_single_round_does_not_open_calibration(self):
        h=self.r["history_boundary"]
        self.assertFalse(h["longitudinal_history_present_in_this_workbook"])
        self.assertEqual(h["observation_rounds_in_workbook"],1)
        m=self.r["model_boundary"]
        self.assertFalse(m["historical_series_ready"])
        self.assertFalse(m["calibration_cycle_open"])
        self.assertFalse(m["estimation_authorized"])
        self.assertFalse(m["system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
