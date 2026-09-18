from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F7AggregateRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f7_aggregate_rank_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.assessment = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f7_aggregate_rank_assessment.json"
            ).read_text(encoding="utf-8")
        )

    def test_rank_gate_forbids_zero_and_allocation_shortcuts(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(
            rules["rank_and_nullity_must_use_exact_rational_coefficient_arithmetic"]
        )
        self.assertTrue(rules["zero_aggregate_must_not_create_bilateral_zero_equations"])
        self.assertTrue(rules["no_nonnegativity_constraint"])
        self.assertTrue(rules["no_issuer_applicability_assumption"])
        self.assertTrue(rules["no_materiality_assumption"])
        self.assertTrue(rules["no_synthetic_allocation"])

    def test_retained_assessment_freezes_without_materialization(self) -> None:
        self.assertEqual(
            self.assessment["verdict"],
            "FREEZE_F7_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY",
        )
        self.assertEqual(
            self.assessment["unconditional_identification"]["stock"]["rank"],
            11,
        )
        self.assertEqual(
            self.assessment["unconditional_identification"]["flow_2025"]["rank"],
            10,
        )
        self.assertEqual(
            self.assessment["unconditional_identification"]["stock"]["unique_cell_count"],
            0,
        )
        self.assertEqual(
            self.assessment["unconditional_identification"]["flow_2025"]["unique_cell_count"],
            0,
        )
        self.assertFalse(
            self.assessment["disposition"]["bilateral_materialization"]
        )

    def test_offline_rank_audit_reproduces_assessment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "audit_f7_aggregate_rank.py"),
                    "--out",
                    tmp,
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            report = json.loads(
                (Path(tmp) / "f7_aggregate_rank_audit.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            report["disposition"],
            "FREEZE_F7_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY",
        )
        for measure in ("stock", "flow_2025"):
            observed = report["analyses"][measure]["unconditional_identification"]
            retained = self.assessment["unconditional_identification"][measure]
            self.assertEqual(observed["rank"], retained["rank"])
            self.assertEqual(observed["nullity"], retained["nullity"])
            self.assertEqual(
                observed["unique_cell_count"],
                retained["unique_cell_count"],
            )
            residual = report["analyses"][measure]["RHS_accounting_identity"][
                "residual_million_RON"
            ]
            retained_residual = self.assessment["RHS_accounting_identity"][measure][
                "residual_million_RON"
            ]
            self.assertAlmostEqual(residual, retained_residual, places=12)


if __name__ == "__main__":
    unittest.main()
