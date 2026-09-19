from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ReferenceModeRecoveryTerminalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.t = load("model/dynamics/reference_mode_recovery_terminal_assessment.json")
        self.refs = load("model/dynamics/reference_modes.json")
        self.manifest = load("model/registries/scientific_baseline_manifest.json")

    def test_stage_closes_at_9_of_10_without_claiming_integrated_closure(self):
        self.assertEqual(
            self.t["status"],
            "STAGE_COMPLETE_FROZEN_9_OF_10_UNDER_CURRENT_PUBLIC_EVIDENCE_BOUNDARY",
        )
        self.assertEqual(self.t["required_reference_modes"], 10)
        self.assertEqual(self.t["ready_reference_modes"], 9)
        self.assertEqual(self.t["blocker_count"], 1)
        self.assertTrue(self.t["disposition"]["reference_mode_recovery_substage_complete"])
        self.assertFalse(self.t["disposition"]["integrated_reference_mode_closure_ready"])
        self.assertFalse(self.t["disposition"]["sectoral_financial_positions_promoted"])

    def test_only_sectoral_financial_positions_remains_blocked(self):
        blocker = self.t["blocker"]
        self.assertEqual(blocker["id"], "sectoral_financial_positions")
        self.assertEqual(blocker["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            blocker["current_public_source_completion_status"],
            "EUROSTAT_INSTRUMENT_SCOPE_FAIL_OECD_S121_SCOPE_FAIL_BNR_ANNUAL_FREQUENCY_TRANSACTION_HISTORY_FAIL",
        )
        mode = next(x for x in self.refs["modes"] if x["id"] == "sectoral_financial_positions")
        self.assertEqual(mode["reference_mode_recovery_stage_status"], self.t["status"])

    def test_all_current_public_paths_have_terminal_classification(self):
        results = {x["id"]: x["result"] for x in self.t["completed_source_paths"]}
        self.assertEqual(
            results["ECB_QSA_INTERNAL_RECOVERY"],
            "EXHAUSTED_AT_FROZEN_SOURCE_AND_RECONCILIATION_BOUNDARY",
        )
        self.assertEqual(
            results["EUROSTAT_COUNTERPART"],
            "DISCOVERY_PASS_SEMANTIC_FAIL_INSTRUMENT_SCOPE",
        )
        self.assertEqual(
            results["OECD_COUNTERPART"],
            "DISCOVERY_PASS_SEMANTIC_FAIL_SECTOR_SCOPE_S121",
        )
        self.assertEqual(
            results["BNR_NATIONAL_FINANCIAL_ACCOUNTS"],
            "ANNUAL_COUNTERPART_STOCK_SEMANTICS_PASS_QUARTERLY_STOCK_TRANSACTION_HISTORY_FAIL",
        )

    def test_stage_completion_does_not_relax_scientific_boundary(self):
        d = self.t["disposition"]
        self.assertEqual(d["reference_mode_readiness"], "9/10")
        self.assertFalse(d["accounting_readiness_change"])
        self.assertFalse(d["active_calibration_cycle_open"])
        self.assertEqual(d["validated_reference_behavioural_mechanisms_change"], 0)
        self.assertFalse(d["system_dynamics_activation"])
        self.assertFalse(d["behavioural_closure_change"])
        self.assertEqual(d["next_operational_state"], "EVIDENCE_TRIGGERED_BASELINE_HOLD")

    def test_baseline_manifest_registers_terminal_reference_stage(self):
        r = self.manifest["canonical_state"]["reference_modes"]
        self.assertEqual(r["recovery_stage_status"], self.t["status"])
        self.assertTrue(r["recovery_substage_complete"])
        self.assertEqual(r["next_operational_state"], "EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertEqual(r["ready_count"], 9)
        self.assertFalse(r["closure_ready"])


if __name__ == "__main__":
    unittest.main()
