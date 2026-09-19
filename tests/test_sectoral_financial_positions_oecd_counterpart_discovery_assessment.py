from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "model" / "dynamics" / "sectoral_financial_positions_oecd_counterpart_discovery_assessment.json"
VINTAGE = ROOT / "data" / "source_vintages" / "sectoral-financial-positions-oecd-counterpart-discovery-vintage-2026-09-19"


class OECDCounterpartDiscoveryAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))

    def test_discovery_pass_is_retained_without_promotion(self) -> None:
        d = self.assessment["discovery_result"]
        self.assertEqual(d["state"], "PASS")
        self.assertEqual(d["stocks_row_count"], 105435)
        self.assertEqual(d["flows_row_count"], 105435)
        self.assertFalse(self.assessment["reference_mode_promotion"])
        self.assertEqual(self.assessment["readiness_count_change"], 0)

    def test_instrument_scope_passes_but_sector_scope_fails(self) -> None:
        r = self.assessment["review_results"]
        self.assertEqual(r["INSTRUMENT_MAPPING"]["status"], "PASS")
        self.assertEqual(
            r["INSTRUMENT_MAPPING"]["exact_source_codes_present_in_both_stocks_and_flows"],
            ["F2", "F3", "F4", "F5", "F6", "F7", "F8"],
        )
        self.assertEqual(r["SECTOR_MAPPING"]["status"], "FAIL")
        self.assertIn("S121", r["SECTOR_MAPPING"]["mappings_not_supported"]["BNR"])
        self.assertIn("S12 - S121", r["SECTOR_MAPPING"]["mappings_not_supported"]["F"])
        self.assertEqual(
            self.assessment["verdict"],
            "FAIL_REQUIRED_SECTOR_SCOPE_INCOMPLETE",
        )
        self.assertFalse(self.assessment["exact_historical_extraction_authorized"])

    def test_other_semantic_dimensions_pass_without_value_fit(self) -> None:
        r = self.assessment["review_results"]
        for key in (
            "COUNTERPART_ORIENTATION",
            "STOCK_FLOW_SEMANTICS",
            "ASSET_LIABILITY_SEMANTICS",
            "UNIT_SCALING",
            "CONSOLIDATION_AND_VALUATION",
            "LINEAGE",
        ):
            self.assertEqual(r[key]["status"], "PASS")
        self.assertFalse(self.assessment["value_review_performed"])
        self.assertFalse(self.assessment["reconciliation_review_performed"])
        self.assertFalse(self.assessment["historical_phase_A_D_reinterpreted"])

    def test_inventory_and_artifact_identity_are_retained(self) -> None:
        inventory = json.loads((VINTAGE / "semantic_inventory.json").read_text(encoding="utf-8"))
        manifest = json.loads((VINTAGE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            inventory["common"]["absent_required_sector_codes"],
            ["S121"],
        )
        self.assertEqual(
            inventory["common"]["required_rmd_instrument_codes_present"],
            ["F2", "F3", "F4", "F5", "F6", "F7", "F8"],
        )
        self.assertEqual(manifest["github_actions"]["workflow_run_attempt"], 2)
        self.assertEqual(manifest["github_actions"]["artifact_id"], 10586683826)
        self.assertEqual(
            manifest["github_actions"]["artifact_zip_sha256"],
            "045265e3a32f9ec28c713029b9d8f7e5495ed50c9f3b411aa3696a680f60550e",
        )
        self.assertTrue(manifest["retained_in_exact_workflow_artifact"])
        self.assertFalse(manifest["exact_raw_files_repository_resident"])


if __name__ == "__main__":
    unittest.main()
