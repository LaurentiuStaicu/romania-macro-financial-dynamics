from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class BNRBLS2025Q2SourceDiscoveryTerminalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.t = load("model/calibration_validation/bnr_bls_2025q2_source_discovery_terminal_assessment.json")
        self.r = load("model/calibration_validation/bnr_bls_missing_round_workbook_recovery_contract.json")
        self.p = load("model/calibration_validation/bnr_bls_canonical_panel_promotion_review.json")
        self.m = load("model/calibration_validation/mechanism_source_readiness.json")
        self.a = load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json")

    def test_stage_is_closed_without_claiming_source_absence(self):
        self.assertEqual(
            self.t["status"],
            "STAGE_CLOSED_FROZEN_SINGLE_GAP_2025_Q2_UNDER_CURRENT_PUBLIC_DISCOVERY_SURFACE_NO_MODEL_EFFECT",
        )
        e = self.t["exhaustion_assessment"]
        self.assertTrue(e["current_public_discovery_surface_exhausted_for_exact_endpoint_identity"])
        self.assertFalse(e["source_absence_claimed"])
        self.assertFalse(e["same_query_repetition_authorized"])
        self.assertFalse(e["filename_pattern_generation_authorized"])
        self.assertFalse(e["timestamp_bruteforce_authorized"])
        self.assertFalse(e["internal_endpoint_guessing_authorized"])

    def test_canonical_panel_remains_11_of_12_with_only_2025q2_missing(self):
        c = self.t["canonical_state"]
        self.assertEqual(c["expected_quarters"], 12)
        self.assertEqual(c["observed_quarters"], 11)
        self.assertEqual(c["missing_quarters"], ["2025-Q2"])
        self.assertFalse(c["rounded_publication_values_are_canonical"])
        self.assertEqual(self.p["approved_post_promotion"]["missing_quarters"], ["2025-Q2"])

    def test_recovery_contract_keeps_2025q2_without_invented_candidate(self):
        q2 = next(x for x in self.r["rounds"] if x["quarter"] == "2025-Q2")
        self.assertEqual(q2["url_candidates"], [])
        self.assertEqual(
            q2["discovery_status"],
            "OFFICIAL_ANNEX_EXISTENCE_KNOWN_EXACT_WORKBOOK_URL_UNIDENTIFIED",
        )
        self.assertEqual(
            self.r["source_discovery_terminal_assessment"],
            "model/calibration_validation/bnr_bls_2025q2_source_discovery_terminal_assessment.json",
        )

    def test_no_model_permission_follows_from_stage_closure(self):
        d = self.t["terminal_disposition"]
        for key in (
            "source_byte_acquisition_authorized",
            "numeric_extraction_authorized",
            "canonical_panel_mutation_authorized",
            "parameter_estimation_authorized",
            "model_selection_authorized",
            "lag_selection_authorized",
            "holdout_opening_authorized",
            "system_dynamics_activation",
            "behavioural_closure_change",
        ):
            self.assertFalse(d[key])
        effect = self.t["model_effect"]
        self.assertFalse(effect["mechanism_classification_change"])
        self.assertFalse(effect["active_calibration_cycle_open"])
        self.assertTrue(effect["canonical_panel_remains_11_of_12"])
        self.assertFalse(effect["bank_credit_feedback_activation"])

    def test_authority_files_link_terminal_assessment(self):
        path = "model/calibration_validation/bnr_bls_2025q2_source_discovery_terminal_assessment.json"
        status = "STAGE_CLOSED_FROZEN_SINGLE_GAP_2025_Q2_UNDER_CURRENT_PUBLIC_DISCOVERY_SURFACE_NO_MODEL_EFFECT"
        credit = next(x for x in self.m["mechanisms"] if x["id"] == "aggregate_bank_credit_response")
        self.assertEqual(credit["bnr_bls_2025q2_source_discovery_terminal_assessment"], path)
        self.assertEqual(credit["bnr_bls_2025q2_source_discovery_stage_status"], status)
        self.assertEqual(self.a["bnr_bls_2025q2_source_discovery_terminal_assessment"], path)
        self.assertEqual(self.a["bnr_bls_2025q2_source_discovery_stage_status"], status)
        self.assertEqual(self.r["source_discovery_stage_status"], status)


if __name__ == "__main__":
    unittest.main()
