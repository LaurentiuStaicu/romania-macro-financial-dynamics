from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = (
    ROOT / "model" / "dynamics"
    / "sectoral_financial_positions_s1n_boundary_diagnostic_assessment.json"
)


class SectoralFinancialPositionsS1NBoundaryAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = json.loads(ASSESSMENT.read_text(encoding="utf-8"))

    def test_exact_negative_artifact_is_frozen(self) -> None:
        workflow = self.a["reviewed_workflow"]
        self.assertEqual(workflow["artifact_id"], 10582468766)
        self.assertEqual(
            workflow["artifact_zip_sha256"],
            "71c3b879233b4f088264fc05382c2e6b2c3f906ed9e059d2469f74ee6a267d0f",
        )
        self.assertEqual(len(self.a["expected_files"]), 9)

    def test_result_is_http_negative_not_network_failure(self) -> None:
        outcome = self.a["source_outcome"]
        self.assertEqual(outcome["series_requested"], 8)
        self.assertEqual(outcome["http_404_count"], 8)
        self.assertEqual(outcome["network_error_count"], 0)
        self.assertFalse(outcome["coverage_gate_pass"])
        self.assertFalse(outcome["explanatory_gate_pass"])
        self.assertEqual(
            outcome["disposition"],
            "NO_REOPEN_EVIDENCE_FROM_S1N",
        )

    def test_negative_result_changes_no_scientific_readiness(self) -> None:
        effects = self.a["hard_effects"]
        self.assertFalse(effects["reference_mode_promotion"])
        self.assertEqual(effects["reference_mode_readiness_change"], 0)
        self.assertFalse(effects["historical_A_D_reinterpreted"])
        self.assertFalse(effects["phase_C_envelope_changed"])
        self.assertFalse(effects["accounting_readiness_changed"])
        self.assertFalse(effects["behavioural_closure_changed"])
        self.assertFalse(effects["residual_allocation_performed"])


if __name__ == "__main__":
    unittest.main()
