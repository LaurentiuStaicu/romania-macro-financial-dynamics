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

    def test_next_step_advances_after_failed_corporate_form(self) -> None:
        step = self.readiness["current_next_step"]
        self.assertEqual(
            step["mechanism_id"],
            "aggregate_bank_credit_response",
        )
        self.assertEqual(
            step["action"],
            "RUN_PRUDENTIAL_COVERAGE_DIAGNOSTIC_NO_ESTIMATION",
        )
        self.assertFalse(step["calibration_cycle_open"])

        mechanisms = {
            item["id"]: item for item in self.readiness["mechanisms"]
        }

        investment = mechanisms["corporate_investment_response"]
        self.assertEqual(
            investment["source_readiness"],
            "FROZEN_TESTED_FORM_FAILED_BEFORE_HOLDOUT",
        )
        self.assertEqual(
            investment["retained_source_vintage"],
            "data/source_vintages/corporate-investment-source-family-vintage-2026-09-19",
        )
        self.assertEqual(
            investment["structural_selection_contract"],
            "model/calibration_validation/corporate_investment_structural_selection_contract.json",
        )
        self.assertEqual(
            investment["selection_result"],
            "model/calibration_validation/corporate_investment_structural_selection_result.json",
        )
        self.assertEqual(
            investment["priority_group"],
            "FREEZE_TESTED_FORM_UNTIL_NEW_EVIDENCE",
        )
        self.assertFalse(investment["estimation_or_refit_allowed"])

        household = mechanisms["household_consumption_response"]
        self.assertEqual(
            household["source_readiness"],
            "BNR_DSTI_WORKBOOK_VINTAGE_RETAINED_LEGACY_XLS_EXTRACTION_NOT_CANONICAL",
        )
        self.assertEqual(
            household["priority_group"],
            "DEFER_UNTIL_DETERMINISTIC_LEGACY_XLS_EXTRACTION_PATH",
        )
        self.assertEqual(
            household["debt_service_source_screening"],
            "model/calibration_validation/debt_service_source_screening.json",
        )
        self.assertFalse(household["estimation_or_refit_allowed"])
        fiscal = mechanisms["fiscal_primary_balance_reaction"]
        self.assertEqual(
            fiscal["source_readiness"],
            "FROZEN_TESTED_ANNUAL_FORM_FAILED_BEFORE_HOLDOUT",
        )
        self.assertEqual(
            fiscal["priority_group"],
            "FREEZE_TESTED_FORM_UNTIL_NEW_EVIDENCE",
        )
        self.assertFalse(fiscal["estimation_or_refit_allowed"])

        fx = mechanisms["exchange_rate_pass_through_to_inflation"]
        self.assertEqual(
            fx["source_readiness"],
            "FROZEN_TESTED_FORM_FAILED_BEFORE_HOLDOUT",
        )
        self.assertEqual(
            fx["priority_group"],
            "FREEZE_TESTED_FORM_UNTIL_NEW_EVIDENCE",
        )
        self.assertFalse(fx["estimation_or_refit_allowed"])

        sovereign = mechanisms["sovereign_yield_spread_response"]
        self.assertEqual(
            sovereign["source_readiness"],
            "FROZEN_TESTED_FORM_FAILED_BEFORE_HOLDOUT",
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
