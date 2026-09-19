from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SovereignYieldSourceBoundaryTests(unittest.TestCase):
    def test_exact_yield_source_is_registered_without_claiming_pure_spread(self) -> None:
        review = load(
            "model/calibration_validation/sovereign_yield_source_boundary_review.json"
        )
        registry = load("model/empirical_dynamics/mechanism_registry.json")
        mechanism = next(
            item for item in registry["mechanisms"]
            if item["id"] == "sovereign_yield_spread_response"
        )
        self.assertEqual(
            review["observed_yield_source"]["romania_series_key"],
            "IRS.M.RO.L.L40.CI.0000.RON.N.Z",
        )
        self.assertFalse(
            review["semantic_boundary"]["pure_sovereign_credit_spread_observed"]
        )
        self.assertIn(
            "cross-currency",
            review["semantic_boundary"]["reason"].lower(),
        )
        self.assertEqual(mechanism["classification"], "CANDIDATE")
        self.assertEqual(
            mechanism["source_boundary_review"],
            "model/calibration_validation/sovereign_yield_source_boundary_review.json",
        )

    def test_benchmark_choice_and_mixed_frequency_are_frozen_before_fit(self) -> None:
        review = load(
            "model/calibration_validation/sovereign_yield_source_boundary_review.json"
        )
        prohibited = " ".join(
            review["source_materialisation_gate"]["prohibited_shortcuts"]
        ).lower()
        self.assertEqual(
            review["benchmark_sources"]["germany_10y"]["series_key"],
            "IRS.M.DE.L.L40.CI.0000.EUR.N.Z",
        )
        self.assertEqual(
            review["benchmark_sources"]["euro_area_10y"]["series_key"],
            "IRS.M.U2.L.L40.CI.0000.EUR.N.Z",
        )
        self.assertIn("germany versus euro-area benchmark", prohibited)
        self.assertIn("forward-fill", prohibited)
        self.assertIn("ciss versus sovciss", prohibited)
        self.assertFalse(
            review["source_materialisation_gate"]["calibration_cycle_open"]
        )

    def test_feedback_loop_remains_quantitatively_inactive(self) -> None:
        review = load(
            "model/calibration_validation/sovereign_yield_source_boundary_review.json"
        )
        feedback = load("model/dynamics/feedback_registry.json")
        model = load("model/registries/model_contract.json")
        loop = next(
            item for item in feedback["loops"]
            if item["id"] == "government_issuance_yield_loop"
        )
        self.assertFalse(loop["quantitatively_active"])
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])
        self.assertFalse(review["disposition"]["central_feedback"])
        self.assertEqual(
            review["disposition"]["validated_reference_behavioural_mechanisms_change"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
