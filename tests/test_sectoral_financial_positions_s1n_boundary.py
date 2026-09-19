from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_ecb_sectoral_financial_positions_s1n_boundary import (
    corrected_residual,
    explanation_passes,
    s1n_key,
)

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SectoralFinancialPositionsS1NBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(
            "model/dynamics/"
            "sectoral_financial_positions_s1n_boundary_diagnostic_contract.json"
        )

    def test_exact_s1n_key_is_frozen(self) -> None:
        self.assertEqual(
            s1n_key("A", "LE", "F"),
            "Q.N.RO.W0.S1N.S1.N.A.LE.F._Z._Z.XDC._T.S.V.N._T",
        )
        self.assertEqual(
            s1n_key("L", "F", "F1"),
            "Q.N.RO.W0.S1N.S1.N.L.F.F1._Z._Z.XDC._T.S.V.N._T",
        )

    def test_corrected_residual_sign_is_not_tunable(self) -> None:
        self.assertAlmostEqual(
            corrected_residual(-0.155390625, 0.150),
            -0.005390625,
        )

    def test_explanation_uses_frozen_phase_c_envelope(self) -> None:
        historical = {"2021-Q3": -0.155, "2022-Q3": 0.115}
        s1n = {"2021-Q3": 0.10, "2022-Q3": -0.04}
        passed, detail = explanation_passes(
            historical, s1n, envelope=0.08, epsilon=1e-9
        )
        self.assertTrue(passed)
        self.assertTrue(
            detail["2021-Q3"]["within_frozen_phase_C_envelope"]
        )
        self.assertTrue(
            detail["2022-Q3"]["within_frozen_phase_C_envelope"]
        )

    def test_missing_failing_period_cannot_pass(self) -> None:
        passed, detail = explanation_passes(
            {"2021-Q3": -0.155},
            {},
            envelope=0.08,
            epsilon=1e-9,
        )
        self.assertFalse(passed)
        self.assertFalse(detail["2021-Q3"]["s1n_available"])

    def test_contract_is_diagnostic_only_and_nonretroactive(self) -> None:
        self.assertFalse(self.contract["formal_reference_mode_gate"])
        self.assertEqual(
            self.contract["result_semantics"]["readiness_count_change"],
            0,
        )
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["diagnostic_only"])
        self.assertTrue(rules["no_reference_mode_promotion"])
        self.assertTrue(rules["no_historical_A_D_rewrite"])
        self.assertTrue(rules["no_phase_C_envelope_change"])
        self.assertTrue(rules["no_S1N_missing_to_zero"])
        self.assertTrue(rules["no_S1N_F1_structural_zero_assumption"])

    def test_positive_result_only_authorizes_future_preregistration(self) -> None:
        positive = self.contract["result_semantics"]["if_explanation_pass"]
        self.assertIn("separate future formal reference-mode contract", positive)
        self.assertEqual(
            self.contract["result_semantics"]["promotion_effect"],
            "NONE",
        )


if __name__ == "__main__":
    unittest.main()
