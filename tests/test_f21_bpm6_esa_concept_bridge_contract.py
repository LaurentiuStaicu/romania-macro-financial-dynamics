from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F21BPM6ESAConceptBridgeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f21_bpm6_esa_concept_bridge_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_no_promotion_during_concept_audit(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_benchmark_mutation"])
        self.assertTrue(rules["no_F21_materialization"])
        self.assertTrue(rules["no_total_F2_promotion"])

    def test_reserve_asset_instrument_is_exact(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["reserve_assets_F2_must_not_be_replaced_by_total_reserve_assets"])
        self.assertTrue(rules["FA_R_F2_must_be_used_for_reserve_currency_and_deposits"])

    def test_sector_failures_cannot_be_balanced_away(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["negative_implied_F21_beyond_source_precision_blocks_bridge"])
        self.assertTrue(rules["aggregate_reconciliation_cannot_override_sector_level_failures"])
        self.assertTrue(rules["no_residual_reallocation_across_H_C_F_G_BNR"])

    def test_functional_category_coverage_is_complete_before_f21_inference(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["other_investment_plus_reserve_assets_is_not_assumed_full_F2"])
        self.assertTrue(rules["direct_investment_F2_detail_must_be_probed"])
        self.assertTrue(rules["direct_investment_debt_total_FA_D_FL_must_not_substitute_for_F2"])
        self.assertTrue(rules["functional_category_F2_coverage_must_be_complete_before_implied_F21"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
