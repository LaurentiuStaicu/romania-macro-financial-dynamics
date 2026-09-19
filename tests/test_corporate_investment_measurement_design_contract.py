from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_measurement_design_contract.json"
)


class CorporateInvestmentMeasurementDesignContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_primary_target_is_sector_specific_investment_rate(self) -> None:
        target = self.c["primary_target"]
        self.assertEqual(target["id"], "nfc_investment_rate")
        self.assertIn("S11", target["series_key"])
        self.assertEqual(
            target["role"],
            "PRIMARY_TARGET_FOR_NEXT_CANDIDATE_FAMILY",
        )
        self.assertEqual(
            self.c["excluded_target_for_this_cycle"]["status"],
            "NOT_SELECTED_FOR_THIS_CYCLE",
        )

    def test_d92_is_not_relabelled_as_eu_funding(self) -> None:
        support = self.c["investment_support_measurement"]
        self.assertEqual(
            support["label"],
            "investment_grants_support_intensity",
        )
        self.assertEqual(support["prohibited_label"], "EU_fund_impulse")
        self.assertIn("D92", support["source_series_key"])

    def test_transformations_are_frozen_without_estimation(self) -> None:
        self.assertEqual(
            self.c["demand_measurement"]["source_series_key"],
            "MNA.Q.Y.RO.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.N",
        )
        self.assertIn(
            "t-4",
            self.c["demand_measurement"]["transformation"],
        )
        self.assertEqual(
            self.c["financing_cost_measurement"]["source_series_key"],
            "MIR.M.RO.B.A2A.F.R.A.2240.RON.N",
        )
        self.assertIn(
            "ARITHMETIC_MEAN",
            self.c["financing_cost_measurement"]["transformation"],
        )
        self.assertIn(
            "NOT_TOTAL_ALL_FIXATIONS_RATE",
            self.c["financing_cost_measurement"]["semantic_boundary"],
        )
        self.assertFalse(
            self.c["financing_cost_measurement"]["prior_source_disposition"][
                "predictive_performance_used"
            ]
        )
        self.assertIn(
            "SUM(D92",
            self.c["investment_support_measurement"]["transformation"],
        )
        boundary = self.c["calibration_boundary"]
        self.assertFalse(boundary["calibration_cycle_open"])
        self.assertFalse(boundary["parameter_estimation_allowed"])
        self.assertFalse(boundary["model_selection_allowed"])
        self.assertFalse(boundary["system_dynamics_activation_allowed"])
        self.assertFalse(boundary["behavioural_closure_change_allowed"])

    def test_lag_selection_is_explicitly_deferred(self) -> None:
        timing = self.c["timing_and_lag_boundary"]
        self.assertFalse(timing["lag_structure_selected"])
        self.assertFalse(timing["lag_search_allowed"])
        self.assertEqual(
            self.c["next_gate"]["action"],
            "REBUILD_OFFLINE_MEASUREMENT_PANEL_WITH_RETAINED_UP_TO_ONE_YEAR_RATE_SOURCE",
        )


if __name__ == "__main__":
    unittest.main()
