from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_promotion_review.json"
)
WORKFLOW_PATH = (
    ROOT
    / ".github"
    / "workflows"
    / "promote-bnr-bls-missing-round-vintage.yml"
)


class BNRBLSMissingRoundPromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        self.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_review_is_source_vintage_retention_only(self) -> None:
        self.assertEqual(
            self.review["review_result"],
            "APPROVED_FOR_IMMUTABLE_SOURCE_VINTAGE_RETENTION_ONLY",
        )
        effect = self.review["promotion_effect"]
        self.assertTrue(effect["retain_exact_workbook_bytes"])
        self.assertTrue(effect["retain_exact_probe_audit"])
        self.assertFalse(effect["canonical_panel_append_authorized"])
        self.assertFalse(effect["value_extraction_authorized"])
        self.assertFalse(effect["parameter_estimation_authorized"])
        self.assertFalse(effect["model_selection_authorized"])
        self.assertFalse(effect["holdout_opening_authorized"])
        self.assertFalse(effect["system_dynamics_activation"])
        self.assertFalse(effect["behavioural_closure_change"])

    def test_exact_recovered_and_pending_quarters_are_frozen(self) -> None:
        self.assertEqual(
            self.review["recovered_quarters"],
            ["2023-Q2", "2023-Q3", "2024-Q2"],
        )
        self.assertEqual(self.review["pending_quarters"], ["2025-Q2"])

    def test_exact_artifact_and_file_hashes_are_frozen(self) -> None:
        self.assertEqual(self.review["source_artifact_id"], 10587121563)
        self.assertEqual(
            self.review["source_artifact_zip_sha256"],
            "974b97275fdd8c8d57f1a5dbcca67d3aef70ff397a996957bc9eaa2b6b779827",
        )
        expected = {item["path"]: item for item in self.review["expected_files"]}
        self.assertEqual(
            set(expected),
            {
                "2023-q2-candidate-1.xls",
                "2023-q3-candidate-1.xls",
                "2024-q2-candidate-1.xls",
                "bnr_bls_missing_round_workbook_recovery.json",
            },
        )
        for name in (
            "2023-q2-candidate-1.xls",
            "2023-q3-candidate-1.xls",
            "2024-q2-candidate-1.xls",
        ):
            self.assertEqual(
                expected[name]["signature"],
                "OLE2_CFBF_D0CF11E0A1B11AE1",
            )

    def test_workflow_cannot_silently_refetch_or_mutate_panel(self) -> None:
        self.assertIn(
            "promote-bnr-bls-missing-round-vintage",
            self.workflow,
        )
        self.assertIn("actions/artifacts/10587121563/zip", self.workflow)
        self.assertIn(
            self.review["source_artifact_zip_sha256"],
            self.workflow,
        )
        self.assertNotIn("www.bnr.ro", self.workflow)
        self.assertNotIn("data/processed/bnr_bls_realised_rounds.csv", self.workflow)
        self.assertIn('test ! -e "$dest"', self.workflow)

    def test_next_gate_is_semantic_coordinate_verification(self) -> None:
        next_gate = " ".join(self.review["required_next_gate_after_retention"])
        self.assertIn("six preregistered BLS observables", next_gate)
        self.assertIn("deterministic cell extraction", next_gate)
        self.assertIn("without interpolation", next_gate)


if __name__ == "__main__":
    unittest.main()
