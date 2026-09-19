from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"external_fx_refinancing_source_screening_2026-09-19.json"

class ExternalFxRefinancingSourceScreeningTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_new_margins_do_not_create_joint_exposure(self):
        m=self.r["identification_matrix"]
        self.assertTrue(m["institutional_sector"])
        self.assertTrue(m["aggregate_external_debt_currency_composition"])
        self.assertTrue(m["s13_currency_risk_margin"])
        self.assertTrue(m["s13_one_year_refinancing_margin"])
        self.assertFalse(m["currency_by_sector"])
        self.assertFalse(m["joint_currency_x_residual_maturity_by_sector"])
        self.assertFalse(m["hedging_by_sector"])

    def test_mof_metrics_are_margins_not_joint_schedule(self):
        x=self.r["evidence"]["mof_s13_portfolio"]["observed_margins"]
        self.assertAlmostEqual(x["domestic_currency_share_pct"],48.5)
        self.assertAlmostEqual(x["debt_maturing_within_one_year_pct"],10.0)
        self.assertAlmostEqual(x["average_time_to_maturity_total_years"],6.9)
        self.assertTrue(any("multiply MoF" in p for p in self.r["prohibited_inference"]))

    def test_feedback_remains_open_and_inactive(self):
        d=self.r["disposition"]
        self.assertEqual(d["feedback_topology"],"OPEN_CHAIN")
        self.assertFalse(d["estimation_or_refit_allowed"])
        self.assertFalse(d["quantitative_closure_authorized"])
        self.assertEqual(d["validated_reference_behavioural_mechanisms_change"],0)
        self.assertEqual(d["behavioural_closure"],"UNCHANGED_INACTIVE")

if __name__=="__main__":
    unittest.main()
