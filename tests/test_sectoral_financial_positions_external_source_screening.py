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
        self.assertFalse(oecd["romania_exact_observation_coverage_retained"])
        self.assertEqual(
            oecd["status"],
            "CANDIDATE_FOR_PREREGISTERED_COUNTRY_COVERAGE_PROBE_NOT_REOPEN_EVIDENCE",
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
