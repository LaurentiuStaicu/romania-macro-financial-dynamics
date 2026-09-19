from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "processed" / "bnr_bls_realised_rounds.csv"
AUDIT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_cross_round_mapping_audit.json"
)


class BNRBLSCrossRoundMappingResultTests(unittest.TestCase):
    def setUp(self) -> None:
        with PANEL.open("r", encoding="utf-8", newline="") as handle:
            self.rows = list(csv.DictReader(handle))
        self.audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    def test_retained_panel_has_only_observed_rounds(self) -> None:
        self.assertEqual(len(self.rows), 8)
        self.assertEqual(
            [row["quarter"] for row in self.rows],
            [
                "2022-Q4",
                "2023-Q1",
                "2023-Q4",
                "2024-Q1",
                "2024-Q3",
                "2024-Q4",
                "2025-Q1",
                "2025-Q3",
            ],
        )

    def test_coverage_gaps_are_explicit_and_unfilled(self) -> None:
        self.assertEqual(
            self.audit["missing_quarters"],
            ["2023-Q2", "2023-Q3", "2024-Q2", "2025-Q2"],
        )
        self.assertEqual(self.audit["observed_round_count"], 8)
        self.assertEqual(self.audit["expected_quarter_count_between_bounds"], 12)
        self.assertAlmostEqual(self.audit["coverage_fraction"], 8 / 12)
        self.assertFalse(self.audit["interpolation_performed"])
        self.assertFalse(self.audit["synthetic_quarters_created"])

    def test_known_legacy_header_anomalies_are_preserved_as_diagnostics(self) -> None:
        validations = self.audit["legacy_round_validations"]
        feb = validations["bls_2023_feb"]["round_date_authority"]
        may = validations["bls_2023_may"]["round_date_authority"]
        self.assertEqual(feb["value"], "31/12/2022")
        self.assertIsNone(feb["household_header_diagnostics"]["A1"])
        self.assertEqual(
            feb["household_header_diagnostics"]["B1"],
            "31/12/2022",
        )
        self.assertEqual(may["value"], "31/03/2023")
        self.assertEqual(
            may["household_header_diagnostics"]["A1"],
            "31/12/2022",
        )
        self.assertFalse(
            may["household_header_date_consistency_required"]
        )

    def test_mapping_result_does_not_open_estimation_or_closure(self) -> None:
        self.assertFalse(self.audit["parameter_estimation_performed"])
        self.assertFalse(self.audit["model_selection_performed"])
        self.assertFalse(self.audit["system_dynamics_activation"])
        self.assertFalse(self.audit["behavioural_closure_change"])
        self.assertTrue(self.audit["hard_rules"]["no_holdout_opening"])
        self.assertTrue(self.audit["hard_rules"]["no_nfc_household_signal_aggregation"])


if __name__ == "__main__":
    unittest.main()
