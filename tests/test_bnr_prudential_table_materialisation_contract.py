from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_prudential_table_materialisation_contract.json"

class BNRPrudentialTableMaterialisationContractTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(P.read_text(encoding="utf-8"))

    def test_target_window_and_variables_are_frozen_before_values(self):
        w=self.c["target_window"]
        self.assertEqual(w["start_period"],"2014-Q4")
        self.assertEqual(w["end_period"],"2025-Q4")
        self.assertEqual(w["expected_quarter_count"],45)
        v=self.c["target_variables"]
        self.assertEqual(v["total_capital_ratio"]["unit"],"percent")
        self.assertEqual(v["npl_ratio"]["unit"],"percent")
        self.assertTrue(v["cet1_ratio_crosscheck"]["required_for_crosscheck"])

    def test_source_selection_cannot_use_numerical_fit(self):
        r=self.c["source_enumeration_rules"]
        self.assertTrue(r["enumerate_exact_official_pdf_urls_before_value_extraction"])
        self.assertTrue(r["no_value_peeking_during_source_selection"])
        self.assertTrue(r["no_url_pattern_generation"])
        self.assertTrue(r["retain_discarded_candidates_and_reason"])
        self.assertEqual(r["minimum_required_quarter_coverage"],45)
        self.assertTrue(r["year_level_source_selection"])
        self.assertEqual(r["primary_publication_rule"],"January Y+1 Monthly Bulletin for year Y")
        self.assertEqual(r["fixed_fallback_order"],["December Y Monthly Bulletin","February Y+1 Monthly Bulletin"])
        self.assertTrue(r["no_quarter_specific_source_cherry_picking"])
        self.assertTrue(r["fallback_requires_documented_non_value_reason"])
        self.assertTrue(r["freeze_year_source_map_before_numeric_extraction"])

    def test_extraction_is_exact_table_based_not_digitisation(self):
        e=self.c["extraction_rules"]
        self.assertFalse(e["ocr_allowed"])
        self.assertFalse(e["chart_digitisation_allowed"])
        self.assertFalse(e["manual_numeric_transcription_allowed"])
        self.assertEqual(e["exact_table_heading_required"],"11.1. Principalii indicatori de prudențialitate")
        self.assertIn("never convert",e["missing_symbol_policy"].lower())

    def test_materialisation_does_not_open_model_cycle(self):
        p=self.c["promotion_boundary"]
        self.assertFalse(p["canonical_series_mutation_in_this_contract"])
        self.assertFalse(p["mechanism_estimation_authorized"])
        self.assertFalse(p["structural_selection_authorized"])
        self.assertFalse(p["holdout_opening_authorized"])
        self.assertFalse(p["system_dynamics_activation"])
        self.assertFalse(p["behavioural_closure_change"])

if __name__=="__main__":
    unittest.main()
