from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VINTAGE = (
    ROOT
    / "data"
    / "source_vintages"
    / "fiscal-reaction-ameco-actual-vintage-2026-09-19"
)
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fiscal_reaction_ameco_source_vintage_promotion_review.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FiscalReactionAmecoSourceVintageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(REVIEW.read_text(encoding="utf-8"))
        self.manifest = json.loads(
            (VINTAGE / "snapshot_manifest.json").read_text(encoding="utf-8")
        )

    def test_exact_reviewed_artifact_is_retained_offline(self) -> None:
        expected = {item["path"] for item in self.review["expected_files"]}
        actual = {
            str(path.relative_to(VINTAGE))
            for path in VINTAGE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, expected)
        for item in self.review["expected_files"]:
            path = VINTAGE / item["path"]
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])

    def test_manifest_preserves_raw_to_normalized_lineage(self) -> None:
        self.assertEqual(
            self.manifest["snapshot_id"],
            "fiscal-reaction-ameco-actual-vintage-2026-09-19",
        )
        self.assertEqual(
            self.manifest["materializer_script_sha256"],
            "af6c8cd20342984544b1d36e8a984a62e7b459c56882f5cf279a0c24f056fe3b",
        )
        normalized = self.manifest["normalized_outputs"][0]
        self.assertEqual(
            normalized["sha256"],
            "4d6ab4c737ffb50d48d4866539e6f069b03bc90945bc7a645ac4bd7f88ef2193",
        )
        self.assertEqual(normalized["rows"], 30)
        self.assertEqual(
            set(normalized["derived_from_raw_sha256"]),
            {
                "085e506f0a5ad72e250606d365b70ddd5f3039108393b7d708949164161a5005",
                "6c9aabbba4abdb94ec5728043c5515933ba8c2883b6f1838500e7979813aec55",
                "68a759d5910ccd2304a220191b96bb204866e08d03e380474c576a3cec2de489",
            },
        )

    def test_actual_only_csv_has_frozen_coverage(self) -> None:
        with (VINTAGE / "fiscal_reaction_annual_actual_source.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        years = [int(row["year"]) for row in rows]
        self.assertEqual(len(rows), 30)
        self.assertEqual(years, list(range(1995, 2025)))
        self.assertTrue(
            all(row["source_status"] == "ACTUAL_ONLY_COMPLETE" for row in rows)
        )
        self.assertLessEqual(max(years), 2024)

    def test_source_vintage_does_not_authorize_estimation_or_closure(self) -> None:
        hard = self.manifest["hard_boundaries"]
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])
        self.assertFalse(self.review["estimation_authorized"])


if __name__ == "__main__":
    unittest.main()
