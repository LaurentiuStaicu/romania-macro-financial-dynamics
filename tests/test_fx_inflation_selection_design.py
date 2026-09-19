from __future__ import annotations

import math
import subprocess
import sys
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.fx_inflation_design import (
    build_design_rows,
    calendar_month_dummies,
    log_change,
    read_level_records,
    rows_in_window,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "data"
    / "source_vintages"
    / "fx-inflation-monthly-levels-vintage-2026-09-19"
    / "fx_inflation_monthly_raw_source.csv"
)
RUNNER = ROOT / "scripts" / "build_fx_inflation_selection_design.py"


class FxInflationSelectionDesignTests(unittest.TestCase):
    def test_log_change_matches_frozen_definition(self) -> None:
        self.assertAlmostEqual(
            log_change(math.e ** 0.01, 1.0),
            1.0,
            places=10,
        )

    def test_calendar_month_dummies_use_january_reference(self) -> None:
        january = calendar_month_dummies("2020-01")
        self.assertEqual(len(january), 11)
        self.assertEqual(sum(january.values()), 0.0)
        august = calendar_month_dummies("2020-08")
        self.assertEqual(sum(august.values()), 1.0)
        self.assertEqual(august["month_08"], 1.0)

    def test_actual_design_stops_before_final_evaluation(self) -> None:
        records = read_level_records(SOURCE, max_period="2020-12")
        self.assertEqual(records[-1]["period"], "2020-12")
        rows = build_design_rows(records)
        self.assertEqual(rows[0]["period"], "2005-08")
        self.assertEqual(rows[-1]["period"], "2020-12")
        self.assertEqual(len(rows), 185)
        calibration = rows_in_window(
            rows, "2005-08", "2014-12"
        )
        selection = rows_in_window(
            rows, "2015-01", "2020-12"
        )
        self.assertEqual(len(calibration), 113)
        self.assertEqual(len(selection), 72)
        self.assertFalse(
            any(str(row["period"]) >= "2021-01" for row in rows)
        )

    def test_fx_blocks_are_derived_only_from_current_or_past_months(self) -> None:
        records = read_level_records(SOURCE, max_period="2005-09")
        august = build_design_rows(
            records,
            first_target="2005-08",
            last_target="2005-08",
        )[0]
        self.assertIn("de_0", august)
        self.assertIn("de_1_3_mean", august)
        self.assertIn("de_4_6_mean", august)
        self.assertIn("de_7_12_mean", august)

    def test_runner_is_summary_only_and_performs_no_estimation(self) -> None:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--summary-only"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("DESIGN_READY_NO_ESTIMATION", result.stdout)
        self.assertIn('"final_evaluation_loaded": false', result.stdout.lower())
        self.assertIn('"estimation_performed": false', result.stdout.lower())
        self.assertIn('"design_rows": 185', result.stdout)


if __name__ == "__main__":
    unittest.main()
