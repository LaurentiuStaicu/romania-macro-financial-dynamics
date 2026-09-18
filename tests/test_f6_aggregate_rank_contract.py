from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F6AggregateRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f6_aggregate_rank_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.assessment = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f6_aggregate_rank_assessment.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_rank_and_no_synthetic_allocation_rules(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["rank_and_nullity_must_use_exact_rational_coefficient_arithmetic"])
        self.assertTrue(rules["unique_cell_status_requires_zero_loading_on_every_nullspace_basis_vector"])
        self.assertTrue(rules["no_synthetic_allocation"])
        self.assertTrue(rules["no_issuer_applicability_zero_in_unconditional_system"])
        self.assertTrue(rules["zero_aggregate_stock_or_flow_must_not_create_bilateral_zero_equations"])

    def test_retained_assessment_freezes_f6_without_materialization(self) -> None:
        self.assertEqual(
            self.assessment["verdict"],
            "FREEZE_F6_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY",
        )
        for measure in ("stock", "flow_2025"):
            identification = self.assessment["unconditional_identification"][measure]
            self.assertEqual(identification["rank"], 11)
            self.assertEqual(identification["nullity"], 24)
            self.assertEqual(identification["unique_cell_count"], 0)
        self.assertFalse(self.assessment["disposition"]["bilateral_materialization"])
        self.assertEqual(
            self.assessment["disposition"]["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )

    def test_offline_audit_reproduces_retained_assessment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "audit_f6_aggregate_rank.py"),
                    "--out",
                    tmp,
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            report = json.loads(
                (Path(tmp) / "f6_aggregate_rank_audit.json").read_text(encoding="utf-8")
            )

        self.assertEqual(
            report["disposition"],
            "FREEZE_F6_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY",
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
