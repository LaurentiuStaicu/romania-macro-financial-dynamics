from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.accounting import (
    AccountingCell,
    expand_matrix,
    observed_sum,
    validate_benchmark_spec,
)

ROOT = Path(__file__).resolve().parents[1]


class AccountingPrimitiveIntegrityTests(unittest.TestCase):
    def test_current_benchmark_contract_validates(self) -> None:
        benchmark = json.loads(
            (ROOT / "model" / "accounting" / "benchmark_2025.json").read_text(
                encoding="utf-8"
            )
        )
        validate_benchmark_spec(benchmark)

    def test_nonfinite_observed_or_derived_values_are_rejected(self) -> None:
        for status in ("OBSERVED", "DERIVED"):
            for value in (float("nan"), float("inf"), -float("inf")):
                with self.assertRaises(ValueError):
                    AccountingCell(
                        holder="H",
                        issuer="F",
                        instrument="F3",
                        measure="stock",
                        status=status,
                        value=value,
                    )

    def test_complete_observed_sum_is_finite(self) -> None:
        benchmark = json.loads(
            (ROOT / "model" / "accounting" / "benchmark_2025.json").read_text(
                encoding="utf-8"
            )
        )
        cells = expand_matrix("F3", "stock", benchmark["matrices"]["F3"]["stock"])
        total = observed_sum(cells)
        self.assertIsNotNone(total)
        self.assertTrue(math.isfinite(float(total)))


if __name__ == "__main__":
    unittest.main()
