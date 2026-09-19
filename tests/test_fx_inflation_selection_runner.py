from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.fx_inflation_design import (
    build_design_rows,
    read_level_records,
)
from romania_macro_financial_dynamics.fx_inflation_selection import (
    FxInflationIdentifiabilityError,
    cumulative_fx_effects,
    fit_ols,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "data"
    / "source_vintages"
    / "fx-inflation-monthly-levels-vintage-2026-09-19"
    / "fx_inflation_monthly_raw_source.csv"
)
RUNNER = ROOT / "scripts" / "run_fx_inflation_structural_selection.py"
GATE = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_selection_execution_gate.json"
)


class FxInflationSelectionRunnerTests(unittest.TestCase):
    def test_candidate_fit_is_identifiable_on_initial_calibration(self) -> None:
        records = read_level_records(SOURCE, max_period="2014-12")
        rows = build_design_rows(
            records,
            first_target="2005-08",
            last_target="2014-12",
        )
        fit = fit_ols(
            "fx_candidate",
            rows,
            condition_number_max=30.0,
        )
        self.assertEqual(fit.design_rank, 20)
        self.assertLessEqual(
            fit.standardized_condition_number,
            30.0,
        )
        short, full = cumulative_fx_effects(fit)
        self.assertTrue(isinstance(short, float))
        self.assertTrue(isinstance(full, float))

    def test_constant_external_price_predictor_is_rejected(self) -> None:
        records = read_level_records(SOURCE, max_period="2014-12")
        rows = build_design_rows(
            records,
            first_target="2005-08",
            last_target="2014-12",
        )
        damaged = [dict(row) for row in rows]
        for row in damaged:
            row["dpstar_0"] = 0.0
        with self.assertRaises(FxInflationIdentifiabilityError):
            fit_ols(
                "external_price_baseline",
                damaged,
                condition_number_max=30.0,
            )

    def test_runner_default_path_performs_no_estimation(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
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
        self.assertIn(
            '"final_evaluation_opened": false',
            result.stdout.lower(),
        )

    def test_selection_cannot_run_without_explicit_gate(self) -> None:
        if GATE.exists():
            self.fail(
                "FX-inflation execution gate unexpectedly exists "
                "during runner-implementation phase"
            )
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--execute-selection",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not authorized", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
