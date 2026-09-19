from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "dynamics"
    / "sectoral_financial_positions_oecd_counterpart_probe_contract.json"
)


class SectoralFinancialPositionsOECDCounterpartProbeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(P.read_text(encoding="utf-8"))

    def test_exact_oecd_counterpart_dataflows_are_frozen(self) -> None:
        flows = {
            item["id"]: item
            for item in self.contract["provider"]["dataflows"]
        }
        self.assertEqual(
            flows["stocks_counterpart"]["flow_ref"],
            "OECD.SDD.NAD,DSD_NASEC20@DF_T725R_Q",
        )
        self.assertEqual(
            flows["flows_counterpart"]["flow_ref"],
            "OECD.SDD.NAD,DSD_NASEC20@DF_T625R_Q",
        )

    def test_query_is_country_scoped_and_structure_driven(self) -> None:
        q = self.contract["query_scope"]
        self.assertEqual(q["reference_area"], "ROU")
        self.assertEqual(q["frequency"], "Q")
        self.assertEqual(q["start_period"], "2014-Q1")
        self.assertEqual(q["end_period"], "2026-Q1")
        self.assertIn("derive", q["dimension_order_source"])
        self.assertEqual(q["all_other_key_dimensions"], "ALL_AVAILABLE_VALUES")

    def test_discovery_probe_cannot_promote_or_remap(self) -> None:
        self.assertFalse(self.contract["formal_reference_mode_gate"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_sector_mapping_in_probe"])
        self.assertTrue(hard["no_instrument_mapping_in_probe"])
        self.assertTrue(hard["no_reconciliation_test_in_probe"])
        self.assertTrue(hard["no_reference_mode_promotion"])
        self.assertTrue(hard["no_accounting_readiness_change"])
        self.assertTrue(hard["no_historical_phase_A_D_reinterpretation"])

    def test_pass_only_authorizes_explicit_review(self) -> None:
        rule = self.contract["discovery_pass_rule"]
        self.assertEqual(
            rule["required_dataflows"],
            ["stocks_counterpart", "flows_counterpart"],
        )
        self.assertEqual(
            rule["effect_if_pass"],
            "ROMANIA_COUNTRY_DATA_RETAINED_FOR_EXPLICIT_SEMANTIC_AND_LINEAGE_REVIEW_ONLY",
        )
        self.assertEqual(
            rule["effect_if_fail"],
            "NO_REOPEN_EVIDENCE_FROM_OECD_COUNTRY_COVERAGE_PROBE",
        )


if __name__ == "__main__":
    unittest.main()
