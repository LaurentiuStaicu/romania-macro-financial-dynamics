from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_accounting_readiness import audit_readiness

ROOT = Path(__file__).resolve().parents[1]


class AccountingReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = json.loads(
            (
                ROOT / "model" / "accounting" / "accounting_readiness_gate.json"
            ).read_text(encoding="utf-8")
        )
        self.benchmark = json.loads(
            (
                ROOT / "model" / "accounting" / "benchmark_2025.json"
            ).read_text(encoding="utf-8")
        )
        self.reconciliation = json.loads(
            (
                ROOT / "model" / "accounting" / "reconciliation_2025.json"
            ).read_text(encoding="utf-8")
        )

    def test_current_readiness_is_recomputed_from_canonical_benchmark(self) -> None:
        report, errors = audit_readiness(
            self.gate,
            self.benchmark,
            self.reconciliation,
        )
        self.assertEqual(errors, [])
        self.assertEqual(
            report["canonical_complete_stock_and_flow_instruments"],
            ["F3"],
        )
        self.assertFalse(
            report["canonical_multi_instrument_stock_initialization_ready"]
        )
        self.assertFalse(
            report["canonical_full_2025_stock_flow_benchmark_ready"]
        )
        self.assertFalse(report["full_RMD_empirical_state_claim_allowed"])
        self.assertEqual(
            report["canonical_stock_in_boundary_cells_finite"],
            35,
        )
        self.assertEqual(
            report["canonical_stock_in_boundary_cells_required"],
            245,
        )

    def test_partial_f4_artifact_does_not_complete_canonical_f4(self) -> None:
        report, errors = audit_readiness(
            self.gate,
            self.benchmark,
            self.reconciliation,
        )
        self.assertEqual(errors, [])
        self.assertFalse(
            report["instrument_readiness"]["F4"]["stock_and_flow_complete"]
        )
        self.assertIn("F4", report["canonical_incomplete_instruments"])

    def test_reconciliation_cannot_overstate_incomplete_matrix(self) -> None:
        mutated = copy.deepcopy(self.reconciliation)
        f7 = next(
            item
            for item in mutated["instrument_gates"]
            if item["instrument"] == "F7"
        )
        f7["stock_matrix_status"] = "COMPLETE_FAKE"
        f7["flow_matrix_status"] = "COMPLETE_FAKE"
        _, errors = audit_readiness(self.gate, self.benchmark, mutated)
        self.assertTrue(
            any(
                "F7 reconciliation overstates canonical completion" in error
                for error in errors
            )
        )

    def test_declared_readiness_cannot_be_flipped_without_data(self) -> None:
        mutated = copy.deepcopy(self.gate)
        mutated["current_expected_state"][
            "canonical_multi_instrument_stock_initialization_ready"
        ] = True
        mutated["current_expected_state"][
            "canonical_full_2025_stock_flow_benchmark_ready"
        ] = True
        _, errors = audit_readiness(
            mutated,
            self.benchmark,
            self.reconciliation,
        )
        self.assertTrue(
            any("stock-initialization readiness" in error for error in errors)
        )
        self.assertTrue(
            any("full stock-flow readiness" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
