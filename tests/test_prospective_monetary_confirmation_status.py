from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ProspectiveMonetaryConfirmationStatusTests(unittest.TestCase):
    def test_no_identifying_event_does_not_open_confirmation(self) -> None:
        status = load(
            "model/calibration_validation/prospective_monetary_confirmation_status.json"
        )
        holdout = load(
            "model/calibration_validation/validation_recovery_holdout.json"
        )
        registry = load("model/empirical_dynamics/mechanism_registry.json")

        monetary = next(
            item for item in registry["mechanisms"]
            if item["id"] == "monetary_policy_lending_rate_pass_through"
        )

        self.assertEqual(
            status["identification_gate"]["nonzero_policy_rate_events_in_reserved_window"],
            0,
        )
        self.assertFalse(
            status["identification_gate"]["identifying_driver_variation_available"]
        )
        self.assertFalse(status["prospective_window"]["formal_confirmation_opened"])
        self.assertFalse(status["prospective_window"]["response_series_values_inspected"])
        self.assertTrue(status["prospective_window"]["policy_driver_only_checked"])
        self.assertEqual(monetary["classification"], "CANDIDATE")
        self.assertEqual(
            status["frozen_beta"],
            holdout["frozen_beta"],
        )

    def test_august_decision_is_hold_and_next_meeting_is_future_to_as_of(self) -> None:
        status = load(
            "model/calibration_validation/prospective_monetary_confirmation_status.json"
        )
        decision = status["policy_driver_evidence"]["last_decision_in_reserved_window"]
        meeting = status["policy_driver_evidence"]["next_scheduled_policy_meeting"]

        self.assertEqual(decision["date"], "2026-08-10")
        self.assertEqual(decision["policy_rate_pct"], 6.50)
        self.assertEqual(decision["decision"], "UNCHANGED")
        self.assertGreater(
            date.fromisoformat(meeting["date"]),
            date.fromisoformat(status["as_of_date"]),
        )

    def test_reserved_response_data_remain_uncontaminated(self) -> None:
        status = load(
            "model/calibration_validation/prospective_monetary_confirmation_status.json"
        )
        rules = status["hard_rules"]

        self.assertTrue(
            rules["do_not_inspect_reserved_MIR_response_values_before_identifying_event"]
        )
        self.assertTrue(rules["do_not_refit_beta"])
        self.assertTrue(rules["do_not_respecify_candidate"])
        self.assertTrue(rules["do_not_open_NFC_holdout"])
        self.assertTrue(rules["do_not_claim_validation_from_elapsed_time"])
        self.assertEqual(
            status["disposition"]["validated_reference_behavioural_mechanisms"],
            0,
        )
        self.assertEqual(
            status["disposition"]["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


    def test_model_contract_registers_prospective_status(self) -> None:
        model = load("model/registries/model_contract.json")
        self.assertEqual(
            model["calibration_validation"][
                "prospective_monetary_confirmation_status"
            ],
            "model/calibration_validation/prospective_monetary_confirmation_status.json",
        )



    def test_prospective_contract_freezes_form_parameter_and_event_gate(self) -> None:
        contract = load(
            "model/calibration_validation/prospective_monetary_confirmation_contract.json"
        )
        holdout = load(
            "model/calibration_validation/validation_recovery_holdout.json"
        )

        inherited = contract["inherited_freeze"]
        self.assertEqual(inherited["candidate"], "delta_policy_contemporaneous")
        self.assertEqual(inherited["frozen_beta"], holdout["frozen_beta"])
        self.assertFalse(inherited["candidate_form_may_change"])
        self.assertFalse(inherited["beta_may_change"])
        self.assertFalse(inherited["causal_claim_allowed"])

        formal = contract["staged_evaluation"]["stage_3_formal_confirmation"]
        self.assertEqual(formal["minimum_distinct_nonzero_policy_event_months"], 4)
        self.assertEqual(formal["minimum_cumulative_absolute_policy_change_pp"], 1.0)
        self.assertTrue(formal["event_conditioned_evaluation"])
        self.assertEqual(
            formal["gates"]["candidate_rmse_improvement_vs_persistence_fraction"],
            0.05,
        )

    def test_first_event_is_diagnostic_only(self) -> None:
        contract = load(
            "model/calibration_validation/prospective_monetary_confirmation_contract.json"
        )
        first = contract["staged_evaluation"]["stage_1_first_event_diagnostic"]
        self.assertEqual(first["status_effect"], "DIAGNOSTIC_ONLY_NO_VALIDATION")
        self.assertIn("cannot validate", first["rule"])

    def test_october_event_response_cannot_be_opened_before_december_release(self) -> None:
        contract = load(
            "model/calibration_validation/prospective_monetary_confirmation_contract.json"
        )
        releases = {
            item["reference_period"]: item["release_date"]
            for item in contract["current_schedule_evidence"]["ECB_MIR_release_calendar"][
                "scheduled_releases"
            ]
        }
        self.assertEqual(releases["2026-10"], "2026-12-02")
        boundary = contract["prospective_data_boundary"]
        self.assertTrue(boundary["no_response_peeking_before_official_release"])
        self.assertEqual(
            boundary["identifying_month_definition"],
            "A calendar month in the reserved window for which policy[t]-policy[t-1] is non-zero.",
        )

    def test_model_contract_registers_prospective_contract(self) -> None:
        model = load("model/registries/model_contract.json")
        self.assertEqual(
            model["calibration_validation"]["prospective_monetary_confirmation_contract"],
            "model/calibration_validation/prospective_monetary_confirmation_contract.json",
        )


if __name__ == "__main__":
    unittest.main()
