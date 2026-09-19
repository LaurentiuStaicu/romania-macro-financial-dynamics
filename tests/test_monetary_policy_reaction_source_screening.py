from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"monetary_policy_reaction_source_screening.json"

class MonetaryPolicyReactionSourceScreeningTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_target_is_observed_but_expectations_units_are_not_ready(self):
        target=self.r["sources"]["inflation_target"]
        self.assertAlmostEqual(target["value_pct"],2.5)
        self.assertAlmostEqual(target["variation_band_pp"],1.0)
        ready=self.r["measurement_readiness"]
        self.assertTrue(ready["exact_inflation_target_midpoint"])
        self.assertFalse(ready["unit_compatible_quantitative_private_inflation_expectations"])

    def test_qualitative_consumer_expectations_are_not_percent_inflation(self):
        c=self.r["sources"]["consumer_price_expectations"]
        self.assertEqual(c["dataset"],"ei_bsco_m / CONS_006")
        self.assertIn("not an expected annual inflation rate",c["semantic_limit"])
        self.assertTrue(any("CONS_006" in x for x in self.r["prohibited_shortcuts"]))

    def test_annual_model_gap_does_not_open_quarterly_rule(self):
        gap=self.r["sources"]["activity_gap_ameco"]
        self.assertEqual(gap["frequency"],"annual")
        self.assertFalse(self.r["measurement_readiness"]["quarterly_activity_gap_retained"])

    def test_policy_rule_remains_deferred(self):
        d=self.r["disposition"]
        self.assertTrue(d["observed_policy_rate_remains_exogenous"])
        self.assertFalse(d["estimation_or_refit_allowed"])
        self.assertFalse(d["policy_rule_activation"])
        self.assertEqual(d["behavioural_closure"],"UNCHANGED_INACTIVE")

if __name__=="__main__":
    unittest.main()
