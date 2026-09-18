from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EurostatF2SectorDetailContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "eurostat_f2_sector_detail_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_no_promotion_or_synthetic_split(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["source_structure_only_no_benchmark_mutation"])
        self.assertTrue(rules["no_F21_materialization"])
        self.assertTrue(rules["no_total_F2_promotion"])
        self.assertTrue(rules["no_split_of_S1V_by_shares"])
        self.assertTrue(rules["no_missing_to_zero"])

    def test_schema_presence_is_not_observation(self) -> None:
        self.assertTrue(
            self.contract["hard_rules"]["schema_code_presence_is_not_observation_availability"]
        )

    def test_bpm6_esa_and_vintage_bridges_remain_explicit(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["Eurostat_BPM6_F2_is_not_presumed_equal_to_QSA_ESA_F2"])
        self.assertTrue(rules["Eurostat_and_ECB_BPS_vintages_may_not_be_assumed_identical"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])


if __name__ == "__main__":
    unittest.main()
