from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class SectoralFinancialPositionsBNRCNFSourceScreeningTests(unittest.TestCase):
    def setUp(self):
        self.r = load("model/dynamics/sectoral_financial_positions_bnr_cnf_source_screening.json")
        self.e = load("model/dynamics/sectoral_financial_positions_external_source_screening.json")
        self.refs = load("model/dynamics/reference_modes.json")

    def test_bnr_annual_counterpart_stock_semantics_are_exact_but_not_quarterly(self):
        matrix = self.r["observed_counterpart_matrix"]
        self.assertEqual(matrix["period"], "2024")
        self.assertEqual(matrix["measure"], "closing stocks only in the explicit counterpart-matrix section")
        self.assertEqual(matrix["unit"], "million RON")
        self.assertEqual(matrix["consolidation"], "non-consolidated")
        self.assertIn("S121", matrix["source_sector_codes_visible"])
        for code in ("AF2", "AF3", "AF4", "AF5", "AF6", "AF7", "AF8"):
            self.assertIn(code, matrix["financial_instruments_visible"])

    def test_semantic_mapping_passes_but_frozen_history_gate_fails(self):
        review = self.r["semantic_review"]
        self.assertEqual(review["sector_mapping"], "PASS_FOR_2024_STOCK_MATRIX")
        self.assertEqual(review["instrument_mapping_F2_F8"], "PASS_FOR_2024_STOCK_MATRIX")
        self.assertEqual(review["quarterly_frequency"], "FAIL")
        self.assertTrue(review["financial_transaction_counterpart_history"].startswith("FAIL"))
        self.assertTrue(review["common_history_minimum_40_quarters"].startswith("FAIL"))

    def test_bnr_evidence_cannot_promote_or_relax_boundary(self):
        d = self.r["disposition"]
        self.assertFalse(d["reference_mode_status_change"])
        self.assertEqual(d["current_status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(d["current_readiness"], "9/10")
        self.assertFalse(d["exact_historical_extraction_authorized"])
        self.assertFalse(d["quarterly_boundary_change_authorized"])
        self.assertFalse(d["annual_single_snapshot_substitution_authorized"])
        self.assertFalse(d["accounting_readiness_change"])
        self.assertFalse(d["behavioural_closure_change"])

    def test_external_screening_registers_bnr_final_path_without_rewriting_canonical_state(self):
        by_id = {x["id"]: x for x in self.e["screened_sources"]}
        bnr = by_id["BNR_NATIONAL_FINANCIAL_ACCOUNTS_PUBLICATIONS"]
        self.assertTrue(bnr["exact_annual_2024_counterpart_stock_matrix_identified"])
        self.assertFalse(bnr["exact_quarterly_F2_F8_counterpart_machine_readable_history_identified"])
        self.assertFalse(bnr["exact_quarterly_stock_and_transaction_history_identified"])
        self.assertEqual(
            self.e["decision"]["external_counterpart_recovery_state"],
            "EXHAUSTED_NO_SEMANTICALLY_ADMISSIBLE_CURRENT_PUBLIC_SOURCE",
        )
        self.assertEqual(
            self.e["decision"]["current_public_source_completion_status"],
            "EUROSTAT_INSTRUMENT_SCOPE_FAIL_OECD_S121_SCOPE_FAIL_BNR_ANNUAL_FREQUENCY_TRANSACTION_HISTORY_FAIL_BNR_QUARTERLY_S13_SECTOR_COUNTERPART_CONSOLIDATION_FAIL",
        )

    def test_reference_mode_remains_partial_and_points_to_screening(self):
        mode = next(x for x in self.refs["modes"] if x["id"] == "sectoral_financial_positions")
        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            mode["bnr_cnf_source_screening"],
            "model/dynamics/sectoral_financial_positions_bnr_cnf_source_screening.json",
        )
        self.assertEqual(
            mode["bnr_cnf_source_screening_status"],
            "OFFICIAL_ANNUAL_COUNTERPART_STOCK_MATRIX_CONFIRMED_FREQUENCY_AND_TRANSACTION_HISTORY_FAIL_NO_REOPEN",
        )


if __name__ == "__main__":
    unittest.main()
