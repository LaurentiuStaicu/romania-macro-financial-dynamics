from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ScientificBaselineMergeAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load("model/registries/scientific_baseline_merge_authorization.json")
        self.m = load("model/registries/model_contract.json")

    def test_scope_is_stack_merge_only(self) -> None:
        self.assertEqual(self.a["status"], "MERGE_AUTHORIZED_INTEGRATION_PENDING")
        auth = self.a["authorization"]
        self.assertEqual(auth["pull_requests_in_order"], [48, 49, 50, 51, 52])
        self.assertEqual(auth["merge_order"], "BOTTOM_UP")
        self.assertEqual(auth["target_branch"], "main")
        self.assertEqual(auth["merge_method"], "merge")

    def test_pre_merge_gate_is_green(self) -> None:
        gate = self.a["pre_merge_gate"]
        self.assertTrue(gate["all_stack_prs_open"])
        self.assertTrue(gate["all_stack_prs_ready_for_review"])
        self.assertTrue(gate["all_stack_prs_mergeable"])
        self.assertTrue(gate["all_stack_prs_mergeable_state_clean"])
        self.assertEqual(gate["blocking_review_threads"], 0)
        self.assertEqual(gate["blocking_review_findings"], 0)
        self.assertTrue(gate["triggered_scientific_ci_green"])

    def test_merge_authorization_does_not_activate_model(self) -> None:
        effects = self.a["scientific_effects"]
        self.assertFalse(effects["merge_authorization_changes_scientific_content"])
        self.assertFalse(effects["accounting_state_changed"])
        self.assertFalse(effects["reference_mode_state_changed"])
        self.assertFalse(effects["behavioural_mechanism_state_changed"])
        self.assertFalse(effects["calibration_or_refit_authorized"])
        self.assertFalse(effects["holdout_opening_authorized"])
        self.assertFalse(effects["system_dynamics_feedback_activation"])
        self.assertFalse(effects["behavioural_closure_activation"])

    def test_repository_governance_is_merge_authorized_but_not_release_authorized(self) -> None:
        g = self.m["repository_governance"]
        self.assertEqual(
            g["merge_authorization_assessment"],
            "model/registries/scientific_baseline_merge_authorization.json",
        )
        self.assertEqual(g["current_merge_readiness_status"], "MERGE_AUTHORIZED_INTEGRATION_PENDING")
        self.assertFalse(g["merge_decision_required"])
        self.assertTrue(g["human_merge_authorized"])
        self.assertFalse(g["automatic_merge_authorized"])
        self.assertFalse(g["release_or_version_change_authorized"])


if __name__ == "__main__":
    unittest.main()
