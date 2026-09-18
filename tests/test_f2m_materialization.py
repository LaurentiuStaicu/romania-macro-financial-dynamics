from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F2MMaterializationTests(unittest.TestCase):
    def generate(self) -> tuple[dict, dict]:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            component = out / "component.json"
            manifest = out / "manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_f2m_component_from_snapshot.py"),
                    "--component-output", str(component),
                    "--manifest-output", str(manifest),
                ],
                cwd=ROOT,
                check=True,
            )
            return (
                json.loads(component.read_text(encoding="utf-8")),
                json.loads(manifest.read_text(encoding="utf-8")),
            )

    def test_source_vintage_verifies_offline(self) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_f2m_source_vintage.py")],
            cwd=ROOT,
            check=True,
        )

    def test_expected_component_classification_counts(self) -> None:
        component, _ = self.generate()
        expected = {
            "stock": {"OBSERVED": 10, "DERIVED": 13, "NOT_APPLICABLE": 13},
            "flow": {"DERIVED": 23, "NOT_APPLICABLE": 13},
        }
        for measure, expected_counts in expected.items():
            cells = component["matrices"][measure]
            self.assertEqual(len(cells), 36)
            self.assertEqual(dict(Counter(c["status"] for c in cells)), expected_counts)
            self.assertEqual(len({(c["holder"], c["issuer"]) for c in cells}), 36)
            for cell in cells:
                if cell["status"] == "NOT_APPLICABLE":
                    self.assertIsNone(cell["value"])
                else:
                    self.assertIsInstance(cell["value"], (int, float))
                    self.assertEqual(cell["value"], round(cell["value"], 2))

    def test_external_complements_are_exact_derived_cells(self) -> None:
        component, _ = self.generate()
        for measure in ("stock", "flow"):
            external = [
                c for c in component["matrices"][measure]
                if c["issuer"] == "X" and c["holder"] != "X"
            ]
            self.assertEqual(len(external), 5)
            for cell in external:
                self.assertEqual(cell["status"], "DERIVED")
                self.assertEqual(
                    cell["derivation"]["identity"],
                    "holder_W0_F2M_assets - complete_resident_issuer_F2M_submatrix",
                )
                self.assertIn("all PASS", cell["derivation"]["independent_control"])

    def test_all_available_aggregate_controls_pass(self) -> None:
        _, manifest = self.generate()
        for rec in manifest["aggregate_reconciliation"]:
            if rec["published_control_million_RON"] is not None:
                self.assertEqual(rec["status"], "PASS")
                self.assertLessEqual(abs(rec["residual_million_RON"]), 0.1)

    def test_total_f2_and_behavioural_closure_remain_untouched(self) -> None:
        component, manifest = self.generate()
        self.assertEqual(component["instrument"], "F2M")
        self.assertTrue(component["component_only"])
        self.assertFalse(component["canonical_total_F2_population_allowed"])
        self.assertEqual(
            component["F21_currency_status"],
            "UNRESOLVED_BILATERAL_CURRENCY_ALLOCATION",
        )
        self.assertEqual(manifest["total_F2_status"], "INCOMPLETE_BLOCKED_BY_F21_CURRENCY")
        self.assertFalse(manifest["canonical_total_F2_benchmark_changed"])
        self.assertFalse(manifest["behavioural_closure_changed"])


if __name__ == "__main__":
    unittest.main()
