from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.fiscal_reaction_selection import (
    FiscalReactionIdentifiabilityError,
    build_lagged_rows,
    fit_ols,
    standardized_condition_number,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER = (
    ROOT
    / "scripts"
    / "run_fiscal_reaction_annual_structural_selection.py"
)
GATE = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fiscal_reaction_annual_selection_execution_gate.json"
)


class FiscalReactionAnnualSelectionRunnerTests(unittest.TestCase):
    def test_lagged_rows_use_only_prior_year_states(self) -> None:
        records = [
            {
                "year": 2020,
                "primary_balance_pct_gdp": -7.0,
                "output_gap_pct_potential_gdp": -3.0,
                "debt_pct_gdp": 46.0,
            },
            {
                "year": 2021,
                "primary_balance_pct_gdp": -6.0,
                "output_gap_pct_potential_gdp": 1.0,
                "debt_pct_gdp": 49.0,
            },
        ]
        row = build_lagged_rows(records)[0]
        self.assertEqual(row["year"], 2021)
        self.assertEqual(row["y"], -6.0)
        self.assertEqual(row["y_lag"], -7.0)
        self.assertEqual(row["debt_lag"], 46.0)
        self.assertEqual(row["output_gap_lag"], -3.0)

    def test_candidate_ols_recovers_known_coefficients(self) -> None:
        rows = []
        expected = {
            "alpha": -1.0,
            "rho": 0.55,
            "beta_d": 0.08,
            "beta_y": 0.25,
        }
        for i in range(1, 41):
            row = {
                "year": 1980 + i,
                "y_lag": -4.0 + 0.11 * i + 0.3 * (i % 3),
                "debt_lag": 15.0 + 0.7 * i + 0.4 * (i % 5),
                "output_gap_lag": -3.0 + 0.17 * i + 0.5 * (i % 7),
            }
            row["y"] = (
                expected["alpha"]
                + expected["rho"] * row["y_lag"]
                + expected["beta_d"] * row["debt_lag"]
                + expected["beta_y"] * row["output_gap_lag"]
            )
            rows.append(row)

        fit = fit_ols(
            "lagged_state_fiscal_balance_ar",
            rows,
            condition_number_max=100.0,
        )
        self.assertEqual(fit.design_rank, 4)
        for name, value in expected.items():
            self.assertAlmostEqual(
                fit.parameters[name],
                value,
                places=8,
            )

    def test_constant_predictor_is_rejected(self) -> None:
        design = [[1.0, float(i), 2.0] for i in range(1, 20)]
        with self.assertRaises(FiscalReactionIdentifiabilityError):
            standardized_condition_number(design)

    def test_runner_default_path_performs_no_estimation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "selection.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(
                "RUNNER_READY_EXECUTION_NOT_REQUESTED",
                result.stdout,
            )
            self.assertIn(
                '"estimation_performed": false',
                result.stdout.lower(),
            )
            self.assertFalse(output.exists())

    def test_selection_cannot_run_without_explicit_gate(self) -> None:
        if GATE.exists():
            self.fail(
                "annual fiscal-reaction execution gate unexpectedly exists "
                "during runner-implementation phase"
            )
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


if __name__ == "__main__":
    unittest.main()
