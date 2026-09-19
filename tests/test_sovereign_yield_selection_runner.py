from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.sovereign_yield_selection import (
    SovereignYieldIdentifiabilityError,
    build_lagged_rows,
    fit_ols,
    standardized_condition_number,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_sovereign_yield_structural_selection.py"
GATE = (
    ROOT
    / "model"
    / "calibration_validation"
    / "sovereign_yield_selection_execution_gate.json"
)


class SovereignYieldSelectionRunnerTests(unittest.TestCase):
    def test_lagged_rows_use_only_prior_quarter_fiscal_values(self) -> None:
        records = [
            {
                "period": "2020-Q1",
                "romania_10y_yield_pct": 4.0,
                "germany_10y_yield_pct": 0.0,
                "euro_area_new_ciss": 0.1,
                "government_debt_pct_gdp": 40.0,
                "government_net_lending_borrowing_pct_gdp": -3.0,
            },
            {
                "period": "2020-Q2",
                "romania_10y_yield_pct": 4.5,
                "germany_10y_yield_pct": 0.2,
                "euro_area_new_ciss": 0.3,
                "government_debt_pct_gdp": 45.0,
                "government_net_lending_borrowing_pct_gdp": -8.0,
            },
        ]
        row = build_lagged_rows(records)[0]
        self.assertEqual(row["y_lag"], 4.0)
        self.assertEqual(row["germany"], 0.2)
        self.assertEqual(row["ciss"], 0.3)
        self.assertEqual(row["debt_lag"], 40.0)
        self.assertEqual(row["b9_lag"], -3.0)

    def test_fiscal_augmented_ols_recovers_known_coefficients(self) -> None:
        rows = []
        expected = {
            "alpha": 1.2,
            "rho": 0.65,
            "beta_g": 0.9,
            "beta_s": 1.7,
            "beta_d": 0.035,
            "beta_b": -0.08,
        }
        for i in range(1, 81):
            row = {
                "period": f"{2000 + (i - 1) // 4:04d}-Q{((i - 1) % 4) + 1}",
                "y_lag": 2.0 + 0.071 * i + 0.19 * (i % 3),
                "germany": 1.0 + 0.031 * i + 0.13 * (i % 5),
                "ciss": 0.05 + 0.004 * i + 0.021 * (i % 7),
                "debt_lag": 25.0 + 0.17 * i + 0.23 * (i % 4),
                "b9_lag": -6.0 + 0.013 * i + 0.16 * (i % 6),
            }
            row["y"] = (
                expected["alpha"]
                + expected["rho"] * row["y_lag"]
                + expected["beta_g"] * row["germany"]
                + expected["beta_s"] * row["ciss"]
                + expected["beta_d"] * row["debt_lag"]
                + expected["beta_b"] * row["b9_lag"]
            )
            rows.append(row)

        fit = fit_ols(
            "fiscal_augmented_common_market_ar",
            rows,
            condition_number_max=100.0,
        )
        self.assertEqual(fit.design_rank, 6)
        for name, value in expected.items():
            self.assertAlmostEqual(fit.parameters[name], value, places=8)

    def test_constant_predictor_is_rejected_by_condition_gate(self) -> None:
        design = [
            [1.0, float(i), 2.0]
            for i in range(1, 20)
        ]
        with self.assertRaises(SovereignYieldIdentifiabilityError):
            standardized_condition_number(design)

    def test_runner_default_path_performs_no_estimation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "selection.json"
            result = subprocess.run(
                [sys.executable, str(RUNNER), "--output", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("RUNNER_READY_EXECUTION_NOT_REQUESTED", result.stdout)
            self.assertIn('"estimation_performed": false', result.stdout.lower())
            self.assertFalse(output.exists())

    def test_execution_gate_never_authorizes_final_evaluation(self) -> None:
        if not GATE.exists():
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "selection.json"
                result = subprocess.run(
                    [
                        sys.executable,
                        str(RUNNER),
                        "--execute-selection",
                        "--output",
                        str(output),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("not authorized", result.stderr.lower())
                self.assertFalse(output.exists())
            return

        import json

        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertTrue(gate["selection_execution_authorized"])
        self.assertFalse(gate["final_evaluation_authorized"])
        self.assertEqual(
            gate["authorized_scope"],
            "STRUCTURAL_SELECTION_2017_Q1_TO_2022_Q4_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
