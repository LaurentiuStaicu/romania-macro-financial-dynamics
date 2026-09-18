from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProvenanceTests(unittest.TestCase):
    def test_vintage_contract_forbids_retroactive_assumption(self) -> None:
        contract = json.loads(
            (ROOT / "data" / "provenance" / "source_vintage_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(
            contract["principles"]["missing_raw_bytes_may_not_be_reconstructed_by_assumption"]
        )
        self.assertTrue(
            contract["principles"][
                "later_live_refetch_is_not_the_original_vintage_unless_sha256_matches"
            ]
        )

    def test_v010_gap_is_partially_recovered_not_silently_closed(self) -> None:
        registry = json.loads(
            (
                ROOT
                / "data"
                / "provenance"
                / "validation_recovery_vintage_status.json"
            ).read_text(encoding="utf-8")
        )
        vintage = registry["vintages"][0]
        self.assertEqual(vintage["status"], "PARTIAL_RAW_RECOVERY")
        self.assertEqual(vintage["raw_payloads_materialized_in_repository"], 3)
        self.assertEqual(vintage["raw_payloads_not_recovered"], 1)
        self.assertFalse(vintage["exact_vintage_reproducible_from_repository"])
        self.assertEqual(
            vintage["unrecovered_raw_sources"],
            ["bis_policy_rate_xml"],
        )
        self.assertTrue(
            vintage["live_audit_2026_09_18"][
                "all_normalized_statistical_inputs_match_retained_model_inputs"
            ]
        )

    def test_offline_provenance_verifier(self) -> None:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_validation_recovery_provenance.py")],
            check=True,
            cwd=ROOT,
        )


if __name__ == "__main__":
    unittest.main()
