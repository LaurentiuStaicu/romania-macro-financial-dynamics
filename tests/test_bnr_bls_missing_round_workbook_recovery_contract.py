from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_bnr_bls_missing_round_workbook_recovery import signature

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_workbook_recovery_contract.json"
)


class BNRBLSMissingRoundWorkbookRecoveryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(P.read_text(encoding="utf-8"))

    def test_exact_four_canonical_missing_quarters_are_targeted(self) -> None:
        self.assertEqual(
            self.contract["target_missing_quarters"],
            ["2023-Q2", "2023-Q3", "2024-Q2", "2025-Q2"],
        )
        self.assertEqual(
            [item["quarter"] for item in self.contract["rounds"]],
            self.contract["target_missing_quarters"],
        )

    def test_known_2023_endpoints_are_explicit_not_generated(self) -> None:
        by_quarter = {
            item["quarter"]: item for item in self.contract["rounds"]
        }
        for quarter in ("2023-Q2", "2023-Q3"):
            item = by_quarter[quarter]
            self.assertEqual(len(item["url_candidates"]), 1)
            self.assertEqual(
                item["discovery_status"],
                "EXACT_ENDPOINT_CONFIRMED_BY_WEB_AS_APPLICATION_VND_MS_EXCEL",
            )
            self.assertTrue(
                item["url_candidates"][0].startswith(
                    "https://www.bnr.ro/uploads/"
                )
            )

    def test_2025_url_is_not_invented(self) -> None:
        by_quarter = {
            item["quarter"]: item for item in self.contract["rounds"]
        }
        item = by_quarter["2025-Q2"]
        self.assertEqual(item["url_candidates"], [])
        self.assertEqual(
            item["discovery_status"],
            "OFFICIAL_ANNEX_EXISTENCE_KNOWN_EXACT_WORKBOOK_URL_UNIDENTIFIED",
        )

    def test_probe_prohibits_bruteforce_parsing_and_panel_mutation(self) -> None:
        rules = self.contract["probe_rules"]
        self.assertTrue(rules["no_wildcard_url_generation"])
        self.assertTrue(rules["no_timestamp_brute_force"])
        self.assertTrue(rules["no_directory_scraping"])
        self.assertTrue(rules["no_value_extraction"])
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_canonical_panel_mutation_in_probe"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_synthetic_quarter_creation"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])

    def test_binary_signature_gate_is_exact(self) -> None:
        self.assertEqual(
            signature(bytes.fromhex("D0CF11E0A1B11AE1") + b"x"),
            "OLE2_CFBF_D0CF11E0A1B11AE1",
        )
        self.assertEqual(signature(b"PK\x03\x04rest"), "ZIP_PK_0304")
        self.assertEqual(signature(b"<html>"), "OTHER")

    def test_live_execution_is_manual_only(self) -> None:
        self.assertEqual(
            self.contract["execution_policy"],
            "MANUAL_ONLY_LIVE_SOURCE_ACQUISITION",
        )
        self.assertTrue(
            self.contract["promotion_boundary"][
                "accessible_workbook_does_not_fill_panel"
            ]
        )


if __name__ == "__main__":
    unittest.main()
