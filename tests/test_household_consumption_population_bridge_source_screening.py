from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "model"
    / "calibration_validation"
    / "household_consumption_population_bridge_source_screening.json"
)


class HouseholdConsumptionPopulationBridgeSourceScreeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = json.loads(P.read_text(encoding="utf-8"))

    def test_hfcs_is_conceptually_relevant_but_not_available_for_romania(self) -> None:
        sources = {item["id"]: item for item in self.review["screened_sources"]}
        hfcs = sources["ECB_HFCS"]
        self.assertEqual(hfcs["conceptual_fit"], "HIGH_IF_ROMANIA_PARTICIPATED")
        self.assertEqual(
            hfcs["bridge_status"],
            "NO_ROMANIA_HFCS_COUNTRY_DATASET_IN_RELEVANT_AVAILABLE_WAVES",
        )
        self.assertIn(
            "HFCN_MEMBER_INSTITUTION",
            hfcs["romania_status"],
        )
        self.assertIn(
            "2023_WAVES_IDENTIFIED",
            hfcs["romania_status"],
        )
        evidence = " ".join(hfcs["participation_evidence"])
        self.assertIn("Banca Națională a României", evidence)
        self.assertIn("fifth wave", evidence)

    def test_abf_public_aggregates_do_not_supply_mortgage_borrower_bridge(self) -> None:
        sources = {item["id"]: item for item in self.review["screened_sources"]}
        abf = sources["INS_ABF_TEMPO"]
        self.assertTrue(abf["evidence"]["quarterly_frequency_available"])
        self.assertTrue(abf["evidence"]["household_consumption_observed"])
        self.assertFalse(
            abf["mortgage_borrower_status_public_breakdown_identified"]
        )
        self.assertFalse(abf["common_dsti_consumption_microdata_link_identified"])

    def test_romania_hbs_microdata_have_consumption_but_no_mortgage_identifier(self) -> None:
        sources = {item["id"]: item for item in self.review["screened_sources"]}
        hbs = sources["EUROSTAT_HBS_2020_SUF"]
        self.assertEqual(hbs["romania_status"], "ROMANIA_2020_SUF_AVAILABLE")
        self.assertTrue(hbs["evidence"]["household_file_contains_consumption_expenditure"])
        self.assertTrue(hbs["evidence"]["household_file_contains_income"])
        self.assertFalse(hbs["mortgage_borrower_status_variable_identified_in_2020_suf_manual"])
        self.assertFalse(hbs["mortgage_or_loan_variable_string_identified_in_2020_suf_manual"])
        self.assertEqual(
            hbs["bridge_status"],
            "ROMANIA_MICRODATA_AVAILABLE_BUT_NO_MORTGAGE_BORROWER_IDENTIFIER_IDENTIFIED",
        )
        self.assertEqual(
            hbs["admissibility"],
            "DO_NOT_USE_OWNER_OCCUPIER_STATUS_AS_MORTGAGE_BORROWER_PROXY",
        )

    def test_no_observed_population_bridge_is_promoted(self) -> None:
        result = self.review["screening_result"]
        self.assertFalse(result["observed_population_bridge_found"])
        self.assertFalse(result["aligned_borrower_consumption_target_found"])
        self.assertFalse(result["aligned_common_microdata_frame_found"])
        self.assertFalse(result["aggregate_burden_source_found"])

    def test_screening_keeps_estimation_and_closure_closed(self) -> None:
        disposition = self.review["disposition"]
        hard = self.review["hard_rules"]
        self.assertEqual(
            disposition["population_bridge_status"],
            "BLOCKED_NO_OBSERVED_OFFICIAL_BRIDGE_IDENTIFIED",
        )
        self.assertFalse(disposition["household_consumption_estimation_authorized"])
        self.assertFalse(disposition["registered_full_form_source_admissible"])
        self.assertTrue(hard["no_synthetic_population_weights"])
        self.assertTrue(hard["no_cross_country_hfcs_transfer"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertEqual(
            disposition["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
