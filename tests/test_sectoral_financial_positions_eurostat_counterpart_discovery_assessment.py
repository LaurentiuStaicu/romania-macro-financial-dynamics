from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "model" / "dynamics" / "sectoral_financial_positions_eurostat_counterpart_discovery_assessment.json"
VINTAGE = ROOT / "data" / "source_vintages" / "sectoral-financial-positions-eurostat-counterpart-discovery-vintage-2026-09-19"


class EurostatCounterpartDiscoveryAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))

    def test_discovery_pass_is_retained_without_promotion(self) -> None:
        d = self.assessment["discovery_result"]
        self.assertEqual(d["state"], "PASS")
        self.assertEqual(d["http_status"], 200)
        self.assertEqual(d["non_null_observation_count"], 64995)
        self.assertEqual(
            d["raw_response_sha256"],
            "547c9e65c60900aa259ba547efb60faedbaa22e8d8a66e1caed6cbd2cbd189ae",
        )
        self.assertFalse(self.assessment["reference_mode_promotion"])
        self.assertEqual(self.assessment["readiness_count_change"], 0)

    def test_semantic_review_fails_only_on_frozen_instrument_scope(self) -> None:
        r = self.assessment["review_results"]
        self.assertEqual(r["SECTOR_MAPPING"]["status"], "PASS")
        self.assertEqual(r["COUNTERPART_ORIENTATION"]["status"], "PASS")
        self.assertEqual(r["STOCK_FLOW_SEMANTICS"]["status"], "PASS")
        self.assertEqual(r["ASSET_LIABILITY_SEMANTICS"]["status"], "PASS")
        self.assertEqual(r["UNIT_SCALING"]["status"], "PASS")
        self.assertEqual(r["CONSOLIDATION_AND_VALUATION"]["status"], "PASS")
        self.assertEqual(r["LINEAGE"]["status"], "PASS")
        self.assertEqual(r["INSTRUMENT_MAPPING"]["status"], "FAIL")
        complete = r["INSTRUMENT_MAPPING"]["exact_or_complete"]
        self.assertTrue(complete["F3"])
        self.assertTrue(complete["F4"])
        for item in ("F2", "F5", "F6", "F7", "F8"):
            self.assertFalse(complete[item])
        self.assertEqual(
            self.assessment["verdict"],
            "FAIL_REQUIRED_INSTRUMENT_SCOPE_INCOMPLETE",
        )
        self.assertFalse(self.assessment["exact_historical_extraction_authorized"])

    def test_review_did_not_use_values_or_reconciliation(self) -> None:
        self.assertFalse(self.assessment["value_review_performed"])
        self.assertFalse(self.assessment["reconciliation_review_performed"])
        self.assertFalse(self.assessment["historical_phase_A_D_reinterpreted"])

    def test_compact_vintage_manifest_retains_exact_artifact_identity(self) -> None:
        manifest = json.loads((VINTAGE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["github_actions"]["workflow_run_attempt"], 2)
        self.assertEqual(manifest["github_actions"]["artifact_id"], 10586785016)
        self.assertEqual(
            manifest["exact_raw_response"]["sha256"],
            "547c9e65c60900aa259ba547efb60faedbaa22e8d8a66e1caed6cbd2cbd189ae",
        )
        self.assertTrue(manifest["exact_raw_response"]["retained_in_exact_workflow_artifact"])
        self.assertTrue(manifest["compact_audit"]["repository_resident"])


if __name__ == "__main__":
    unittest.main()
