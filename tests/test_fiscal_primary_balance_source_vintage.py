from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = (
    ROOT
    / "data"
    / "source_vintages"
    / "fiscal-primary-balance-quarterly-vintage-2026-09-19"
)
REVIEW = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fiscal_primary_balance_source_vintage_promotion_review.json"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class FiscalPrimaryBalanceSourceVintageTests(unittest.TestCase):
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

    def test_manifest_preserves_matched_vintage_lineage(self) -> None:
        manifest = json.loads(
            (SNAPSHOT / "snapshot_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["snapshot_id"], self.review["snapshot_id"])
        self.assertEqual(len(manifest["raw_sources"]), 2)
        updates = {
            source["dataset_updated"] for source in manifest["raw_sources"]
        }
        self.assertEqual(updates, {"2026-07-21T11:00:00+0200"})
        self.assertEqual(manifest["normalized_outputs"][0]["rows"], 105)

    def test_primary_balance_identity_holds_for_every_retained_quarter(self) -> None:
        path = SNAPSHOT / "fiscal_primary_balance_quarterly_source.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 105)
        self.assertEqual(rows[0]["period"], "2000-Q1")
        self.assertEqual(rows[-1]["period"], "2026-Q1")
        for row in rows:
            overall = float(row["net_lending_borrowing_pct_gdp"])
            interest = float(row["interest_expenditure_pct_gdp"])
            primary = float(row["primary_balance_pct_gdp"])
            self.assertAlmostEqual(primary, overall + interest, places=10)
            self.assertEqual(row["source_completeness"], "COMPLETE")

    def test_snapshot_does_not_authorize_fiscal_reaction_estimation(self) -> None:
        self.assertFalse(self.review["estimation_authorized"])
        boundaries = self.review["hard_boundaries"]
        self.assertTrue(boundaries["no_parameter_estimation"])
        self.assertTrue(boundaries["no_output_gap_construction"])
        self.assertTrue(boundaries["no_debt_gap_construction"])
        self.assertTrue(boundaries["no_regime_inference"])
        self.assertTrue(boundaries["no_system_dynamics_activation"])


if __name__ == "__main__":
    unittest.main()
