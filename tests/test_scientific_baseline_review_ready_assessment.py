from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ScientificBaselineReviewReadyAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load("model/registries/scientific_baseline_review_ready_assessment.json")
        self.m = load("model/registries/model_contract.json")

    def test_transition_is_review_only(self) -> None:
        self.assertEqual(self.a["status"], "REVIEW_READY_MERGE_DECISION_PENDING")
        d = self.a["decision"]
        self.assertTrue(d["human_continuation_authorized"])
        self.assertEqual(d["authorized_scope"], "MARK_CONSOLIDATED_STACK_READY_FOR_REVIEW")
        self.assertEqual(d["pull_requests"], [48, 49, 50, 51, 52])
        self.assertTrue(d["all_marked_ready_for_review"])
        self.assertFalse(d["merge_authorized"])

    def test_transition_has_no_scientific_effect(self) -> None:
        e = self.a["scientific_effects"]
        self.assertFalse(e["scientific_tree_changed_by_ready_transition"])
        self.assertFalse(e["accounting_state_changed"])
        self.assertFalse(e["reference_mode_state_changed"])
        self.assertFalse(e["mechanism_state_changed"])
        self.assertFalse(e["calibration_or_refit_authorized"])
        self.assertFalse(e["system_dynamics_activation"])
        self.assertFalse(e["behavioural_closure_activation"])

    def test_model_contract_retains_review_ready_assessment_after_merge_authorization(self) -> None:
        g = self.m["repository_governance"]
        self.assertEqual(
            g["review_ready_assessment"],
            "model/registries/scientific_baseline_review_ready_assessment.json",
        )
        self.assertFalse(g["pull_request_must_remain_draft"])
        self.assertFalse(g["human_review_decision_required"])
        self.assertIn(
            g["current_merge_readiness_status"],
            {
                "REVIEW_READY_MERGE_DECISION_PENDING",
                "MERGE_AUTHORIZED_INTEGRATION_PENDING",
            },
        )
        self.assertFalse(g["automatic_merge_authorized"])
        self.assertFalse(g["release_or_version_change_authorized"])

    def test_next_state_still_requires_merge_decision(self) -> None:
        n = self.a["next_state"]
        self.assertEqual(n["id"], "MERGE_DECISION_PENDING")
        self.assertTrue(n["review_ready"])
        self.assertTrue(n["merge_decision_required"])
        self.assertFalse(n["automatic_merge_authorized"])
        self.assertFalse(n["merge_to_main_authorized_by_this_assessment"])
        self.assertFalse(n["release_or_tag_authorized"])
        self.assertFalse(n["version_change_authorized"])


if __name__ == "__main__":
    unittest.main()
