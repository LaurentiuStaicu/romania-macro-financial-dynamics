from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ScientificBaselineConsolidationTerminalAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.old = load("model/registries/scientific_baseline_merge_readiness_assessment.json")
        self.term = load("model/registries/scientific_baseline_consolidation_terminal_assessment.json")
        self.model = load("model/registries/model_contract.json")

    def test_original_failure_is_retained_as_historical_snapshot(self) -> None:
        self.assertEqual(
            self.old["status"],
            "NOT_READY_REVIEWABILITY_BLOCKER_SCIENTIFIC_BASELINE_GREEN",
        )
        self.assertEqual(
            self.term["predecessor_assessment"],
            "model/registries/scientific_baseline_merge_readiness_assessment.json",
        )

    def test_scientific_stack_is_exactly_tree_equivalent(self) -> None:
        eq = self.term["exact_tree_equivalence"]
        self.assertTrue(eq["equal"])
        self.assertEqual(
            eq["original_pr_47_terminal_tree"],
            "f8ca0b757b4be46cc19b36564e9f0eed69ef95ce",
        )
        self.assertEqual(
            eq["stacked_pr_51_terminal_tree"],
            eq["original_pr_47_terminal_tree"],
        )

    def test_clean_checkout_is_frozen_as_success(self) -> None:
        clean = self.term["clean_checkout_reproducibility"]
        self.assertEqual(clean["scientific_ci_run_id"], 35459208972)
        self.assertEqual(clean["verify_baseline_job_id"], 105939898290)
        self.assertEqual(clean["conclusion"], "SUCCESS")
        self.assertEqual(
            clean["live_source_refreshes"],
            "INTENTIONALLY_SKIPPED_MANUAL_ONLY",
        )

    def test_irreducible_provenance_exception_is_narrow_and_explicit(self) -> None:
        limits = self.term["github_review_constraints"]
        example = limits["irreducible_example"]
        self.assertGreater(
            example["added_lines"],
            limits["single_file_loadable_diff_lines"],
        )
        self.assertGreater(
            example["bytes"],
            limits["single_file_raw_diff_bytes"],
        )
        exception = self.term["provenance_review_exception"]
        self.assertEqual(exception["status"], "JUSTIFIED_AND_TEST_ENFORCED")
        self.assertEqual(
            exception["scope"],
            "immutable machine-produced retained source vintages only",
        )

    def test_consolidation_is_complete_without_scientific_activation(self) -> None:
        complete = self.term["stage_completion"]
        self.assertTrue(complete["stage_complete"])
        self.assertFalse(complete["autonomous_consolidation_tasks_remaining"])
        effects = self.term["scientific_effects"]
        self.assertFalse(effects["accounting_state_changed"])
        self.assertFalse(effects["reference_mode_state_changed"])
        self.assertFalse(effects["behavioural_mechanism_state_changed"])
        self.assertFalse(effects["calibration_or_refit_authorized"])
        self.assertFalse(effects["system_dynamics_feedback_activation"])
        self.assertFalse(effects["behavioural_closure_activation"])

    def test_next_state_requires_human_repository_decision(self) -> None:
        nxt = self.term["next_state"]
        self.assertEqual(nxt["id"], "HUMAN_REVIEW_DECISION_PENDING")
        self.assertTrue(nxt["ready_for_human_review_decision"])
        self.assertFalse(nxt["automatic_ready_for_review_transition_authorized"])
        self.assertFalse(nxt["automatic_merge_authorized"])
        self.assertFalse(nxt["merge_to_main_authorized_by_this_assessment"])
        self.assertFalse(nxt["release_or_tag_authorized"])
        self.assertFalse(nxt["version_change_authorized"])

    def test_model_contract_retains_terminal_assessment_after_later_review_transition(self) -> None:
        gov = self.model["repository_governance"]
        self.assertEqual(
            gov["consolidation_terminal_assessment"],
            "model/registries/scientific_baseline_consolidation_terminal_assessment.json",
        )
        self.assertTrue(gov["scientific_review_series_complete"])
        self.assertEqual(
            gov["scientific_review_series_terminal_tree"],
            "f8ca0b757b4be46cc19b36564e9f0eed69ef95ce",
        )
        self.assertIn(
            gov["current_merge_readiness_status"],
            {
                "CONSOLIDATION_COMPLETE_HUMAN_REVIEW_DECISION_PENDING",
                "REVIEW_READY_MERGE_DECISION_PENDING",
                "MERGE_AUTHORIZED_INTEGRATION_PENDING",
            },
        )
        self.assertFalse(gov["automatic_merge_authorized"])
        self.assertFalse(gov["release_or_version_change_authorized"])


if __name__ == "__main__":
    unittest.main()
