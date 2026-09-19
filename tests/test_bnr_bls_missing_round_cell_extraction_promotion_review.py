from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_cell_extraction_promotion_review.json"
)
WORKFLOW = (
    ROOT
    / ".github"
    / "workflows"
    / "promote-bnr-bls-missing-round-cell-extraction-vintage.yml"
)


class BNRBLSMissingRoundCellExtractionPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_promotion_is_retention_only(self) -> None:
        self.assertEqual(
            self.review["review_result"],
            "APPROVED_FOR_IMMUTABLE_CELL_EXTRACTION_VINTAGE_RETENTION_ONLY",
        )
        effect = self.review["promotion_effect"]
        self.assertTrue(effect["retain_exact_extraction_json"])
        self.assertFalse(effect["semantic_admission_authorized"])
        self.assertFalse(effect["canonical_panel_append_authorized"])
        self.assertFalse(effect["parameter_estimation_authorized"])
        self.assertFalse(effect["system_dynamics_activation"])
        self.assertFalse(effect["behavioural_closure_change"])

    def test_artifact_and_exact_file_set_are_frozen(self) -> None:
        self.assertEqual(self.review["source_artifact_id"], 10587291974)
        self.assertEqual(
            self.review["source_artifact_zip_sha256"],
            "9b75298c240ac63628df8b28342fc267a77d0869dee28e30c5b2d7f53ac4efcf",
        )
        self.assertEqual(
            {item["path"] for item in self.review["expected_files"]},
            {
                "bls_2023_aug_cells.json",
                "bls_2023_nov_cells.json",
                "bls_2024_aug_cells.json",
                "bnr_bls_missing_round_cell_extraction_audit.json",
            },
        )

    def test_workflow_cannot_refetch_bnr_or_touch_panel(self) -> None:
        self.assertIn("actions/artifacts/10587291974/zip", self.workflow)
        self.assertNotIn("www.bnr.ro", self.workflow)
        self.assertNotIn("data/processed/bnr_bls_realised_rounds.csv", self.workflow)
        self.assertIn('test ! -e "$dest"', self.workflow)


if __name__ == "__main__":
    unittest.main()
