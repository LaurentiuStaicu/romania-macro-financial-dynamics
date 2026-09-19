from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ValidationRecoveryStageTerminalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.t = load("model/registries/validation_recovery_stage_terminal_assessment.json")
        self.m = load("model/registries/model_contract.json")
        self.b = load("model/registries/scientific_baseline_manifest.json")
        self.a = load("model/accounting/accounting_readiness_gate.json")
        self.r = load("model/calibration_validation/mechanism_source_readiness.json")

    def test_stage_is_complete_only_as_evidence_triggered_hold(self):
        self.assertEqual(
            self.t["status"],
            "STAGE_COMPLETE_EVIDENCE_TRIGGERED_BASELINE_HOLD",
        )
        self.assertEqual(
            self.t["next_operational_state"]["id"],
            "EVIDENCE_TRIGGERED_BASELINE_HOLD",
        )
        self.assertIsNone(
            self.t["next_operational_state"]["active_autonomous_empirical_task"]
        )
        self.assertTrue(
            self.t["stage_completion_rule"][
                "all_currently_admissible_tasks_resolved_or_frozen"
            ]
        )
        self.assertTrue(
            self.t["stage_completion_rule"]["no_mechanism_estimation_authorized"]
        )

    def test_stage_completion_does_not_mean_model_completion_or_release(self):
        self.assertFalse(
            self.t["terminal_state"]["system_dynamics"][
                "complete_endogenous_system_dynamics_model"
            ]
        )
        self.assertFalse(
            self.t["terminal_state"]["system_dynamics"][
                "behavioural_closure_active"
            ]
        )
        self.assertFalse(self.t["no_release_effect"]["release_or_tag_authorized"])
        self.assertFalse(
            self.t["no_release_effect"]["merge_to_main_authorized_by_this_assessment"]
        )
        self.assertFalse(self.t["no_release_effect"]["version_change_authorized"])
        self.assertTrue(
            self.t["no_release_effect"]["human_release_decision_still_required"]
        )

    def test_terminal_accounting_state_preserves_incompleteness(self):
        accounting = self.t["terminal_state"]["accounting"]
        expected = self.a["current_expected_state"]
        self.assertEqual(
            set(accounting["canonical_complete_stock_and_flow_instruments"]),
            set(expected["canonical_complete_stock_and_flow_instruments"]),
        )
        self.assertEqual(
            set(accounting["incomplete_or_partial_instruments"]),
            set(expected["canonical_incomplete_instruments"]),
        )
        self.assertFalse(accounting["full_2025_stock_flow_benchmark_ready"])
        self.assertFalse(accounting["active_unconditional_recovery_task_remains"])

    def test_terminal_mechanism_state_preserves_closed_calibration(self):
        mechanisms = self.t["terminal_state"]["behavioural_mechanisms"]
        self.assertEqual(mechanisms["non_rejected_mechanisms"], 11)
        self.assertEqual(mechanisms["candidate"], 6)
        self.assertEqual(mechanisms["deferred"], 5)
        self.assertEqual(mechanisms["activated"], 0)
        self.assertEqual(mechanisms["validated_reference_behavioural_mechanisms"], 0)
        self.assertEqual(mechanisms["estimation_or_refit_allowed"], 0)
        self.assertFalse(mechanisms["active_calibration_cycle_open"])
        self.assertFalse(self.r["global_state"]["active_calibration_cycle_open"])

    def test_model_contract_and_baseline_register_same_terminal_stage(self):
        self.assertEqual(
            self.m["scientific_stage"]["terminal_assessment"],
            "model/registries/validation_recovery_stage_terminal_assessment.json",
        )
        self.assertEqual(self.m["scientific_stage"]["status"], self.t["status"])
        self.assertFalse(self.m["scientific_stage"]["model_complete"])
        self.assertFalse(self.m["scientific_stage"]["release_ready"])

        stage = self.b["canonical_state"]["scientific_stage"]
        self.assertEqual(stage["status"], self.t["status"])
        self.assertEqual(
            stage["next_operational_state"],
            self.t["next_operational_state"]["id"],
        )
        self.assertTrue(stage["selective_reopen_active"])
        self.assertEqual(
            stage["selective_reopen_mechanism"],
            "fiscal_primary_balance_reaction",
        )
        self.assertIsNone(stage["active_autonomous_empirical_task"])
        self.assertEqual(
            stage["active_manual_empirical_gate"],
            "FISCAL_PRIMARY_BALANCE_CAPB_REALTIME_VINTAGE_MATERIALISATION",
        )
        self.assertFalse(stage["model_complete"])
        self.assertFalse(stage["release_ready"])

    def test_reopen_classes_are_explicit_and_not_queue_exhaustion(self):
        ids = {x["id"] for x in self.t["reopen_classes"]}
        self.assertEqual(
            ids,
            {
                "ACCOUNTING_EVIDENCE_TRIGGER",
                "REFERENCE_MODE_SOURCE_TRIGGER",
                "BEHAVIOURAL_SOURCE_OR_IDENTIFICATION_TRIGGER",
                "PROSPECTIVE_POLICY_EVENT_TRIGGER",
            },
        )
        self.assertIn("Queue exhaustion by itself.", self.t["non_reopen_conditions"])


if __name__ == "__main__":
    unittest.main()
