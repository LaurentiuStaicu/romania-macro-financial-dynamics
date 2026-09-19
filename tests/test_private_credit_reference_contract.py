from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PrivateCreditReferenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "private_credit_reference_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_ecb_component_scope_is_preregistered(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["institution"], "European Central Bank / ESCB")
        self.assertEqual(source["dataset"].split(" — ")[0], "BSI")
        self.assertEqual(source["reference_area"], "RO")
        self.assertEqual(source["adjustment"], "N")
        self.assertEqual(source["reference_sector"], "A")
        self.assertEqual(source["balance_sheet_item"], "A20")
        self.assertEqual(source["maturity"], "A")
        self.assertEqual(source["counterpart_area"], "U6")
        self.assertEqual(source["currency"], "Z01")
        self.assertEqual(source["suffix"], "E")

        components = source["components"]
        self.assertEqual(
            components["nfc_stock"]["series_key"],
            "BSI.M.RO.N.A.A20.A.1.U6.2240.Z01.E",
        )
        self.assertEqual(
            components["households_npish_stock"]["series_key"],
            "BSI.M.RO.N.A.A20.A.1.U6.2250.Z01.E",
        )
        self.assertEqual(
            components["nfc_flow"]["series_key"],
            "BSI.M.RO.N.A.A20.A.4.U6.2240.Z01.E",
        )
        self.assertEqual(
            components["households_npish_flow"]["series_key"],
            "BSI.M.RO.N.A.A20.A.4.U6.2250.Z01.E",
        )

    def test_stock_and_flow_semantics_cannot_be_conflated(self) -> None:
        boundary = self.contract["concept_boundary"]
        self.assertTrue(boundary["stock_is_end_of_period_outstanding_amount"])
        self.assertTrue(boundary["flow_is_ECB_financial_transaction"])
        self.assertTrue(boundary["flow_is_not_stock_first_difference"])
        self.assertTrue(boundary["flow_is_not_gross_new_lending_originations"])
        self.assertTrue(boundary["aggregate_scope_is_S11_plus_S14_S15"])
        self.assertTrue(boundary["aggregate_excludes_other_financial_sectors"])

    def test_no_missing_or_broader_sector_shortcuts(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_missing_component_to_zero"])
        self.assertTrue(rules["no_interpolation"])
        self.assertTrue(rules["no_stock_difference_flow_proxy"])
        self.assertTrue(rules["no_other_sector_completion"])
        self.assertTrue(
            rules[
                "both_reference_modes_promote_together_only_if_all_four_components_pass"
            ]
        )
        self.assertFalse(rules["behavioural_closure_may_change"])

    def test_promotion_is_observability_only(self) -> None:
        rule = self.contract["promotion_rule"]
        self.assertIn("workflow run", rule)
        self.assertIn("artifact identifier", rule)
        self.assertIn("SHA-256", rule)
        self.assertIn("does not activate", rule)


if __name__ == "__main__":
    unittest.main()
