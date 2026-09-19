from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "data"
    / "source_vintages"
    / "sovereign-yield-quarterly-vintage-2026-09-19"
)
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_source_vintage_promotion_review.json"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class SovereignYieldSourceVintageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(REVIEW.read_text(encoding="utf-8"))

    def test_exact_reviewed_artifact_is_retained_offline(self) -> None:
        expected = {
            item["path"]: item for item in self.review["expected_files"]
        }
        actual = {
            str(path.relative_to(SNAPSHOT))
            for path in SNAPSHOT.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, set(expected))

        for relative, meta in expected.items():
            path = SNAPSHOT / relative
            self.assertEqual(path.stat().st_size, meta["bytes"], relative)
            self.assertEqual(sha256(path), meta["sha256"], relative)

    def test_manifest_preserves_raw_to_normalized_lineage(self) -> None:
        manifest = json.loads(
            (SNAPSHOT / "snapshot_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["snapshot_id"], self.review["snapshot_id"])
        self.assertEqual(
            manifest["source_vintage_contract"],
            "data/provenance/source_vintage_contract.json",
        )
        self.assertEqual(
            manifest["fetcher_script_sha256"],
            self.review["provenance"]["fetcher_script_sha256"],
        )
        self.assertEqual(len(manifest["raw_sources"]), 4)
        self.assertEqual(len(manifest["normalized_outputs"]), 1)
        self.assertEqual(manifest["normalized_outputs"][0]["rows"], 84)

    def test_promotion_does_not_authorize_estimation_or_closure(self) -> None:
        self.assertFalse(self.review["estimation_authorized"])
        boundaries = self.review["hard_boundaries"]
        self.assertTrue(boundaries["no_regression_or_parameter_estimation"])
        self.assertTrue(boundaries["no_system_dynamics_activation"])
        self.assertTrue(boundaries["no_behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
