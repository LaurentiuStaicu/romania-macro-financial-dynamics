from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SectoralFinancialPositionsReferenceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/dynamics/sectoral_financial_positions_boundary_review.json"
        )
        self.contract = load(
            "model/dynamics/sectoral_financial_positions_reference_contract.json"
        )

    def test_narrower_boundary_is_explicitly_not_accounting_completion(self) -> None:
        separation = self.review["separation_from_accounting_spine"]
        self.assertFalse(separation["bilateral_holder_issuer_positions_observed_by_this_boundary"])
        self.assertFalse(separation["canonical_instrument_matrices_completed_by_this_boundary"])
        self.assertFalse(separation["accounting_readiness_may_change"])
        self.assertFalse(separation["benchmark_cells_may_change"])
        self.assertTrue(
            separation[
                "aggregate_reference_mode_may_be_ready_while_bilateral_accounting_remains_incomplete"
            ]
        )

    def test_source_boundary_matches_exact_rmd_sector_and_instrument_scope(self) -> None:
        source = self.contract["source"]
        self.assertEqual(source["dataset"].split(" — ")[0], "QSA")
        self.assertEqual(source["reference_area"], "RO")
        self.assertEqual(source["represented_total_formula"], "F minus F1")
        self.assertEqual(
            source["resident_sector_mapping"]["F"],
            [["S12", 1.0], ["S121", -1.0]],
        )
        self.assertEqual(source["resident_sector_mapping"]["H"], [["S1M", 1.0]])
        self.assertEqual(source["resident_sector_mapping"]["C"], [["S11", 1.0]])
        self.assertEqual(source["resident_sector_mapping"]["G"], [["S13", 1.0]])
        self.assertEqual(source["resident_sector_mapping"]["BNR"], [["S121", 1.0]])
        self.assertEqual(
            self.review["proposed_reference_boundary"]["represented_instruments"],
            ["F2", "F3", "F4", "F5", "F6", "F7", "F8"],
        )

    def test_stock_and_flow_semantics_cannot_be_conflated(self) -> None:
        construction = self.contract["construction"]
        rules = self.contract["hard_rules"]
        self.assertIn("separately published QSA concepts", construction["stock_flow_semantics"])
        self.assertTrue(rules["no_stock_difference_flow_proxy"])
        self.assertTrue(rules["no_BF90_total_substitution_without_F1_exclusion"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_interpolation"])

    def test_system_reconciliation_is_required_for_both_stock_and_flow(self) -> None:
        gates = self.contract["consistency_gates"]
        self.assertIn(
            "0.1 million RON",
            gates["represented_system_net_position_reconciliation"],
        )
        self.assertIn(
            "0.1 million RON",
            gates["represented_system_net_transaction_reconciliation"],
        )
        self.assertTrue(gates["resident_F_composite_exact_same_period"])
        self.assertTrue(gates["X_orientation_must_be_explicit"])

    def test_promotion_cannot_mutate_accounting_or_behaviour(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_bilateral_allocation"])
        self.assertTrue(rules["no_accounting_benchmark_mutation"])
        self.assertTrue(rules["no_accounting_readiness_promotion"])
        self.assertTrue(rules["no_behavioural_activation"])
        promotion = self.contract["promotion_rule"]
        self.assertIn("Accounting Spine readiness", promotion)
        self.assertIn("behavioural closure remain unchanged", promotion)


if __name__ == "__main__":
    unittest.main()
