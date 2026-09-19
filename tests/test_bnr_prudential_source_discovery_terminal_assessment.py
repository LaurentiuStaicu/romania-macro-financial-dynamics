from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class BNRPrudentialSourceDiscoveryTerminalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.t=load("model/calibration_validation/bnr_prudential_source_discovery_terminal_assessment.json")
        self.e=load("model/calibration_validation/bnr_prudential_table_source_enumeration.json")
        self.d=load("model/calibration_validation/bnr_prudential_interactive_database_discovery_review.json")
        self.p=load("model/calibration_validation/bank_credit_prudential_population_boundary_review.json")
        self.m=load("model/calibration_validation/mechanism_source_readiness.json")
        self.a=load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json")

    def test_stage_is_closed_without_claiming_source_absence(self):
        self.assertEqual(self.t["status"],"STAGE_CLOSED_FROZEN_INCOMPLETE_UNDER_CURRENT_PUBLIC_DISCOVERY_SURFACE_NO_MODEL_EFFECT")
        self.assertTrue(self.t["exhaustion_assessment"]["current_public_discovery_surface_exhausted"])
        self.assertFalse(self.t["exhaustion_assessment"]["same_query_repetition_authorized"])
        self.assertFalse(self.t["terminal_disposition"]["active_prudential_discovery_task_remains"])
        self.assertFalse(self.e["discovery_methodology"]["search_index_failure_means_absence"])
        self.assertFalse(self.d["web_search_screening"]["search_index_non_discovery_is_absence"])

    def test_pdf_and_interactive_paths_are_frozen_until_new_official_evidence(self):
        self.assertEqual(self.e["status"],"FROZEN_INCOMPLETE_3_OF_11_CURRENT_PUBLIC_DISCOVERY_EXHAUSTED_NO_MODEL_EFFECT")
        self.assertEqual(self.d["disposition"]["interactive_database_path_status"],"FROZEN_INCONCLUSIVE_UNTIL_NEW_OFFICIAL_CATALOG_OR_EXPORT_EVIDENCE")
        self.assertEqual(self.t["terminal_disposition"]["pdf_path_status"],"FROZEN_INCOMPLETE_3_OF_11_UNTIL_NEW_OFFICIAL_LINK_EVIDENCE")
        self.assertEqual(len(self.t["reopen_triggers"]),4)
        self.assertGreaterEqual(len(self.t["non_reopen_conditions"]),5)

    def test_no_model_permission_follows_from_stage_closure(self):
        d=self.t["terminal_disposition"]
        for key in ("source_byte_acquisition_authorized","numeric_extraction_authorized","canonical_series_mutation_authorized","structural_selection_authorized","estimation_or_refit_authorized","holdout_opening_authorized","system_dynamics_activation","behavioural_closure_change"):
            self.assertFalse(d[key])
        effect=self.t["model_effect"]
        self.assertFalse(effect["mechanism_classification_change"])
        self.assertFalse(effect["active_calibration_cycle_open"])
        self.assertFalse(effect["bank_credit_feedback_activation"])

    def test_authority_files_link_terminal_assessment(self):
        path="model/calibration_validation/bnr_prudential_source_discovery_terminal_assessment.json"
        self.assertEqual(self.p["current_source_disposition"]["source_discovery_terminal_assessment"],path)
        credit=next(x for x in self.m["mechanisms"] if x["id"]=="aggregate_bank_credit_response")
        self.assertEqual(credit["bnr_prudential_source_discovery_terminal_assessment"],path)
        self.assertEqual(self.a["bnr_prudential_source_discovery_terminal_assessment"],path)

if __name__=="__main__":
    unittest.main()
