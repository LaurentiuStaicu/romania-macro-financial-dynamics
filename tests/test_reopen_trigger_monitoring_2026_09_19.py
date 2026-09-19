from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ReopenTriggerMonitoring20260919Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load("model/registries/reopen_trigger_monitoring_2026_09_19.json")
        self.m = load("model/registries/model_contract.json")

    def test_no_trigger_is_promoted_from_nonconfirmation(self) -> None:
        self.assertEqual(
            self.a["status"],
            "NO_DECLARED_REOPEN_TRIGGER_SATISFIED_BASELINE_HOLD_CONTINUES",
        )
        d = self.a["decision"]
        self.assertFalse(d["any_declared_reopen_trigger_satisfied"])
        self.assertFalse(d["accounting_instrument_reopened"])
        self.assertFalse(d["reference_mode_reopened"])
        self.assertFalse(d["behavioural_mechanism_reopened"])

    def test_baseline_hold_remains_closed(self) -> None:
        d = self.a["decision"]
        self.assertFalse(d["active_calibration_cycle_open"])
        self.assertFalse(d["holdout_or_reserved_response_opening_authorized"])
        self.assertFalse(d["estimation_or_refit_authorized"])
        self.assertFalse(d["system_dynamics_feedback_activation_authorized"])
        self.assertFalse(d["behavioural_closure_activation_authorized"])
        self.assertEqual(d["current_scientific_state"], "EVIDENCE_TRIGGERED_BASELINE_HOLD")

    def test_policy_event_is_not_created_from_unchanged_rate(self) -> None:
        f = self.a["findings"]["prospective_monetary_policy_event"]
        self.assertEqual(f["status"], "NO_REOPEN_UNCHANGED_RATE_MEETING")
        self.assertIn("non-zero", f["trigger_test"])
        self.assertIn("remain closed", f["conclusion"])

    def test_source_nonconfirmation_is_not_source_absence(self) -> None:
        f = self.a["findings"]["fx_inflation_direct_import_price"]
        self.assertEqual(
            f["status"],
            "NO_REOPEN_ROMANIA_EXACT_TRANSACTION_PRICE_SERIES_NOT_CONFIRMED",
        )
        self.assertIn("not been confirmed", f["conclusion"])
        accounting = self.a["findings"]["accounting_and_sectoral_financial_positions"]
        self.assertIn("not a proof", accounting["caveat"])

    def test_monitoring_snapshot_is_retained_after_later_selective_reopen(self) -> None:
        stage = self.m["scientific_stage"]
        self.assertEqual(
            stage["latest_reopen_trigger_monitoring"],
            "model/registries/reopen_trigger_monitoring_2026_09_19.json",
        )
        self.assertEqual(
            stage["latest_reopen_trigger_monitoring_status"],
            "NO_DECLARED_REOPEN_TRIGGER_SATISFIED_BASELINE_HOLD_CONTINUES",
        )
        self.assertEqual(
            stage["latest_reopen_trigger_monitoring_superseded_for"],
            ["fiscal_primary_balance_reaction"],
        )
        self.assertEqual(stage["next_operational_state"], "EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertTrue(stage["selective_reopen_active"])
        self.assertIsNone(stage["active_autonomous_empirical_task"])
        self.assertEqual(
            stage["active_manual_empirical_gate"],
            "FISCAL_PRIMARY_BALANCE_CAPB_REALTIME_VINTAGE_MATERIALISATION",
        )


if __name__ == "__main__":
    unittest.main()
