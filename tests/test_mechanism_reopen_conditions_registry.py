from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MechanismReopenConditionsRegistryTests(unittest.TestCase):
    def setUp(self):
        self.r = load("model/calibration_validation/mechanism_reopen_conditions_registry.json")
        self.s = load("model/calibration_validation/mechanism_source_readiness.json")

    def test_registry_covers_exactly_the_source_readiness_mechanisms(self):
        expected = {x["id"] for x in self.s["mechanisms"]}
        actual = set(self.r["mechanisms"])
        self.assertEqual(actual, expected)

    def test_registry_matches_classification_and_source_readiness(self):
        source = {x["id"]: x for x in self.s["mechanisms"]}
        for mechanism_id, entry in self.r["mechanisms"].items():
            self.assertEqual(entry["classification"], source[mechanism_id]["classification"])
            self.assertEqual(
                entry["source_readiness"],
                source[mechanism_id]["source_readiness"],
            )

    def test_every_mechanism_has_a_real_reopen_trigger_and_non_reopen_boundary(self):
        for mechanism_id, entry in self.r["mechanisms"].items():
            reopen = entry["reopen_when"]
            if isinstance(reopen, list):
                self.assertGreater(len(reopen), 0, mechanism_id)
                self.assertTrue(all(isinstance(x, str) and x.strip() for x in reopen))
            else:
                self.assertIsInstance(reopen, str, mechanism_id)
                self.assertTrue(reopen.strip(), mechanism_id)

            blocked = entry["evidence_that_does_not_reopen"]
            self.assertIsInstance(blocked, list, mechanism_id)
            self.assertGreater(len(blocked), 0, mechanism_id)
            self.assertTrue(all(isinstance(x, str) and x.strip() for x in blocked))
            self.assertTrue(entry["frozen_boundary"].strip(), mechanism_id)
            self.assertTrue(entry["reopen_effect"].strip(), mechanism_id)

    def test_governing_evidence_files_exist(self):
        for mechanism_id, entry in self.r["mechanisms"].items():
            evidence = entry["governing_evidence"]
            self.assertGreater(len(evidence), 0, mechanism_id)
            for rel in evidence:
                self.assertTrue((ROOT / rel).is_file(), f"{mechanism_id}: missing {rel}")

    def test_global_closed_baseline_is_preserved(self):
        self.assertEqual(
            self.r["current_baseline_action"],
            "HOLD_CLOSED_BASELINE_UNTIL_DECLARED_REOPEN_TRIGGER",
        )
        self.assertFalse(self.r["current_active_calibration_cycle_open"])
        self.assertEqual(self.r["current_validated_reference_behavioural_mechanisms"], 0)
        self.assertEqual(
            self.s["current_next_step"]["action"],
            self.r["current_baseline_action"],
        )
        self.assertFalse(self.s["current_next_step"]["calibration_cycle_open"])
        path = "model/calibration_validation/mechanism_reopen_conditions_registry.json"
        self.assertEqual(self.s["mechanism_reopen_conditions_registry"], path)
        self.assertEqual(self.s["current_next_step"]["reopen_conditions_registry"], path)

    def test_reopen_never_means_automatic_activation(self):
        g = self.r["governance"]
        self.assertTrue(g["reopen_authorizes_only_the_declared_next_gate"])
        self.assertTrue(g["reopen_does_not_authorize_automatic_estimation_or_refit"])
        self.assertTrue(
            g["reopen_does_not_authorize_holdout_inspection_unless_the_governing_contract_explicitly_does"]
        )
        self.assertTrue(g["reopen_does_not_establish_causality"])
        self.assertTrue(g["reopen_does_not_activate_system_dynamics_feedback"])
        self.assertTrue(g["reopen_does_not_activate_behavioural_closure"])
        self.assertTrue(g["accounting_constraints_remain_binding_across_all_reopened_mechanisms"])

    def test_prospective_monetary_reopen_remains_event_conditioned(self):
        entry = self.r["mechanisms"]["monetary_policy_lending_rate_pass_through"]
        self.assertEqual(
            entry["reopen_effect"],
            "PROSPECTIVE_EVENT_CONDITIONED_DIAGNOSTIC_OR_CONFIRMATION_GATE_ONLY",
        )
        self.assertTrue(any("first non-zero BNR policy-rate event" in x for x in entry["reopen_when"]))
        self.assertTrue(any("four distinct non-zero policy-event months" in x for x in entry["reopen_when"]))

    def test_failed_pre_holdout_cycles_cannot_be_reopened_by_post_outcome_respecification(self):
        for mechanism_id in (
            "exchange_rate_pass_through_to_inflation",
            "sovereign_yield_spread_response",
            "corporate_investment_response",
            "fiscal_primary_balance_reaction",
        ):
            entry = self.r["mechanisms"][mechanism_id]
            joined = " ".join(entry["evidence_that_does_not_reopen"]).lower()
            self.assertTrue(
                "final evaluation" in joined
                or "final evaluation window" in joined
                or "untouched final evaluation" in joined
            )


if __name__ == "__main__":
    unittest.main()
