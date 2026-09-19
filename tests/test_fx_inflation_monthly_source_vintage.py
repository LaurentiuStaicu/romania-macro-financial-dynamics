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
    / "fx-inflation-monthly-levels-vintage-2026-09-19"
)
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_source_vintage_promotion_review.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FxInflationMonthlySourceVintageTests(unittest.TestCase):
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

    def test_manifest_preserves_three_source_lineage(self) -> None:
        self.assertEqual(
            self.manifest["snapshot_id"],
            "fx-inflation-monthly-levels-vintage-2026-09-19",
        )
        self.assertEqual(
            self.manifest["materializer_script_sha256"],
            "d7775966c706a78fdd7fcbeaa2f62b859394e467bc48af875a756af1be1636e0",
        )
        normalized = self.manifest["normalized_outputs"][0]
        self.assertEqual(
            normalized["sha256"],
            "bba995fe9e435cc124a5b66c035a5e65085ef705f912bf6c018dcd0d4a4748ea",
        )
        self.assertEqual(normalized["rows"], 294)
        self.assertEqual(normalized["transformations"], [])
        self.assertEqual(
            set(normalized["derived_from_raw_sha256"]),
            {
                "7354d85c7106f16c3905c885d6cbf2c7581fd2a10652d8f0d8456b79b4f56254",
                "e498c33240446913d26402ce8e1a1d30fc0552e989a888f76e684143dc95a0cf",
                "1c9d9541d69fb3dbd2ddbda4a066e2025c76033840e891e328c19e8022d94604",
            },
        )

    def test_common_level_csv_is_complete_and_untransformed(self) -> None:
        with (VINTAGE / "fx_inflation_monthly_raw_source.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 294)
        self.assertEqual(rows[0]["period"], "2002-01")
        self.assertEqual(rows[-1]["period"], "2026-06")
        self.assertTrue(
            all(
                row["source_completeness"] == "COMPLETE_LEVELS_ONLY"
                for row in rows
            )
        )

    def test_vintage_does_not_authorize_estimation_or_closure(self) -> None:
        hard = self.manifest["hard_boundaries"]
        self.assertTrue(hard["level_only_materialisation"])
        self.assertTrue(hard["no_log_difference"])
        self.assertTrue(hard["no_lag_selection"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])
        self.assertFalse(self.review["estimation_authorized"])


if __name__ == "__main__":
    unittest.main()
