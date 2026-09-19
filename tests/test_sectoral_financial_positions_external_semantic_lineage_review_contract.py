from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "dynamics"
    / "sectoral_financial_positions_external_semantic_lineage_review_contract.json"
)


class SectoralFinancialPositionsExternalSemanticLineageReviewContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(P.read_text(encoding="utf-8"))

    def test_review_is_post_discovery_but_pre_value_and_pre_promotion(self) -> None:
        self.assertFalse(self.contract["formal_reference_mode_gate"])
        for source in self.contract["eligible_sources"].values():
            self.assertEqual(source["prerequisite_state"], "PASS")
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_reference_mode_promotion"])
        self.assertTrue(hard["no_accounting_readiness_change"])
        self.assertTrue(hard["no_value_fit_used_for_semantic_mapping"])
        self.assertTrue(hard["no_reconciliation_used_for_semantic_mapping"])

    def test_exact_rmd_boundary_is_frozen(self) -> None:
        target = self.contract["frozen_rmd_target"]
        self.assertEqual(
            target["required_rmd_sectors"],
            ["H", "C", "F", "G", "X", "BNR"],
        )
        self.assertEqual(
            target["required_instruments"],
            ["F2", "F3", "F4", "F5", "F6", "F7", "F8"],
        )
        self.assertEqual(
            target["required_measures"],
            ["stock", "financial_transaction"],
        )
        self.assertEqual(
            target["required_entries"],
            ["assets", "liabilities"],
        )

    def test_mapping_cannot_be_rescued_by_broader_totals_or_fit(self) -> None:
        questions = {
            item["id"]: item["pass_condition"]
            for item in self.contract["review_questions"]
        }
        self.assertIn("no residual sector assignment", questions["SECTOR_MAPPING"])
        self.assertIn("Broader financial-total", questions["INSTRUMENT_MAPPING"])
        self.assertIn("Stock differences", questions["STOCK_FLOW_SEMANTICS"])
        rule = self.contract["semantic_review_pass_rule"]
        self.assertTrue(
            rule["mappings_must_be_frozen_before_historical_values_are_evaluated"]
        )
        self.assertTrue(
            rule["values_or_reconciliation_residuals_may_not_influence_mapping"]
        )

    def test_lineage_cannot_be_misreported_as_independent_validation(self) -> None:
        euro = self.contract["eligible_sources"]["EUROSTAT_NASQ_10_F_CP"]
        oecd = self.contract["eligible_sources"]["OECD_COUNTERPART_DATAFLOWS"]
        self.assertIn("NOT_INDEPENDENT", euro["source_lineage_classification"])
        self.assertIn("NOT_ASSUMED_INDEPENDENT", oecd["source_lineage_classification"])
        self.assertTrue(
            self.contract["hard_rules"]["no_source_independence_claim_from_republication"]
        )

    def test_pass_only_authorizes_separate_historical_extraction_contract(self) -> None:
        rule = self.contract["semantic_review_pass_rule"]
        self.assertEqual(
            rule["effect_if_pass"],
            "AUTHORIZE_SEPARATE_PREREGISTERED_EXACT_HISTORICAL_EXTRACTION_CONTRACT_ONLY",
        )
        extraction = self.contract[
            "exact_historical_extraction_contract_requirements_if_pass"
        ]
        self.assertTrue(extraction["must_be_separately_preregistered"])
        self.assertEqual(extraction["required_common_history_minimum_quarters"], 40)
        self.assertTrue(extraction["system_reconciliation_gate_must_be_preregistered_before_value_review"])
        self.assertTrue(extraction["no_post_result_mapping_changes"])


if __name__ == "__main__":
    unittest.main()
