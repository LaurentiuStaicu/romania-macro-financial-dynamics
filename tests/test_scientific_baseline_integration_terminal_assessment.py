from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ScientificBaselineIntegrationTerminalAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load("model/registries/scientific_baseline_integration_terminal_assessment.json")
        self.m = load("model/registries/model_contract.json")

    def test_stack_is_recorded_as_fully_merged(self) -> None:
        self.assertEqual(
            [item["pull_request"] for item in self.a["merged_stack"]],
            [48, 49, 50, 51, 52],
        )
        self.assertEqual(
            self.a["original_audit_pull_request"]["disposition"],
            "CLOSED_SUPERSEDED_NOT_MERGED_DIRECTLY",
        )

    def test_post_merge_main_verification_is_green(self) -> None:
        verify = self.a["post_merge_verification"]
        self.assertEqual(
            verify["main_head_after_stack_merge"],
            "9efab3020d10ade5e2d94f5df1e44f91d88ea08a",
        )
        self.assertEqual(verify["scientific_ci"]["conclusion"], "SUCCESS")
        self.assertEqual(verify["f2m_component_materialization"]["conclusion"], "SUCCESS")
        self.assertEqual(verify["f4_partial_materialization"]["conclusion"], "SUCCESS")
        self.assertFalse(verify["canonical_reproduction_requires_live_network"])

    def test_scientific_state_remains_incomplete_and_frozen(self) -> None:
        s = self.a["final_scientific_state"]
        self.assertEqual(s["scientific_stage"], "STAGE_COMPLETE_EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertEqual(s["next_operational_state"], "EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertFalse(s["model_complete"])
        self.assertFalse(s["release_ready"])
        self.assertEqual(s["canonical_complete_stock_and_flow_instruments"], ["F3"])
        self.assertFalse(s["canonical_full_2025_stock_flow_benchmark_ready"])
        self.assertEqual(s["reference_modes_ready"], 9)
        self.assertEqual(s["reference_modes_required"], 10)
        self.assertEqual(s["validated_reference_behavioural_mechanisms"], 0)
        self.assertFalse(s["active_calibration_cycle_open"])
        self.assertFalse(s["behavioural_closure_active"])
        self.assertFalse(s["complete_endogenous_system_dynamics_model"])

    def test_integration_has_no_scientific_activation_or_release_effect(self) -> None:
        effects = self.a["integration_effects"]
        for key, value in effects.items():
            self.assertFalse(value, key)

    def test_model_contract_is_terminal_for_repository_integration(self) -> None:
        g = self.m["repository_governance"]
        self.assertEqual(
            g["integration_terminal_assessment"],
            "model/registries/scientific_baseline_integration_terminal_assessment.json",
        )
        self.assertEqual(g["current_merge_readiness_status"], "INTEGRATION_COMPLETE")
        self.assertTrue(g["integration_complete"])
        self.assertFalse(g["merge_decision_required"])
        self.assertFalse(g["automatic_merge_authorized"])
        self.assertFalse(g["release_or_version_change_authorized"])


if __name__ == "__main__":
    unittest.main()
