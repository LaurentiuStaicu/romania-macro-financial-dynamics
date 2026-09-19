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
            "NOT_AVAILABLE_FOR_ROMANIA",
        )
        self.assertIn(
            "NOT_A_PARTICIPATING_COUNTRY",
            hfcs["romania_status"],
        )

    def test_abf_public_aggregates_do_not_supply_mortgage_borrower_bridge(self) -> None:
        sources = {item["id"]: item for item in self.review["screened_sources"]}
        abf = sources["INS_ABF_TEMPO"]
        self.assertTrue(abf["evidence"]["quarterly_frequency_available"])
        self.assertTrue(abf["evidence"]["household_consumption_observed"])
        self.assertFalse(
            abf["mortgage_borrower_status_public_breakdown_identified"]
        )
        self.assertFalse(abf["common_dsti_consumption_microdata_link_identified"])

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
            "BLOCKED_NO_OBSERVED_PUBLIC_BRIDGE_IDENTIFIED",
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
