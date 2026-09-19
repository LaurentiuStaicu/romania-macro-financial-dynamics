from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class MechanismSourceReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.readiness = load(
            "model/calibration_validation/mechanism_source_readiness.json"
        )

    def test_global_state_does_not_confuse_source_readiness_with_validation(self) -> None:
        state = self.readiness["global_state"]
        self.assertFalse(state["active_calibration_cycle_open"])
        self.assertEqual(state["validated_reference_behavioural_mechanisms"], 0)
        self.assertFalse(state["behavioural_closure_active"])
        self.assertEqual(state["reference_mode_readiness"], "9/10")

    def test_no_listed_mechanism_is_authorized_for_estimation_or_refit(self) -> None:
        for mechanism in self.readiness["mechanisms"]:
            self.assertFalse(
                mechanism["estimation_or_refit_allowed"],
                mechanism["id"],
            )

    def test_readiness_map_covers_every_non_rejected_registry_mechanism_once(self) -> None:
        registry = load("model/empirical_dynamics/mechanism_registry.json")
        required = {
            item["id"]
            for item in registry["mechanisms"]
            if item["classification"] != "REJECTED"
        }
        listed = [item["id"] for item in self.readiness["mechanisms"]]
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), required)
        self.assertEqual(
            self.readiness["coverage_rule"]["scope"],
            "ALL_NON_REJECTED_MECHANISMS",
        )
        self.assertFalse(
            self.readiness["coverage_rule"]["duplicate_entries_allowed"]
        )
        self.assertFalse(
            self.readiness["coverage_rule"]["missing_entries_allowed"]
        )

    def test_next_step_is_offline_runner_implementation_not_calibration(self) -> None:
        step = self.readiness["current_next_step"]
        self.assertEqual(
            step["mechanism_id"],
            "sovereign_yield_spread_response",
        )
        self.assertEqual(
            step["action"],
            "IMPLEMENT_OFFLINE_SOVEREIGN_SELECTION_RUNNER_NO_EXECUTION",
        )
        self.assertFalse(step["calibration_cycle_open"])

        mechanisms = {
            item["id"]: item for item in self.readiness["mechanisms"]
        }
        sovereign = mechanisms["sovereign_yield_spread_response"]
        self.assertEqual(
            sovereign["source_readiness"],
            "SOURCE_VINTAGE_RETAINED_STRUCTURAL_SELECTION_CONTRACT_FROZEN_RUNNER_PENDING",
        )
        self.assertEqual(
            sovereign["live_execution_policy"],
            "MANUAL_ONLY_LIVE_SOURCE_EVIDENCE",
        )
        self.assertEqual(
            sovereign["materialiser_workflow"],
            ".github/workflows/sovereign-yield-quarterly-materialisation.yml",
        )

    def test_waiting_and_deferred_mechanisms_remain_frozen(self) -> None:
        mechanisms = {
            item["id"]: item for item in self.readiness["mechanisms"]
        }
        self.assertEqual(
            mechanisms["monetary_policy_lending_rate_pass_through"][
                "priority_group"
            ],
            "WAIT_FOR_EXTERNAL_EVENT",
        )
        self.assertEqual(
            mechanisms["government_refinancing_effective_rate"][
                "priority_group"
            ],
            "DEFER_UNTIL_NEW_SOURCE",
        )
        self.assertEqual(
            mechanisms["monetary_policy_reaction_function"][
                "priority_group"
            ],
            "DEFER_UNTIL_REACTION_FUNCTION_IDENTIFICATION_CONTRACT",
        )
        self.assertEqual(
            mechanisms["external_fx_refinancing_feedback"][
                "priority_group"
            ],
            "DEFER_UNTIL_CURRENCY_RESIDUAL_MATURITY_HEDGING_SOURCE",
        )


if __name__ == "__main__":
    unittest.main()
