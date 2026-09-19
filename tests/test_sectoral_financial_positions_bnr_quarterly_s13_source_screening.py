from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class SectoralFinancialPositionsBNRQuarterlyS13ScreeningTests(unittest.TestCase):
    def setUp(self):
        self.r = load(
            "model/dynamics/sectoral_financial_positions_bnr_quarterly_s13_source_screening.json"
        )
        self.e = load(
            "model/dynamics/sectoral_financial_positions_external_source_screening.json"
        )
        self.refs = load("model/dynamics/reference_modes.json")

    def test_quarterly_history_and_full_sequence_are_confirmed_for_s13(self):
        s = self.r["confirmed_semantics"]
        self.assertTrue(s["quarterly_history_available"])
        self.assertEqual(
            s["reporting_sector"],
            "S13 general government and its subsectors S1311, S1313, S1314",
        )
        self.assertEqual(s["consolidation"], "consolidated within and across the reported general-government subsectors")
        self.assertIn("stocks", s["sequence_of_accounts"])
        self.assertIn("financial transactions", s["sequence_of_accounts"])

    def test_source_fails_full_rmd_sector_counterpart_boundary(self):
        b = self.r["frozen_rmd_boundary_comparison"]
        self.assertTrue(b["frequency_pass"])
        self.assertFalse(b["sector_scope_pass"])
        self.assertFalse(b["counterpart_structure_pass"])
        self.assertFalse(b["consolidation_pass"])
        self.assertTrue(b["instrument_and_sequence_evidence_useful"])

    def test_no_reopen_or_promotion_follows_from_s13_quarterly_source(self):
        d = self.r["disposition"]
        self.assertFalse(d["formal_reopen_trigger_satisfied"])
        self.assertFalse(d["reference_mode_status_change"])
        self.assertEqual(d["current_readiness"], "9/10")
        self.assertFalse(d["exact_historical_extraction_authorized"])
        self.assertFalse(d["reference_mode_promotion_authorized"])
        self.assertFalse(d["accounting_readiness_change"])
        self.assertFalse(d["system_dynamics_activation"])
        self.assertFalse(d["behavioural_closure_change"])

    def test_external_screening_registers_quarterly_s13_path(self):
        by_id = {x["id"]: x for x in self.e["screened_sources"]}
        s = by_id["BNR_QUARTERLY_S13_FINANCIAL_ACCOUNTS"]
        self.assertEqual(s["quarterly_history_start"], "1998-Q4")
        self.assertEqual(s["latest_indexed_reference_period"], "2024-Q2")
        self.assertFalse(s["full_rmd_sector_counterpart_scope"])
        self.assertEqual(
            s["status"],
            "OFFICIAL_QUARTERLY_S13_FINANCIAL_ACCOUNTS_CONFIRMED_FREQUENCY_PASS_SECTOR_COUNTERPART_CONSOLIDATION_FAIL_NO_REOPEN",
        )

    def test_reference_mode_remains_partial(self):
        mode = next(x for x in self.refs["modes"] if x["id"] == "sectoral_financial_positions")
        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            mode["bnr_quarterly_s13_source_screening"],
            "model/dynamics/sectoral_financial_positions_bnr_quarterly_s13_source_screening.json",
        )


if __name__ == "__main__":
    unittest.main()
