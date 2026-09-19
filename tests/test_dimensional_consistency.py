from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_dimensional_consistency import audit_registry

ROOT = Path(__file__).resolve().parents[1]


class DimensionalConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(
            (ROOT / "model" / "dynamics" / "unit_registry.json").read_text(
                encoding="utf-8"
            )
        )

    def test_registry_passes_recomputed_dimensional_audit(self) -> None:
        self.assertEqual(audit_registry(self.registry), [])

    def test_declared_consistent_status_cannot_hide_bad_rate_dimension(self) -> None:
        mutated = copy.deepcopy(self.registry)
        check = next(
            item
            for item in mutated["equation_checks"]
            if item["id"] == "rate_stock_identity"
        )
        check["rhs_rate_signature"]["time"] = 0
        check["status"] = "CONSISTENT"
        errors = audit_registry(mutated)
        self.assertTrue(
            any(
                error.startswith("rate_stock_identity:")
                for error in errors
            )
        )

    def test_additive_dimension_mismatch_is_detected(self) -> None:
        mutated = copy.deepcopy(self.registry)
        check = next(
            item
            for item in mutated["equation_checks"]
            if item["id"] == "period_stock_identity"
        )
        check["rhs_terms"][2]["time"] = -1
        check["status"] = "CONSISTENT"
        errors = audit_registry(mutated)
        self.assertTrue(
            any(
                error.startswith("period_stock_identity:")
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
