from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class FxInflationPassThroughSourceBoundaryTests(unittest.TestCase):
    def test_primary_source_keys_are_frozen_without_opening_calibration(self) -> None:
        review = load(
            "model/calibration_validation/"
            "fx_inflation_pass_through_source_boundary_review.json"
        )
        registry = load("model/empirical_dynamics/mechanism_registry.json")
        mechanism = next(
            item for item in registry["mechanisms"]
            if item["id"] == "exchange_rate_pass_through_to_inflation"
        )

        self.assertEqual(
            review["primary_sources"]["exchange_rate"]["series_key"],
            "EXR.M.RON.EUR.SP00.A",
        )
        self.assertEqual(
            review["primary_sources"]["inflation"]["dataset"],
            "prc_hicp_midx — HICP monthly index",
        )
        self.assertEqual(
            review["primary_sources"]["inflation"]["coicop"],
            "CP00",
        )
        self.assertFalse(
            review["source_materialisation_gate"]["calibration_cycle_open"]
        )
        self.assertEqual(mechanism["classification"], "CANDIDATE")
        self.assertEqual(
            mechanism["source_boundary_review"],
            "model/calibration_validation/"
            "fx_inflation_pass_through_source_boundary_review.json",
        )

    def test_external_price_control_cannot_be_chosen_post_hoc(self) -> None:
        review = load(
            "model/calibration_validation/"
            "fx_inflation_pass_through_source_boundary_review.json"
        )
        screening = load(
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json"
        )
        screen = review["external_price_control_screen"]
        prohibited = " ".join(
            review["source_materialisation_gate"]["prohibited_shortcuts"]
        ).lower()

        self.assertEqual(
            screening["preferred_direct_control"]["status"],
            "ROMANIA_COVERAGE_NOT_CONFIRMED",
        )
        self.assertEqual(
            screen["screening"],
            "model/calibration_validation/"
            "fx_inflation_external_price_control_screening.json",
        )
        self.assertFalse(screen["calibration_may_open"])
        self.assertIn(
            "after inspecting model fit",
            screening["purpose"],
        )
        self.assertIn("euro-area import prices", prohibited)
        self.assertIn("lag length", prohibited)
        self.assertIn("cpi and hicp", prohibited)

    def test_sign_convention_and_no_causal_activation_are_explicit(self) -> None:
        review = load(
            "model/calibration_validation/"
            "fx_inflation_pass_through_source_boundary_review.json"
        )
        self.assertEqual(review["transformation_boundary"]["fx_quote"], "RON_per_EUR")
        self.assertIn(
            "depreciation",
            review["transformation_boundary"][
                "positive_fx_change_interpretation"
            ].lower(),
        )
        self.assertFalse(
            review["scientific_boundaries"][
                "causal_claim_from_distributed_lag_alone"
            ]
        )
        self.assertFalse(review["disposition"]["central_feedback"])
        self.assertEqual(
            review["disposition"]["validated_reference_behavioural_mechanisms_change"],
            0,
        )

    def test_behavioural_closure_remains_inactive(self) -> None:
        model = load("model/registries/model_contract.json")
        review = load(
            "model/calibration_validation/"
            "fx_inflation_pass_through_source_boundary_review.json"
        )
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])
        self.assertEqual(
            review["disposition"]["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
