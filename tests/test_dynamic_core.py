from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.accounting import expand_matrix
from romania_macro_financial_dynamics.dynamics import (
    IncompleteEmpiricalState,
    PositionChange,
    PositionKey,
    advance_position,
    empirical_cells_to_state,
    first_order_delay_derivative,
    simulate_first_order_delay_euler,
    system_net_financial_worth,
)

ROOT = Path(__file__).resolve().parents[1]


class DynamicCoreTests(unittest.TestCase):
    def test_stock_identity(self) -> None:
        closing = advance_position(
            100.0,
            PositionChange(transactions=12.0, revaluations=-3.0, other_changes=1.0),
        )
        self.assertEqual(closing, 110.0)

    def test_zero_flow_extreme_condition(self) -> None:
        self.assertEqual(advance_position(123.456, PositionChange()), 123.456)

    def test_finite_large_value_extreme_condition(self) -> None:
        closing = advance_position(
            1.0e12,
            PositionChange(transactions=2.0e9, revaluations=-1.0e9, other_changes=5.0e8),
        )
        self.assertTrue(math.isfinite(closing))
        self.assertEqual(closing, 1_001_500_000_000.0)

    def test_double_entry_conservation(self) -> None:
        positions = {
            PositionKey("H", "F", "F4"): 100.0,
            PositionKey("F", "G", "F3"): 40.0,
            PositionKey("X", "C", "F5"): 25.0,
        }
        self.assertAlmostEqual(system_net_financial_worth(positions), 0.0, places=12)

    def test_dimensional_registry_is_consistent(self) -> None:
        registry = json.loads(
            (ROOT / "model" / "dynamics" / "unit_registry.json").read_text(encoding="utf-8")
        )
        self.assertTrue(registry["equation_checks"])
        self.assertTrue(
            all(check["status"] == "CONSISTENT" for check in registry["equation_checks"])
        )

    def test_delay_steady_state(self) -> None:
        self.assertEqual(first_order_delay_derivative(5.0, 5.0, 2.0), 0.0)

    def test_integration_error_convergence(self) -> None:
        exact = 1.0 - math.exp(-1.0)
        coarse = simulate_first_order_delay_euler(
            initial=0.0,
            input_value=1.0,
            tau_years=1.0,
            horizon_years=1.0,
            dt_years=0.25,
        )
        fine = simulate_first_order_delay_euler(
            initial=0.0,
            input_value=1.0,
            tau_years=1.0,
            horizon_years=1.0,
            dt_years=0.125,
        )
        self.assertLess(abs(fine - exact), abs(coarse - exact))

    def test_complete_f3_empirical_initialization_succeeds(self) -> None:
        benchmark = json.loads(
            (ROOT / "model" / "accounting" / "benchmark_2025.json").read_text(
                encoding="utf-8"
            )
        )
        cells = expand_matrix("F3", "stock", benchmark["matrices"]["F3"]["stock"])
        state = empirical_cells_to_state(cells)
        self.assertEqual(len(state), 36)
        self.assertEqual(state[PositionKey("X", "X", "F3")], 0.0)

    def test_incomplete_empirical_initialization_rejected(self) -> None:
        benchmark = json.loads(
            (ROOT / "model" / "accounting" / "benchmark_2025.json").read_text(
                encoding="utf-8"
            )
        )
        cells = expand_matrix("F2", "stock", benchmark["matrices"]["F2"]["stock"])
        with self.assertRaises(IncompleteEmpiricalState):
            empirical_cells_to_state(cells)


if __name__ == "__main__":
    unittest.main()
