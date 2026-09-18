from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EurostatF2DetailedSectorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "eurostat_f2_detailed_sector_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_exact_h_c_codes_are_explicit(self) -> None:
        self.assertEqual(self.contract["candidate_rmd_mapping"]["C"], "S11")
        self.assertEqual(self.contract["candidate_rmd_mapping"]["H"], "S1M")

    def test_no_synthetic_split_or_promotion(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_split_of_S1V_by_shares"])
        self.assertTrue(rules["no_missing_to_zero"])
        self.assertTrue(rules["no_F21_materialization"])
        self.assertTrue(rules["no_total_F2_promotion"])

    def test_cross_source_and_concept_bridges_remain_required(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["Eurostat_and_ECB_BPS_vintages_must_not_be_assumed_identical"])
        self.assertTrue(rules["BPM6_and_ESA_F2_must_not_be_assumed_identical"])

    def test_transaction_code_is_discovered_not_guessed(self) -> None:
        self.assertTrue(
            self.contract["hard_rules"][
                "transaction_stk_flow_code_must_be_discovered_from_Eurostat_metadata_or_response_not_guessed"
            ]
        )

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
