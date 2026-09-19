from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GovernmentDebtStockReferenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "government_debt_stock_reference_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_official_concept_is_preregistered(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["institution"], "Eurostat")
        self.assertEqual(source["dataset"].split(" — ")[0], "gov_10q_ggdebt")
        self.assertEqual(source["geo"], "RO")
        self.assertEqual(source["sector"], "S13")
        self.assertEqual(source["na_item"], "GD")
        self.assertEqual(set(source["units_to_probe"]), {"MIO_NAC", "PC_GDP"})

    def test_maastricht_debt_is_not_accounting_spine_total_liabilities(self) -> None:
        boundary = self.contract["concept_boundary"]
        self.assertTrue(boundary["GD_is_consolidated_gross_debt"])
        self.assertTrue(boundary["GD_is_nominal_face_value"])
        self.assertTrue(boundary["GD_is_not_total_financial_accounts_liabilities"])
        self.assertTrue(
            boundary["GD_is_not_market_value_F3_plus_F4_plus_other_liabilities"]
        )
        self.assertTrue(boundary["GD_does_not_complete_the_Accounting_Spine"])
        self.assertTrue(boundary["GD_does_not_identify_holder_by_issuer_counterparts"])

    def test_no_accounting_or_behavioural_promotion_is_smuggled_in(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["reference_mode_source_audit_only"])
        self.assertTrue(rules["no_accounting_benchmark_mutation"])
        self.assertTrue(rules["no_instrument_allocation"])
        self.assertTrue(rules["no_holder_issuer_allocation"])
        self.assertFalse(rules["behavioural_closure_may_change"])

    def test_promotion_requires_retained_immutable_evidence(self) -> None:
        rule = self.contract["promotion_rule"]
        self.assertIn("workflow run", rule)
        self.assertIn("artifact identifier", rule)
        self.assertIn("SHA-256", rule)
        self.assertIn("does not complete the Accounting Spine", rule)


if __name__ == "__main__":
    unittest.main()
