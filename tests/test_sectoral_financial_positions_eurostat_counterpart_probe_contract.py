from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "dynamics"
    / "sectoral_financial_positions_eurostat_counterpart_probe_contract.json"
)


class SectoralFinancialPositionsEurostatCounterpartProbeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(P.read_text(encoding="utf-8"))

    def test_exact_dataset_and_recent_romania_scope_are_frozen(self) -> None:
        provider = self.contract["provider"]
        scope = self.contract["query_scope"]
        self.assertEqual(provider["dataset_code"], "nasq_10_f_cp")
        self.assertEqual(scope["geo"], "RO")
        self.assertEqual(scope["sinceTimePeriod"], "2025-Q1")
        self.assertEqual(scope["untilTimePeriod"], "2026-Q1")
        self.assertEqual(
            scope["all_other_dimensions"],
            "UNFILTERED_FOR_SCHEMA_DISCOVERY",
        )

    def test_lineage_is_explicitly_not_independent(self) -> None:
        lineage = " ".join(
            self.contract["scientific_lineage_boundary"]
        ).lower()
        self.assertIn("validated", lineage)
        self.assertIn("eurostat", lineage)
        self.assertIn("not assumed", lineage)
        self.assertIn("independent", lineage)

    def test_probe_is_not_a_reference_mode_gate(self) -> None:
        self.assertFalse(self.contract["formal_reference_mode_gate"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_sector_mapping_in_probe"])
        self.assertTrue(hard["no_instrument_mapping_in_probe"])
        self.assertTrue(hard["no_reconciliation_test_in_probe"])
        self.assertTrue(hard["no_reference_mode_promotion"])
        self.assertTrue(hard["no_accounting_readiness_change"])
        self.assertTrue(hard["no_historical_phase_A_D_reinterpretation"])

    def test_pass_only_authorizes_mapping_lineage_review(self) -> None:
        rule = self.contract["discovery_pass_rule"]
        self.assertEqual(rule["required_geo_identity"], "RO")
        self.assertEqual(rule["minimum_non_null_observations"], 1)
        self.assertEqual(
            rule["effect_if_pass"],
            "EUROSTAT_ROMANIA_COUNTERPART_SCHEMA_AND_RECENT_DATA_RETAINED_FOR_EXPLICIT_MAPPING_LINEAGE_REVIEW_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
