from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "model" / "calibration_validation" / "bnr_bls_canonical_panel_promotion_review.json"
PANEL = ROOT / "data" / "processed" / "bnr_bls_realised_rounds.csv"
AUDIT = ROOT / "model" / "calibration_validation" / "bnr_bls_cross_round_mapping_audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BNRBLSCanonicalPanelPromotionReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        with PANEL.open("r", encoding="utf-8", newline="") as handle:
            self.rows = list(csv.DictReader(handle))

    def test_review_is_locked_to_exact_candidate_artifact(self) -> None:
        self.assertEqual(
            self.review["review_result"],
            "APPROVED_FOR_CANONICAL_PANEL_PROMOTION_WITH_SINGLE_EXPLICIT_GAP",
        )
        self.assertEqual(self.review["source_workflow_run_id"], 35452800689)
        self.assertEqual(self.review["source_artifact_id"], 10587302658)
        self.assertEqual(
            self.review["source_artifact_zip_sha256"],
            "4d415a330e7eed17694ef51c6184db43a5fe980fbfea9e6342c275eb79743d26",
        )
        files = {item["path"]: item for item in self.review["expected_candidate_files"]}
        self.assertEqual(
            files["bnr_bls_realised_rounds_candidate.csv"]["sha256"],
            "c5dad2c9577431e9765bc02b166e8d5a2b4c4b4c8e761fbb5bbce50f4e6498ff",
        )
        self.assertEqual(
            files["bnr_bls_panel_regeneration_candidate_audit.json"]["sha256"],
            "5a8a5166c6c1edc82020c61ec7c47dccc43084b1ef5249de6c6d7fe2510445c5",
        )

    def test_promoted_canonical_panel_is_exact_reviewed_candidate(self) -> None:
        self.assertEqual(sha256(PANEL), "c5dad2c9577431e9765bc02b166e8d5a2b4c4b4c8e761fbb5bbce50f4e6498ff")
        self.assertEqual(len(self.rows), 11)
        self.assertEqual(
            [row["quarter"] for row in self.rows],
            ["2022-Q4","2023-Q1","2023-Q2","2023-Q3","2023-Q4","2024-Q1","2024-Q2","2024-Q3","2024-Q4","2025-Q1","2025-Q3"],
        )
        self.assertEqual(
            [row["quarter"] for row in self.rows if not row["reference_date"]],
            ["2023-Q2", "2024-Q2"],
        )

    def test_canonical_audit_records_single_explicit_gap_and_provenance(self) -> None:
        self.assertEqual(self.audit["observed_round_count"], 11)
        self.assertEqual(self.audit["missing_quarters"], ["2025-Q2"])
        self.assertAlmostEqual(self.audit["coverage_fraction"], 11 / 12)
        promotion = self.audit["canonical_panel_promotion"]
        self.assertEqual(promotion["source_artifact_id"], 10587302658)
        self.assertEqual(promotion["promoted_canonical_panel_sha256"], "c5dad2c9577431e9765bc02b166e8d5a2b4c4b4c8e761fbb5bbce50f4e6498ff")
        self.assertEqual(promotion["remaining_gap"], "2025-Q2")
        self.assertFalse(promotion["parameter_estimation_authorized"])
        self.assertFalse(promotion["behavioural_closure_change"])

    def test_promotion_does_not_open_behavioural_cycle(self) -> None:
        effect = self.review["promotion_effect"]
        self.assertFalse(effect["parameter_estimation_authorized"])
        self.assertFalse(effect["model_selection_authorized"])
        self.assertFalse(effect["lag_selection_authorized"])
        self.assertFalse(effect["holdout_opening_authorized"])
        self.assertFalse(effect["system_dynamics_activation"])
        self.assertFalse(effect["behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
