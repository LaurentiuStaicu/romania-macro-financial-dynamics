from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F3MaterializationTests(unittest.TestCase):
    def test_source_vintage_verifies_offline(self) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_f3_source_vintage.py")],
            cwd=ROOT,
            check=True,
        )

    def test_generator_changes_only_f3_and_produces_complete_matrix(self) -> None:
        baseline_path = ROOT / "model" / "accounting" / "benchmark_2025.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            benchmark_out = out / "benchmark_2025.json"
            materialization_out = out / "f3_materialization_manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_f3_benchmark_from_snapshot.py"),
                    "--benchmark-input",
                    str(baseline_path),
                    "--benchmark-output",
                    str(benchmark_out),
                    "--materialization-output",
                    str(materialization_out),
                ],
                cwd=ROOT,
                check=True,
            )
            generated = json.loads(benchmark_out.read_text(encoding="utf-8"))
            manifest = json.loads(materialization_out.read_text(encoding="utf-8"))

        for instrument in baseline["matrices"]:
            if instrument != "F3":
                self.assertEqual(
                    generated["matrices"][instrument],
                    baseline["matrices"][instrument],
                )

        self.assertEqual(
            manifest["counts"]["stock"],
            {"OBSERVED": 24, "DERIVED": 11, "NOT_APPLICABLE": 1},
        )
        self.assertEqual(
            manifest["counts"]["flow"],
            {"OBSERVED": 24, "DERIVED": 11, "NOT_APPLICABLE": 1},
        )

        for measure in ("stock", "flow"):
            overrides = generated["matrices"]["F3"][measure]["overrides"]
            self.assertEqual(len(overrides), 36)
            statuses = {}
            for item in overrides:
                statuses[item["status"]] = statuses.get(item["status"], 0) + 1
            self.assertEqual(
                statuses,
                {"OBSERVED": 24, "DERIVED": 11, "NOT_APPLICABLE": 1},
            )
            observed = [item for item in overrides if item["status"] == "OBSERVED"]
            self.assertTrue(
                all(
                    item["source_series_key"].startswith("QSA.Q.")
                    for item in observed
                )
            )
            x_to_x = [
                item
                for item in overrides
                if item["holder"] == "X" and item["issuer"] == "X"
            ][0]
            self.assertEqual(x_to_x["status"], "NOT_APPLICABLE")
            self.assertIsNone(x_to_x["value"])

    def test_materialization_manifest_all_reconciliations_pass(self) -> None:
        audit = json.loads(
            (
                ROOT
                / "data"
                / "source_vintages"
                / "accounting-f3-2025-vintage-2026-09-18"
                / "qsa_f3_coverage_audit.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            audit["aggregate_reconciliation_status_counts"],
            {"PASS": 20},
        )
        self.assertEqual(
            audit["maturity_reconciliation_status_counts"],
            {"PASS": 2},
        )


if __name__ == "__main__":
    unittest.main()
