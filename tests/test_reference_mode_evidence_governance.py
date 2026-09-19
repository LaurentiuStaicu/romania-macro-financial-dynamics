from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ReferenceModeEvidenceGovernanceTests(unittest.TestCase):
    def test_every_ready_mode_has_repository_evidence(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        ready_statuses = set(
            references["closure_readiness_policy"][
                "ready_statuses_for_integrated_quantitative_closure"
            ]
        )
        ready = [
            item for item in references["modes"]
            if item["status"] in ready_statuses
        ]
        self.assertEqual(len(ready), 8)

        for mode in ready:
            self.assertTrue(str(mode["source"]).strip(), mode["id"])
            self.assertNotIn("TBD", str(mode["time_resolution"]), mode["id"])
            self.assertTrue(str(mode["current_endogeneity"]).strip(), mode["id"])

            if "assessment" in mode:
                self.assertTrue(
                    (ROOT / mode["assessment"]).is_file(),
                    mode["id"],
                )
            elif "evidence" in mode:
                evidence = mode["evidence"]
                self.assertTrue(
                    (ROOT / evidence["normalized_series"]).is_file(),
                    mode["id"],
                )
                self.assertTrue(
                    (ROOT / evidence["role_freeze"]).is_file(),
                    mode["id"],
                )
                self.assertTrue(
                    (ROOT / evidence["vintage_status"]).is_file(),
                    mode["id"],
                )
                self.assertTrue(
                    str(evidence["provenance_status"]).strip(),
                    mode["id"],
                )
            else:
                self.fail(f"Ready reference mode lacks evidence pointer: {mode['id']}")

    def test_policy_rate_does_not_overclaim_raw_vintage_recovery(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        vintage = load("data/provenance/validation_recovery_vintage_status.json")
        policy = next(
            item for item in references["modes"]
            if item["id"] == "policy_rate"
        )

        self.assertIn(
            "RAW_BIS_TRANSPORT_ENVELOPE_NOT_EXACTLY_RECOVERED",
            policy["evidence"]["provenance_status"],
        )
        entry = vintage["vintages"][0]
        self.assertEqual(entry["status"], "PARTIAL_RAW_RECOVERY")
        self.assertFalse(entry["exact_vintage_reproducible_from_repository"])
        self.assertIn("bis_policy_rate_xml", entry["unrecovered_raw_sources"])
        self.assertTrue(
            entry["live_audit_2026_09_18"][
                "all_normalized_statistical_inputs_match_retained_model_inputs"
            ]
        )

    def test_ecb_lending_rate_evidence_preserves_byte_identical_recovery(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        vintage = load("data/provenance/validation_recovery_vintage_status.json")
        by_id = {item["id"]: item for item in references["modes"]}

        recovered = set(
            vintage["vintages"][0]["byte_identical_recovered_sources"]
        )
        self.assertIn("ecb_household_housing_new_business_ron", recovered)
        self.assertIn("ecb_nfc_new_business_upto1y_ron", recovered)
        for mode_id in ("household_lending_rate", "nfc_lending_rate"):
            self.assertIn(
                "ECB_RAW_BYTE_IDENTICAL_RECOVERED",
                by_id[mode_id]["evidence"]["provenance_status"],
            )


if __name__ == "__main__":
    unittest.main()
