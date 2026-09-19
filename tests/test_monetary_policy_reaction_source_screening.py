from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"monetary_policy_reaction_source_screening.json"

class MonetaryPolicyReactionSourceScreeningTests(unittest.TestCase):
    def setUp(self):
        self.r=json.loads(P.read_text(encoding="utf-8"))

    def test_target_and_quantitative_expectations_concept_are_observed(self):
        target=self.r["sources"]["inflation_target"]
        self.assertAlmostEqual(target["value_pct"],2.5)
        self.assertAlmostEqual(target["variation_band_pp"],1.0)
        ready=self.r["measurement_readiness"]
        self.assertTrue(ready["exact_inflation_target_midpoint"])
        self.assertTrue(ready["unit_compatible_quantitative_private_inflation_expectations"])
        self.assertTrue(ready["quantitative_expectations_concept_observed"])
        self.assertFalse(
            ready["quantitative_expectations_machine_readable_formation_time_history_retained"]
        )

    def test_qualitative_consumer_expectations_are_not_percent_inflation(self):
        c=self.r["sources"]["consumer_price_expectations"]
        self.assertEqual(c["dataset"],"ei_bsco_m / CONS_006")
        self.assertIn("not an expected annual inflation rate",c["semantic_limit"])
        self.assertTrue(any("CONS_006" in x for x in self.r["prohibited_shortcuts"]))

    def test_financial_analyst_expectations_require_formation_time_mapping(self):
        a=self.r["sources"]["financial_analyst_expectations"]
        self.assertEqual(
            a["status"],
            "QUANTITATIVE_1Y_2Y_SERIES_CONCEPT_CONFIRMED_MACHINE_READABLE_FORMATION_TIME_HISTORY_NOT_RETAINED",
        )
        self.assertIn("formation date",a["horizon_mapping_boundary"])
        self.assertFalse(a["chart_digitisation_allowed"])
        self.assertFalse(
            self.r["measurement_readiness"][
                "quantitative_expectations_machine_readable_formation_time_history_retained"
            ]
        )

    def test_quarterly_bnr_gap_is_observed_but_real_time_vintages_are_not_retained(self):
        gap=self.r["sources"]["activity_gap_bnr"]
        self.assertEqual(gap["frequency"],"quarterly")
        self.assertEqual(gap["latest_reviewed_information_cutoff"],"2024-10-29")
        self.assertFalse(gap["chart_digitisation_allowed"])
        ready=self.r["measurement_readiness"]
        self.assertTrue(ready["quarterly_bnr_activity_gap_observed_in_reports"])
        self.assertFalse(ready["quarterly_activity_gap_retained"])
        self.assertFalse(ready["real_time_gap_vintages_retained"])

    def test_annual_ameco_gap_does_not_replace_real_time_quarterly_gap(self):
        gap=self.r["sources"]["activity_gap_ameco"]
        self.assertEqual(gap["frequency"],"annual")
        self.assertFalse(self.r["measurement_readiness"]["quarterly_activity_gap_retained"])

    def test_policy_rule_remains_deferred(self):
        d=self.r["disposition"]
        self.assertEqual(
            d["source_readiness"],
            "QUANTITATIVE_EXPECTATIONS_AND_QUARTERLY_GAP_CONCEPTS_OBSERVED_FORMATION_TIME_AND_REAL_TIME_VINTAGES_NOT_RETAINED",
        )
        self.assertTrue(d["observed_policy_rate_remains_exogenous"])
        self.assertFalse(d["estimation_or_refit_allowed"])
        self.assertFalse(d["policy_rule_activation"])
        self.assertEqual(d["behavioural_closure"],"UNCHANGED_INACTIVE")

if __name__=="__main__":
    unittest.main()
