from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ScientificBaselineMergeReadinessAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.a = load("model/registries/scientific_baseline_merge_readiness_assessment.json")
        self.m = load("model/registries/model_contract.json")

    def test_scientific_gate_passes_but_reviewability_gate_fails(self):
        self.assertEqual(
            self.a["status"],
            "NOT_READY_REVIEWABILITY_BLOCKER_SCIENTIFIC_BASELINE_GREEN",
        )
        self.assertEqual(self.a["scientific_gate"]["verdict"], "PASS")
        self.assertEqual(self.a["reviewability_gate"]["verdict"], "FAIL")
        self.assertTrue(self.a["merge_readiness"]["scientific_integrity_ready"])
        self.assertFalse(self.a["merge_readiness"]["github_reviewability_ready"])
        self.assertFalse(self.a["merge_readiness"]["overall_merge_ready"])

    def test_reviewability_fail_is_material_under_documented_limits(self):
        g = self.a["reviewability_gate"]
        self.assertGreater(
            g["observed_changed_files"],
            g["github_documentation"]["documented_diff_file_limit"],
        )
        self.assertGreater(
            g["observed_additions"],
            g["github_documentation"]["documented_loadable_diff_line_limit"],
        )
        self.assertGreater(
            g["observed_commits"],
            g["github_documentation"]["documented_compare_commit_listing_limit"],
        )
        self.assertTrue(g["exceeds_diff_file_limit"])
        self.assertTrue(g["exceeds_loadable_diff_line_limit"])
        self.assertTrue(g["exceeds_compare_commit_listing_limit"])

    def test_large_vintages_may_not_be_deleted_only_to_shrink_pr(self):
        p = self.a["payload_characterization"]
        self.assertFalse(p["large_source_vintage_payload_is_arbitrary_generated_junk"])
        self.assertTrue(p["exact_offline_vintage_retention_is_scientifically_governed"])
        self.assertEqual(
            p["disposition"],
            "DO_NOT_DELETE_OR_REGENERATE_AD_HOC_TO_SHRINK_PR",
        )
        self.assertIn(
            "Delete retained source vintages solely to make the diff smaller.",
            self.a["prohibited_next_actions"],
        )

    def test_public_metadata_repair_is_complete_without_version_change(self):
        meta = self.a["metadata_consistency"]
        self.assertEqual(meta["required_repair"], "COMPLETED")
        self.assertEqual(
            meta["readme_current_status_after_repair"],
            "EVIDENCE_TRIGGERED_BASELINE_HOLD",
        )
        self.assertEqual(
            meta["v0_1_0_release_note_after_repair"],
            "EXPLICIT_HISTORICAL_SNAPSHOT_WORDING",
        )
        self.assertTrue(
            self.a["merge_readiness"]["metadata_consistency_ready_after_repair"]
        )
        self.assertIn(
            "Change release/tag/version as part of this gate.",
            self.a["prohibited_next_actions"],
        )

    def test_model_contract_retains_old_assessment_but_advances_current_governance(self):
        g = self.m["repository_governance"]
        self.assertEqual(
            g["merge_readiness_assessment"],
            "model/registries/scientific_baseline_merge_readiness_assessment.json",
        )
        self.assertEqual(
            g["consolidation_terminal_assessment"],
            "model/registries/scientific_baseline_consolidation_terminal_assessment.json",
        )
        self.assertNotEqual(
            g["current_merge_readiness_status"],
            self.a["status"],
        )
        self.assertIn(
            g["current_merge_readiness_status"],
            {
                "CONSOLIDATION_COMPLETE_HUMAN_REVIEW_DECISION_PENDING",
                "REVIEW_READY_MERGE_DECISION_PENDING",
                "MERGE_AUTHORIZED_INTEGRATION_PENDING",
            },
        )
        self.assertFalse(g["automatic_merge_authorized"])
        self.assertFalse(g["release_or_version_change_authorized"])

    def test_recommended_next_state_is_consolidation_not_merge(self):
        self.assertEqual(
            self.a["recommended_next_state"],
            "DRAFT_CONSOLIDATION_REQUIRED_BEFORE_REVIEW_READY",
        )
        self.assertFalse(
            self.a["merge_readiness"]["human_merge_decision_authorized_by_this_assessment"]
        )


if __name__ == "__main__":
    unittest.main()
