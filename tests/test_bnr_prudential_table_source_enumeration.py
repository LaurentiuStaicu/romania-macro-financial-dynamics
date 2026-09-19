from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model"/"calibration_validation"/"bnr_prudential_table_source_enumeration.json"

class BNRPrudentialTableSourceEnumerationTests(unittest.TestCase):
    def setUp(self):
        self.e=json.loads(P.read_text(encoding="utf-8"))

    def test_enumeration_is_explicitly_incomplete_not_negative_evidence(self):
        self.assertEqual(self.e["status"],"INCOMPLETE_SOURCE_ENUMERATION_NO_MODEL_EFFECT")
        self.assertFalse(self.e["completion_gate"]["enumeration_complete"])
        self.assertEqual(self.e["counts"]["required_data_years"],11)
        self.assertEqual(self.e["counts"]["exact_primary_identified"],3)
        self.assertEqual(self.e["counts"]["unresolved_primary"],8)
        unresolved=[x for x in self.e["year_sources"] if x["primary_exact_url"] is None]
        self.assertEqual(len(unresolved),8)
        self.assertTrue(all(x["primary_discovery_status"]=="UNRESOLVED_NOT_NEGATIVE_EVIDENCE" for x in unresolved))

    def test_only_independently_identified_exact_primaries_are_selected(self):
        selected=[x for x in self.e["year_sources"] if x["selected"]]
        self.assertEqual([x["data_year"] for x in selected],[2019,2022,2024])
        self.assertEqual(
            [x["primary_exact_url"] for x in selected],
            [
                "https://www.bnro.ro/files/d/Pubs_ro/Lunare/2020/2020bl01.pdf",
                "https://www.bnro.ro/files/d/Pubs_ro/Lunare/2023/2023bl01.pdf",
                "https://www.bnr.ro/uploads/2025-03-07buletinlunarnr.012025_documentpdf_545_1741348451.pdf",
            ],
        )
        self.assertTrue(all(not x["values_inspected"] for x in selected))
        self.assertTrue(all(not x["numeric_extraction_performed"] for x in selected))
        self.assertTrue(all(not x["source_bytes_retained"] for x in selected))

    def test_discovered_fallback_is_not_selected_while_primary_is_unresolved(self):
        y2016=next(x for x in self.e["year_sources"] if x["data_year"]==2016)
        self.assertFalse(y2016["selected"])
        fallback=y2016["discovered_nonselected_fallback_evidence"][0]
        self.assertEqual(fallback["publication"],"February 2017")
        self.assertEqual(fallback["selection_status"],"NOT_SELECTED_PRIMARY_STATUS_UNRESOLVED")

    def test_no_extraction_or_model_permission_follows(self):
        gate=self.e["completion_gate"]
        for key in (
            "source_byte_acquisition_authorized",
            "numeric_extraction_authorized",
            "canonical_series_mutation_authorized",
            "structural_selection_authorized",
            "estimation_or_refit_authorized",
        ):
            self.assertFalse(gate[key])
        hard=self.e["hard_rules"]
        self.assertTrue(hard["no_url_pattern_generation"])
        self.assertTrue(hard["no_search_index_failure_as_negative_evidence"])
        self.assertTrue(hard["no_fallback_without_documented_primary_source_or_layout_failure"])
        self.assertTrue(hard["no_value_inspection"])

if __name__=="__main__":
    unittest.main()
