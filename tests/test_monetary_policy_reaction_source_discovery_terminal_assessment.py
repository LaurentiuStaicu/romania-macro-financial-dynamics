from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MonetaryPolicyReactionSourceDiscoveryTerminalAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.t = load("model/calibration_validation/monetary_policy_reaction_source_discovery_terminal_assessment.json")
        self.s = load("model/calibration_validation/monetary_policy_reaction_source_screening.json")
        self.m = load("model/calibration_validation/mechanism_source_readiness.json")

    def test_stage_is_closed_without_claiming_provider_side_absence(self):
        self.assertEqual(
            self.t["status"],
            "STAGE_CLOSED_FROZEN_UNDER_CURRENT_PUBLIC_DISCOVERY_SURFACE_NO_MODEL_EFFECT",
        )
        e = self.t["exhaustion_assessment"]
        self.assertTrue(
            e[
                "current_public_discovery_surface_exhausted_for_identifying_required_machine_readable_histories"
            ]
        )
        self.assertFalse(e["provider_side_data_absence_claimed"])
        self.assertFalse(e["same_query_repetition_authorized"])
        self.assertFalse(e["chart_digitisation_authorized"])
        self.assertFalse(e["internal_endpoint_guessing_authorized"])

    def test_required_measurement_histories_remain_unretained(self):
        p = self.t["prerequisite_state"]
        self.assertTrue(p["quantitative_private_expectations_concept_confirmed"])
        self.assertTrue(p["quarterly_bnr_gdp_gap_concept_confirmed"])
        self.assertFalse(p["formation_time_expectations_history_retained"])
        self.assertFalse(p["real_time_gap_vintages_retained"])
        self.assertFalse(p["estimation_or_refit_allowed"])

    def test_chart_coordinates_cannot_be_relabelled_as_formation_dates(self):
        e = self.t["exhaustion_assessment"]
        self.assertFalse(e["chart_digitisation_authorized"])
        self.assertFalse(e["target_horizon_coordinate_as_formation_date_authorized"])
        self.assertFalse(e["later_revised_gap_backfill_authorized"])
        self.assertTrue(
            any(
                "target-horizon-shifted chart coordinate" in x
                for x in self.t["non_reopen_conditions"]
            )
        )

    def test_source_screening_and_registry_link_terminal_gate(self):
        path = "model/calibration_validation/monetary_policy_reaction_source_discovery_terminal_assessment.json"
        status = "STAGE_CLOSED_FROZEN_UNDER_CURRENT_PUBLIC_DISCOVERY_SURFACE_NO_MODEL_EFFECT"
        self.assertEqual(self.s["source_discovery_terminal_assessment"], path)
        self.assertEqual(self.s["source_discovery_stage_status"], status)

        mechanism = next(
            x
            for x in self.m["mechanisms"]
            if x["id"] == "monetary_policy_reaction_function"
        )
        self.assertEqual(
            mechanism["monetary_policy_reaction_source_discovery_terminal_assessment"],
            path,
        )
        self.assertEqual(
            mechanism["monetary_policy_reaction_source_discovery_stage_status"],
            status,
        )
        self.assertFalse(mechanism["estimation_or_refit_allowed"])

    def test_no_model_permission_follows_from_stage_closure(self):
        d = self.t["terminal_disposition"]
        for key in (
            "parameter_estimation_authorized",
            "model_selection_authorized",
            "lag_selection_authorized",
            "holdout_opening_authorized",
            "policy_rule_activation",
            "system_dynamics_activation",
            "behavioural_closure_change",
        ):
            self.assertFalse(d[key])
        self.assertTrue(d["observed_policy_rate_remains_exogenous"])

        effect = self.t["model_effect"]
        self.assertFalse(effect["mechanism_classification_change"])
        self.assertEqual(effect["mechanism_classification"], "DEFERRED")
        self.assertFalse(effect["active_calibration_cycle_open"])
        self.assertFalse(effect["estimation_or_refit_allowed"])
        self.assertFalse(effect["policy_rule_activation"])


if __name__ == "__main__":
    unittest.main()
