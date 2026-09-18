from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F4PartialMaterializationTests(unittest.TestCase):
    def generate(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            component = out / "component.json"
            manifest = out / "manifest.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_f4_partial_from_snapshot.py"),
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

    def test_source_vintage_verifies_offline(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_f4_partial_source_vintage.py")],
            cwd=ROOT,
            check=True,
        )

    def test_only_unconditional_rank_unique_core_is_materialized(self):
        component, manifest = self.generate()
        for measure in ("stock", "flow"):
            cells = component["matrices"][measure]
            self.assertEqual(len(cells), 36)
            counts = Counter(c["status"] for c in cells)
            self.assertEqual(counts["UNRESOLVED"], 20)
            self.assertEqual(counts["NOT_APPLICABLE"], 1)
            self.assertEqual(
                counts.get("OBSERVED", 0) + counts.get("DERIVED", 0),
                15,
            )
        self.assertFalse(manifest["conditional_stock_cells_promoted"])

    def test_phase_b_complements_are_promoted_but_conditional_cells_are_not(self):
        component, _ = self.generate()
        stock = {(c["holder"], c["issuer"]): c for c in component["matrices"]["stock"]}
        flow = {(c["holder"], c["issuer"]): c for c in component["matrices"]["flow"]}
        for issuer in ("H", "C", "G"):
            self.assertEqual(stock[("X", issuer)]["status"], "DERIVED")
            self.assertEqual(flow[("X", issuer)]["status"], "DERIVED")
        for pair in (("H", "F"), ("X", "F"), ("H", "BNR"), ("F", "BNR")):
            self.assertEqual(stock[pair]["status"], "UNRESOLVED")

    def test_canonical_and_behavioural_boundaries(self):
        component, manifest = self.generate()
        self.assertFalse(component["complete_F4_matrix"])
        self.assertFalse(component["canonical_benchmark_changed"])
        self.assertFalse(manifest["canonical_benchmark_2025_changed"])
        self.assertFalse(manifest["behavioural_closure_changed"])
        self.assertFalse(manifest["BNR_asset_counterpart_allocation_performed"])


if __name__ == "__main__":
    unittest.main()
