from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FiscalCapbReopenAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load("model/registries/fiscal_capb_reopen_assessment_2026_09_19.json")

    def test_trigger_is_satisfied_but_scope_is_narrow(self) -> None:
        self.assertEqual(
            self.a["status"],
            "FISCAL_PRIMARY_BALANCE_REOPEN_TRIGGER_SATISFIED_PREREGISTRATION_ONLY",
        )
        decision = self.a["trigger_decision"]
        self.assertTrue(decision["declared_reopen_trigger_satisfied"])
        self.assertEqual(
            decision["reopen_scope"],
            "CAPB_REALTIME_VINTAGE_SOURCE_MATERIALISATION_AND_TIMING_ADJUDICATION_ONLY",
        )
        self.assertEqual(
            decision["mechanism_classification_after_reopen"],
            "DEFERRED",
        )

    def test_reopen_does_not_authorize_estimation_or_holdout(self) -> None:
        decision = self.a["trigger_decision"]
        self.assertFalse(decision["active_calibration_cycle_open"])
        self.assertFalse(decision["parameter_estimation_authorized"])
        self.assertFalse(decision["refit_authorized"])
        self.assertFalse(decision["prior_final_evaluation_2018_2024_opening_authorized"])
        self.assertFalse(decision["causal_claim_authorized"])
        self.assertFalse(decision["system_dynamics_feedback_activation_authorized"])
        self.assertFalse(decision["behavioural_closure_activation_authorized"])

    def test_exact_measurement_evidence_is_named(self) -> None:
        series = self.a["trigger_evidence"]["exact_series"]
        self.assertEqual(series["code"], "ROM.1.0.319.0.UBLGBPS")
        self.assertEqual(series["country"], "Romania")
        self.assertIn("excluding interest", series["concept"])
        self.assertTrue(
            self.a["trigger_evidence"]["historical_vintages"][
                "machine_readable_zip_vintages_available"
            ]
        )


if __name__ == "__main__":
    unittest.main()
