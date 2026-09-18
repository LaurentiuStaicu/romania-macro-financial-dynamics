from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_qsa_accounting_coverage import formula

ROOT = Path(__file__).resolve().parents[1]


class AccountingRecoveryContractTests(unittest.TestCase):
    def test_contract_prohibits_synthetic_allocation(self) -> None:
        contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "empirical_recovery_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(contract["hard_rules"]["no_synthetic_bilateral_allocation"])
        self.assertTrue(contract["hard_rules"]["no_missing_value_to_zero"])
        self.assertTrue(
            contract["hard_rules"][
                "no_benchmark_cell_promotion_during_source_coverage_audit"
            ]
        )

    def test_financial_sector_is_exact_s12_minus_s121(self) -> None:
        contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "empirical_recovery_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            contract["sector_mapping"]["F"]["qsa_identity"],
            "S12 - S121",
        )

    def test_f_to_f_uses_inclusion_exclusion(self) -> None:
        terms = formula("F", "F", side="canonical", measure="LE")
        coefficients = sorted(term.coefficient for term in terms)
        self.assertEqual(coefficients, [-1.0, -1.0, 1.0, 1.0])
        self.assertEqual(len({term.key for term in terms}), 4)

    def test_rest_of_world_to_government_uses_issuer_liability_w1(self) -> None:
        terms = formula("X", "G", side="canonical", measure="LE")
        self.assertEqual(len(terms), 1)
        self.assertIn(".W1.S13.S1.N.L.LE.F3.T.", terms[0].key)

    def test_government_to_rest_of_world_uses_holder_asset_w1(self) -> None:
        terms = formula("G", "X", side="canonical", measure="LE")
        self.assertEqual(len(terms), 1)
        self.assertIn(".W1.S13.S1.N.A.LE.F3.T.", terms[0].key)

    def test_rest_of_world_internal_cell_has_no_qsa_formula(self) -> None:
        self.assertEqual(
            formula("X", "X", side="canonical", measure="LE"),
            (),
        )


if __name__ == "__main__":
    unittest.main()
