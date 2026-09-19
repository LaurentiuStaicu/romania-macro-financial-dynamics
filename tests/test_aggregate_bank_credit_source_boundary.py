from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class AggregateBankCreditSourceBoundaryTests(unittest.TestCase):
    def test_source_review_keeps_calibration_closed(self) -> None:
        review = load(
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json"
        )
        registry = load("model/empirical_dynamics/mechanism_registry.json")
        mechanism = next(
            item for item in registry["mechanisms"]
            if item["id"] == "aggregate_bank_credit_response"
        )

        self.assertEqual(
            review["verdict"],
            "SOURCE_FEASIBILITY_PASS_CALIBRATION_NOT_OPENED_"
            "SECTOR_AND_DEMAND_SUPPLY_BOUNDARY_REQUIRED",
        )
        self.assertFalse(
            review["source_materialisation_gate"]["calibration_cycle_open"]
        )
        self.assertEqual(mechanism["classification"], "CANDIDATE")
        self.assertFalse(mechanism["central_feedback"])
        self.assertEqual(
            mechanism["source_boundary_review"],
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json",
        )

    def test_credit_components_are_already_sector_specific(self) -> None:
        review = load(
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json"
        )
        snapshot = load("model/dynamics/private_credit_reference_snapshot.json")
        keys = snapshot["provenance"]["series_keys"]
        existing = review["existing_rmd_credit_evidence"]

        self.assertEqual(existing["nfc_stock_key"], keys["nfc_stock"])
        self.assertEqual(
            existing["households_npish_stock_key"],
            keys["households_npish_stock"],
        )
        self.assertEqual(existing["nfc_flow_key"], keys["nfc_flow"])
        self.assertEqual(
            existing["households_npish_flow_key"],
            keys["households_npish_flow"],
        )
        self.assertTrue(
            review["scientific_boundary_decisions"][
                "preserve_sector_specific_credit_components"
            ]
        )

    def test_demand_supply_and_prudential_states_cannot_be_conflated(self) -> None:
        review = load(
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json"
        )
        decisions = review["scientific_boundary_decisions"]
        prohibited = " ".join(
            review["source_materialisation_gate"]["prohibited_shortcuts"]
        ).lower()

        self.assertTrue(decisions["aggregate_single_equation_not_yet_eligible_for_calibration"])
        self.assertTrue(
            decisions["do_not_synthetically_aggregate_BLS_NFC_and_household_signals"]
        )
        self.assertIn("not automatically a causal instrument", decisions["BLS_credit_standards_role"])
        self.assertIn("keep separate", decisions["BLS_loan_demand_role"])
        self.assertIn("not an exogenous", decisions["NPL_role"])
        self.assertIn("not an exogenous", decisions["total_capital_ratio_role"])
        self.assertIn("credit growth alone", prohibited)
        self.assertIn("clean exogenous bank-supply instrument", prohibited)
        self.assertIn("digitise", prohibited)

    def test_exact_bls_spreadsheets_are_catalogued_without_claiming_history(self) -> None:
        review = load(
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json"
        )
        catalog = review["bls_machine_readable_source_catalog"]
        self.assertEqual(
            catalog["status"],
            "CANONICAL_11_OF_12_EXACT_REALIZED_ROUNDS_RETAINED_SINGLE_GAP_2025_Q2",
        )
        self.assertTrue(catalog["historical_coverage_claimed"])
        self.assertFalse(catalog["historical_coverage_complete"])
        self.assertEqual(catalog["canonical_observed_round_count"], 11)
        self.assertEqual(catalog["canonical_expected_round_count"], 12)
        self.assertEqual(catalog["canonical_missing_rounds"], ["2025-Q2"])
        self.assertGreaterEqual(len(catalog["files"]), 6)
        retained_legacy = 0
        xlsx_candidates = 0
        for item in catalog["files"]:
            self.assertTrue(
                item["url"].endswith(".xls")
                or item["url"].endswith(".xlsx")
            )
            if item["format"] == "xls":
                self.assertFalse(item["content_not_materialised"])
                self.assertEqual(
                    item["value_extraction_status"],
                    "NOT_CANONICAL_LEGACY_XLS",
                )
                retained_legacy += 1
            else:
                self.assertTrue(item["content_not_materialised"])
                self.assertEqual(
                    item["value_extraction_status"],
                    "NEXT_XLSX_BRIDGE_CANDIDATE",
                )
                xlsx_candidates += 1
        self.assertGreaterEqual(retained_legacy, 5)
        self.assertGreaterEqual(xlsx_candidates, 1)
        self.assertIn(
            "access-path limitation",
            catalog["provider_access_observation"],
        )
        self.assertIn(
            "only one survey round",
            catalog["may_2025_xlsx_bridge"]["interpretation"],
        )

    def test_prudential_machine_readable_candidates_do_not_change_variables_post_hoc(self) -> None:
        review = load(
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json"
        )
        screen = review["external_prudential_source_screening"]
        sources = screen["sources"]

        self.assertEqual(
            sources["cet1_quarterly_domestic_banks"]["series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.A.I4008._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertIn(
            "not the same variable",
            sources["cet1_quarterly_domestic_banks"]["semantic_limit"],
        )
        self.assertEqual(
            sources["npl_annual_broad_boundary"]["series_key"],
            "CBD2.A.RO.W0.67._Z._Z.A.F.I3632._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertEqual(
            sources["npl_quarterly_domestic_banks"]["series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.F.I3632._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertEqual(
            sources["cbd2_quarterly_npl_family"]["status"],
            "EXACT_ROMANIA_QUARTERLY_SERIES_CONFIRMED",
        )
        self.assertEqual(
            sources["solvency_ratio_candidate"]["series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.A.I4001._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertEqual(
            sources["solvency_ratio_candidate"]["status"],
            "EXACT_ROMANIA_QUARTERLY_SERIES_CONFIRMED_AND_RETAINED",
        )
        self.assertEqual(
            sources["solvency_ratio_candidate"]["retained_vintage"],
            "data/source_vintages/bank-credit-prudential-coverage-vintage-2026-09-19",
        )
        self.assertIn(
            "not numerically identical",
            sources["solvency_ratio_candidate"]["semantic_limit"],
        )
        self.assertIn(
            "Annual frequency",
            sources["npl_annual_broad_boundary"]["semantic_limit"],
        )
        rules = " ".join(screen["decision_rules"]).lower()
        self.assertIn("do not choose cet1 versus total capital ratio", rules)
        self.assertIn("do not forward-fill", rules)
        self.assertEqual(
            screen["calibration_effect"],
            "NONE_DIRECT_SUBSTITUTION_REJECTED",
        )
        self.assertFalse(
            screen["population_boundary_decision"]["direct_cbd2_to_bnr_equivalence"]
        )
        self.assertFalse(
            screen["population_boundary_decision"]["numeric_similarity_can_bridge"]
        )
        self.assertEqual(
            review["prudential_population_boundary_review"],
            "model/calibration_validation/bank_credit_prudential_population_boundary_review.json",
        )
        self.assertEqual(
            review["bnr_prudential_table_source_enumeration"],
            "model/calibration_validation/bnr_prudential_table_source_enumeration.json",
        )
        self.assertEqual(
            screen["source_enumeration_status"],
            "INCOMPLETE_SOURCE_ENUMERATION_NO_MODEL_EFFECT",
        )
        self.assertEqual(
            screen["exact_primary_years_identified"],
            [2019, 2022, 2024],
        )

    def test_no_system_dynamics_activation_follows_from_source_feasibility(self) -> None:
        review = load(
            "model/calibration_validation/"
            "aggregate_bank_credit_source_boundary_review.json"
        )
        feedback = load("model/dynamics/feedback_registry.json")
        model = load("model/registries/model_contract.json")
        loop = next(
            item for item in feedback["loops"]
            if item["id"] == "bank_credit_balance_sheet_loop"
        )

        self.assertFalse(loop["quantitatively_active"])
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])
        self.assertEqual(
            review["disposition"]["validated_reference_behavioural_mechanisms_change"],
            0,
        )
        self.assertFalse(review["disposition"]["central_feedback"])


if __name__ == "__main__":
    unittest.main()
