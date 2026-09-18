from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BPSF2SectorStructureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "bps_f2_sector_structure_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_source_structure_only(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["source_structure_only_no_benchmark_mutation"])
        self.assertTrue(rules["no_total_F2_promotion"])
        self.assertTrue(rules["no_F21_materialization"])

    def test_no_coarse_sector_split(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_split_of_S1P_by_shares"])
        self.assertTrue(rules["no_split_of_S1V_by_shares"])
        self.assertTrue(rules["no_inference_that_unpublished_detailed_sector_is_zero"])

    def test_concept_and_unit_bridges_remain_required(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_assumption_BPS_F2_equals_QSA_F2_without_definition_bridge"])
        self.assertTrue(rules["BPM6_ESA_deposit_loan_classification_difference_must_remain_explicit"])
        self.assertTrue(rules["EUR_RON_must_not_be_combined_without_conversion_bridge"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
