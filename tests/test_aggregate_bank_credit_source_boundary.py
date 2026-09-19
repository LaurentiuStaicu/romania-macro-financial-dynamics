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
            "DIRECT_OFFICIAL_SPREADSHEETS_IDENTIFIED_"
            "PROVIDER_ACCESS_BLOCKED_IN_CURRENT_ENVIRONMENT",
        )
        self.assertFalse(catalog["historical_coverage_claimed"])
        self.assertGreaterEqual(len(catalog["files"]), 6)
        for item in catalog["files"]:
            self.assertTrue(item["content_not_materialised"])
            self.assertTrue(
                item["url"].endswith(".xls")
                or item["url"].endswith(".xlsx")
            )
        self.assertIn(
            "not evidence of missing files",
            catalog["provider_access_observation"],
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
