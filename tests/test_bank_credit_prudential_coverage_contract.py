from __future__ import annotations

import unittest

from scripts.audit_ecb_bank_credit_prudential_coverage import (
    parse_csv,
    strip_flow,
)
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class BankCreditPrudentialCoverageContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/calibration_validation/"
            "bank_credit_prudential_coverage_contract.json"
        )

    def test_three_prudential_concepts_are_kept_distinct(self) -> None:
        series = self.contract["source"]["candidate_series"]
        self.assertEqual(
            series["npl_ratio"]["full_series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.F.I3632._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertEqual(
            series["solvency_ratio"]["full_series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.A.I4001._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertEqual(
            series["cet1_ratio"]["full_series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.A.I4008._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertIn(
            "does not assert",
            series["solvency_ratio"]["derivation_note"],
        )

    def test_bnr_anchor_is_diagnostic_not_numeric_bridge_gate(self) -> None:
        anchor = self.contract["bnr_semantic_anchor"]
        self.assertEqual(
            anchor["concept_statement"],
            "BNR labels Total capital ratio as previously solvency ratio.",
        )
        self.assertEqual(
            anchor["diagnostic_values"]["2024-Q3"]["total_capital_ratio_pct"],
            24.95,
        )
        self.assertIn("No numerical tolerance", anchor["comparison_rule"])

    def test_no_cet1_fallback_is_authorized(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(
            rules["no_CET1_substitution_for_solvency_after_outcomes"]
        )
        self.assertTrue(rules["no_population_bridge_by_numeric_similarity"])
        self.assertTrue(rules["no_calibration_or_refit"])
        self.assertFalse(
            self.contract["result_effect"]["calibration_cycle_open"]
        )

    def test_ecb_csv_parser_is_offline_and_exact(self) -> None:
        body = (
            b"KEY,TIME_PERIOD,OBS_VALUE\n"
            b"x,2024-Q1,2.41\n"
            b"x,2024-Q2,2.49\n"
        )
        self.assertEqual(
            parse_csv(body),
            {"2024-Q1": 2.41, "2024-Q2": 2.49},
        )
        self.assertEqual(
            strip_flow(
                "CBD2.Q.RO.W0.11._Z._Z.A.F.I3632._Z._Z._Z._Z._Z._Z.PC"
            ),
            "Q.RO.W0.11._Z._Z.A.F.I3632._Z._Z._Z._Z._Z._Z.PC",
        )


if __name__ == "__main__":
    unittest.main()
