from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

class BNRPrudentialInteractiveDatabaseDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.c=load("model/calibration_validation/bnr_prudential_interactive_database_discovery_contract.json")
        self.r=load("model/calibration_validation/bnr_prudential_interactive_database_discovery_review.json")
        self.p=load("model/calibration_validation/bank_credit_prudential_population_boundary_review.json")
        self.m=load("model/calibration_validation/mechanism_source_readiness.json")
        self.a=load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json")

    def test_discovery_requires_exact_machine_readable_population_match(self):
        req=self.c["discovery_pass_requires"]
        for key in ("official_bnr_host_or_documented_bnr_export","stable_dataset_or_series_identifier","machine_readable_export_or_api","exact_population_metadata","exact_variable_semantics","quarterly_frequency","coverage_including_all_41_common_window_quarters"):
            self.assertTrue(req[key])

    def test_current_result_is_inconclusive_not_absence(self):
        self.assertEqual(self.r["status"],"OFFICIAL_DATABASE_CONFIRMED_TARGET_SERIES_NOT_IDENTIFIED_STAGE_FROZEN")
        self.assertFalse(self.r["web_search_screening"]["exact_target_machine_readable_series_identified"])
        self.assertFalse(self.r["web_search_screening"]["search_index_non_discovery_is_absence"])
        self.assertEqual(self.r["disposition"]["interactive_database_path_status"],"FROZEN_INCONCLUSIVE_UNTIL_NEW_OFFICIAL_CATALOG_OR_EXPORT_EVIDENCE")

    def test_pdf_path_is_frozen_and_model_cycle_closed(self):
        d=self.r["disposition"]
        self.assertFalse(d["pdf_path_remains_active"])
        self.assertTrue(d["stage_closed"])
        self.assertTrue(d["reopen_requires_new_official_evidence"])
        for key in ("source_byte_acquisition_authorized","numeric_extraction_authorized","canonical_series_mutation_authorized","structural_selection_authorized","estimation_or_refit_authorized"):
            self.assertFalse(d[key])

    def test_authority_registries_link_same_review(self):
        path="model/calibration_validation/bnr_prudential_interactive_database_discovery_review.json"
        self.assertEqual(self.p["current_source_disposition"]["interactive_database_discovery_review"],path)
        credit=next(x for x in self.m["mechanisms"] if x["id"]=="aggregate_bank_credit_response")
        self.assertEqual(credit["bnr_prudential_interactive_database_discovery_review"],path)
        self.assertEqual(self.a["bnr_prudential_interactive_database_discovery_review"],path)
        self.assertEqual(
            self.r["terminal_assessment"],
            "model/calibration_validation/bnr_prudential_source_discovery_terminal_assessment.json",
        )
        self.assertTrue(
            self.r["hard_rules"]["no_repeat_same_discovery_without_new_official_trigger"]
        )

if __name__=="__main__":
    unittest.main()
