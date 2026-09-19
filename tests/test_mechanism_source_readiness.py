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

    def test_next_step_holds_closed_baseline_after_consolidation(self) -> None:
        step = self.readiness["current_next_step"]
        self.assertEqual(
            step["mechanism_id"],
            "SCIENTIFIC_BASELINE",
        )
        self.assertEqual(
            step["action"],
            "HOLD_CLOSED_BASELINE_UNTIL_DECLARED_REOPEN_TRIGGER",
        )
        self.assertFalse(step["calibration_cycle_open"])
        self.assertIn(
            "Cross-registry mechanism readiness",
            step["reason"],
        )

        mechanisms = {
            item["id"]: item for item in self.readiness["mechanisms"]
        }

        aggregate_credit = mechanisms["aggregate_bank_credit_response"]
        self.assertEqual(
            aggregate_credit["source_readiness"],
            "BLS_CANONICAL_8_OF_12_PUBLICATION_BRIDGE_COMPLETE_ENOUGH_FOR_CORROBORATION_MISSING_WORKBOOK_RECOVERY_CONTRACT_FROZEN",
        )
        self.assertEqual(aggregate_credit["observed_round_count"], 8)
        self.assertEqual(
            aggregate_credit["missing_rounds"],
            ["2023-Q2", "2023-Q3", "2024-Q2", "2025-Q2"],
        )
        self.assertEqual(
            aggregate_credit["cross_round_mapping_audit"],
            "model/calibration_validation/bnr_bls_cross_round_mapping_audit.json",
        )
        self.assertEqual(
            aggregate_credit["publication_text_bridge"],
            "model/calibration_validation/bnr_bls_publication_text_bridge.json",
        )
        self.assertEqual(
            aggregate_credit["publication_text_fully_covered_rounds"],
            ["2023-Q3", "2024-Q2", "2025-Q2"],
        )
        self.assertEqual(
            aggregate_credit["publication_text_partial_rounds"],
            ["2023-Q2"],
        )
        self.assertEqual(
            aggregate_credit["publication_text_direct_or_exact_status_quo_observations"],
            20,
        )
        self.assertEqual(
            aggregate_credit["canonical_missing_rounds"],
            ["2023-Q2", "2023-Q3", "2024-Q2", "2025-Q2"],
        )
        self.assertEqual(
            aggregate_credit["missing_round_recovery_contract"],
            "model/calibration_validation/bnr_bls_missing_round_workbook_recovery_contract.json",
        )
        self.assertEqual(
            aggregate_credit["missing_round_recovery_workflow"],
            ".github/workflows/bnr-bls-missing-round-workbook-recovery.yml",
        )
        self.assertEqual(
            aggregate_credit["missing_round_recovery_execution_policy"],
            "MANUAL_ONLY_LIVE_SOURCE_ACQUISITION",
        )
        self.assertEqual(
            aggregate_credit["recovery_endpoint_status"]["2023-Q2"],
            "EXACT_ENDPOINT_CONFIRMED_BY_WEB_AS_APPLICATION_VND_MS_EXCEL_BINARY_NOT_RETAINED",
        )
        self.assertEqual(
            aggregate_credit["recovery_endpoint_status"]["2025-Q2"],
            "OFFICIAL_ANNEX_EXISTENCE_KNOWN_EXACT_URL_UNIDENTIFIED",
        )
        self.assertFalse(aggregate_credit["estimation_or_refit_allowed"])

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
            "COMPLETE_DSTI_TEXT_WINDOW_OFFICIAL_POPULATION_BRIDGE_SCREENED_NOT_FOUND",
        )
        self.assertEqual(
            household["priority_group"],
            "DEFER_UNTIL_NEW_OBSERVED_POPULATION_BRIDGE_SOURCE",
        )
        self.assertEqual(
            household["debt_service_source_screening"],
            "model/calibration_validation/debt_service_source_screening.json",
        )
        self.assertEqual(
            household["dsti_level_publication_boundary_review"],
            "model/calibration_validation/bnr_household_dsti_level_publication_boundary_review.json",
        )
        self.assertEqual(
            household["confirmed_publication_text_quarters"],
            [
                "2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4",
                "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4",
                "2025-Q1", "2025-Q2",
            ],
        )
        self.assertEqual(household["publication_text_window"]["observed_quarters"], 10)
        self.assertEqual(household["publication_text_window"]["missing_quarters"], [])
        self.assertEqual(household["publication_text_window"]["coverage_fraction"], 1.0)
        self.assertFalse(
            household["publication_text_window"]["exact_machine_readable_history_retained"]
        )
        self.assertFalse(household["registered_macro_dsr_identified"])
        self.assertTrue(household["alternative_housing_loan_burden_observed"])
        self.assertEqual(
            household["population_alignment_status"],
            "BLOCKED_NO_OBSERVED_OFFICIAL_BRIDGE_IDENTIFIED",
        )
        self.assertFalse(
            household["housing_dsti_directly_admissible_in_registered_aggregate_consumption_form"]
        )
        self.assertEqual(
            household["borrower_burden_population_alignment_review"],
            "model/calibration_validation/household_consumption_borrower_burden_alignment_review.json",
        )
        self.assertEqual(
            household["population_bridge_source_screening"],
            "model/calibration_validation/household_consumption_population_bridge_source_screening.json",
        )
        self.assertFalse(household["official_population_bridge_found"])
        self.assertFalse(household["estimation_or_refit_allowed"])
        credit_risk = mechanisms["credit_risk_npl_response"]
        self.assertEqual(
            credit_risk["source_readiness"],
            "AGGREGATE_NPL_EXACT_MORTGAGE_PORTFOLIO_FAMILY_OBSERVED_JOINT_BOUNDARY_AND_ACTIVITY_UNRESOLVED",
        )
        self.assertEqual(
            credit_risk["priority_group"],
            "DEFER_UNTIL_MATCHED_AGGREGATE_OR_MORTGAGE_PORTFOLIO_SOURCE",
        )
        self.assertEqual(
            credit_risk["mortgage_portfolio_source_screening"],
            "model/calibration_validation/credit_risk_mortgage_portfolio_source_screening.json",
        )
        self.assertTrue(credit_risk["mortgage_npl_publication_observed"])
        self.assertFalse(
            credit_risk["mortgage_npl_exact_machine_readable_history_retained"]
        )
        self.assertFalse(credit_risk["mortgage_target_selected"])
        self.assertFalse(credit_risk["dti_o_debt_service_substitution_allowed"])
        self.assertFalse(credit_risk["estimation_or_refit_allowed"])

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
            "DEFER_UNTIL_EXPECTATIONS_GAP_VINTAGE_IDENTIFICATION_CONTRACT",
        )
        self.assertEqual(
            mechanisms["external_fx_refinancing_feedback"][
                "priority_group"
            ],
            "DEFER_UNTIL_JOINT_EXPOSURE_SOURCE",
        )


if __name__ == "__main__":
    unittest.main()
