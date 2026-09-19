from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SectoralFinancialPositionsPhaseCDiagnosticContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/dynamics/sectoral_financial_positions_phase_c_diagnostic_contract.json"
        )
        self.phase_b = load(
            "model/dynamics/sectoral_financial_positions_phase_b_assessment.json"
        )

    def test_phase_c_is_diagnostic_only_and_downstream_of_phase_b(self) -> None:
        self.assertEqual(
            self.phase_b["verdict"],
            self.contract["prerequisite"]["required_phase_b_verdict"],
        )
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["diagnostic_only_no_promotion"])
        self.assertTrue(rules["no_reference_mode_status_change"])
        self.assertTrue(rules["no_readiness_count_change"])
        self.assertTrue(rules["no_accounting_readiness_change"])
        self.assertTrue(rules["no_behavioural_closure_change"])

    def test_phase_c_cannot_tune_prior_gates(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_post_result_orientation_swap"])
        self.assertTrue(rules["no_tolerance_change"])
        self.assertTrue(rules["no_structural_zero_change"])
        self.assertTrue(rules["missing_series_remain_missing_not_zero"])
        self.assertTrue(rules["no_stock_difference_flow_proxy"])

    def test_diagnostic_instruments_and_break_window_are_frozen(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["instruments"], ["F1", "F11", "F12"])
        self.assertEqual(source["measures"], ["LE", "F"])
        self.assertEqual(source["entries"], ["A", "L"])
        comparisons = " ".join(self.contract["comparisons"])
        self.assertIn("2021-Q2", comparisons)
        self.assertIn("2021-Q3", comparisons)
        self.assertIn("2021-Q4", comparisons)
        self.assertIn("F1 - F11 - F12", comparisons)


if __name__ == "__main__":
    unittest.main()
