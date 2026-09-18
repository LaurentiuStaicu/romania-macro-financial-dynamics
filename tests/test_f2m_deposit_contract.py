from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_qsa_f2m_deposit_coverage import formula

ROOT = Path(__file__).resolve().parents[1]


class F2MDepositContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f2m_deposit_coverage_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_f2m_is_not_total_f2(self) -> None:
        self.assertTrue(self.contract["hard_rules"]["no_F2M_relabelled_as_F2"])
        self.assertTrue(
            self.contract["hard_rules"]["no_synthetic_currency_allocation"]
        )

    def test_households_and_nfcs_are_structural_non_issuers(self) -> None:
        self.assertEqual(
            set(self.contract["structural_non_issuer_sectors_for_F2M"]),
            {"H", "C"},
        )
        self.assertEqual(formula("H", "H", "LE"), ())
        self.assertEqual(formula("H", "C", "LE"), ())

    def test_external_deposit_assets_may_not_be_residual_allocated(self) -> None:
        self.assertTrue(
            self.contract["hard_rules"][
                "no_external_deposit_allocation_from_row_residuals"
            ]
        )
        blockers = {
            (item["instrument"], item.get("boundary")): item["status"]
            for item in self.contract["parallel_blockers"]
        }
        self.assertEqual(
            blockers[("F2M", "resident holder to rest-of-world issuer")],
            "UNRESOLVED_EXTERNAL_DEPOSIT_ASSETS",
        )

    def test_financial_sector_deposits_use_exact_subtraction(self) -> None:
        terms = formula("H", "F", "LE")
        self.assertEqual(sorted(term.coefficient for term in terms), [-1.0, 1.0])

    def test_total_f2_remains_blocked_by_currency(self) -> None:
        blockers = {
            item["instrument"]: item["status"]
            for item in self.contract["parallel_blockers"]
        }
        self.assertEqual(
            blockers["F21"],
            "UNRESOLVED_BILATERAL_CURRENCY_ALLOCATION",
        )


if __name__ == "__main__":
    unittest.main()
