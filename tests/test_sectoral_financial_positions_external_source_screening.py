from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "dynamics"
    / "sectoral_financial_positions_external_source_screening.json"
)


class SectoralFinancialPositionsExternalSourceScreeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(P.read_text(encoding="utf-8"))

    def test_eurostat_counterpart_dataset_is_priority_probe_candidate(self) -> None:
        by_id = {item["id"]: item for item in self.review["screened_sources"]}
        eurostat = by_id["EUROSTAT_QUARTERLY_COUNTERPART_FINANCIAL_ACCOUNTS"]
        self.assertEqual(eurostat["dataset_code"], "nasq_10_f_cp")
        self.assertTrue(eurostat["romania_exact_observation_coverage_retained"])
        self.assertEqual(
            eurostat["status"],
            "DISCOVERY_PASS_SEMANTIC_REVIEW_FAIL_INSTRUMENT_SCOPE_NO_REOPEN",
        )
        self.assertTrue(
            self.review["decision"]["eurostat_counterpart_probe_justified"]
        )
        self.assertEqual(
            self.review["decision"]["discovery_priority"][0],
            "OECD_COUNTERPART_DATAFLOWS",
        )

    def test_eurostat_lineage_is_republication_not_independent_measurement(self) -> None:
        by_id = {item["id"]: item for item in self.review["screened_sources"]}
        eurostat = by_id["EUROSTAT_QUARTERLY_COUNTERPART_FINANCIAL_ACCOUNTS"]
        lineage = " ".join(eurostat["lineage_boundary"]).lower()
        self.assertIn("validated", lineage)
        self.assertIn("ecb", lineage)
        self.assertIn("not assumed", lineage)
        self.assertIn("independent", lineage)

    def test_oecd_counterpart_dataflows_are_only_probe_candidates(self) -> None:
        by_id = {item["id"]: item for item in self.review["screened_sources"]}
        oecd = by_id["OECD_QUARTERLY_COUNTERPART_FINANCIAL_ACCOUNTS"]
        self.assertEqual(
            oecd["candidate_dataflows"]["stocks"]["id"],
            "OECD.SDD.NAD,DSD_NASEC20@DF_T725R_Q",
        )
        self.assertEqual(
            oecd["candidate_dataflows"]["flows"]["id"],
            "OECD.SDD.NAD,DSD_NASEC20@DF_T625R_Q",
        )
        self.assertTrue(oecd["romania_exact_observation_coverage_retained"])
        self.assertEqual(
            oecd["status"],
            "DISCOVERY_PASS_SEMANTIC_REVIEW_FAIL_SECTOR_SCOPE_NO_REOPEN",
        )
        self.assertEqual(
            oecd["semantic_lineage_review_verdict"],
            "FAIL_REQUIRED_SECTOR_SCOPE_INCOMPLETE",
        )

    def test_oecd_lineage_is_not_assumed_independent(self) -> None:
        by_id = {item["id"]: item for item in self.review["screened_sources"]}
        oecd = by_id["OECD_QUARTERLY_COUNTERPART_FINANCIAL_ACCOUNTS"]
        lineage = " ".join(oecd["lineage_boundary"]).lower()
        self.assertIn("oecd-ecb", lineage)
        self.assertIn("not assumed", lineage)
        self.assertIn("lineage", lineage)

    def test_screening_does_not_reopen_or_promote(self) -> None:
        decision = self.review["decision"]
        hard = self.review["hard_rules"]
        self.assertFalse(decision["immediate_reference_mode_reopen_authorized"])
        self.assertFalse(decision["reference_mode_promotion_authorized"])
        self.assertFalse(decision["accounting_readiness_change"])
        self.assertTrue(decision["oecd_probe_justified"])
        self.assertEqual(
            decision["external_counterpart_recovery_state"],
            "EXHAUSTED_NO_SEMANTICALLY_ADMISSIBLE_CURRENT_PUBLIC_SOURCE",
        )
        self.assertEqual(decision["reference_mode_readiness_change"], 0)
        self.assertTrue(hard["no_reference_mode_promotion_from_discovery_probe"])
        self.assertTrue(hard["no_accounting_readiness_promotion"])
        self.assertTrue(hard["no_behavioural_closure_change"])

    def test_historical_ecb_recovery_chain_remains_frozen(self) -> None:
        state = self.review["frozen_current_state"]
        self.assertEqual(state["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(state["readiness_count_change"], 0)
        self.assertEqual(
            state["internal_source_recovery"],
            "FROZEN_UNTIL_REOPEN_TRIGGER",
        )
        self.assertEqual(state["canonical_accounting_instruments_complete"], ["F3"])


if __name__ == "__main__":
    unittest.main()
