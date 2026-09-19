from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class ReferenceModeBlockerAssessmentTests(unittest.TestCase):
    def test_every_current_blocker_has_an_explicit_assessment(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        blockers = {
            item["id"]: item
            for item in references["modes"]
            if item["status"] != "OBSERVED_SERIES_AVAILABLE"
        }
        self.assertEqual(
            set(blockers),
            {"government_refinancing_need", "sectoral_financial_positions"},
        )
        for mode_id, mode in blockers.items():
            self.assertIn("assessment", mode, mode_id)
            self.assertTrue((ROOT / mode["assessment"]).is_file(), mode_id)

    def test_refinancing_need_stays_partial_without_concept_substitution(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/government_refinancing_need_reference_assessment.json"
        )
        mode = next(
            item for item in references["modes"]
            if item["id"] == "government_refinancing_need"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            assessment["verdict"],
            "REMAINS_PARTIAL_SERIES_AVAILABLE",
        )
        self.assertEqual(
            assessment["disposition"]["status"],
            "PARTIAL_SERIES_AVAILABLE",
        )
        self.assertEqual(assessment["disposition"]["readiness_count_change"], 0)
        self.assertTrue(
            assessment["blocker"]["blocker_is_definition_and_vintage_consistency"]
        )
        prohibited = " ".join(assessment["prohibited_shortcuts"]).lower()
        self.assertIn("gross financing need", prohibited)
        self.assertIn("repricing", prohibited)
        self.assertEqual(
            assessment["disposition"][
                "government_refinancing_effective_rate_mechanism"
            ],
            "UNCHANGED_DEFERRED",
        )

    def test_sectoral_positions_cannot_outrun_accounting_readiness(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/sectoral_financial_positions_reference_assessment.json"
        )
        accounting = load("model/accounting/accounting_readiness_gate.json")
        model = load("model/registries/model_contract.json")
        mode = next(
            item for item in references["modes"]
            if item["id"] == "sectoral_financial_positions"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            assessment["verdict"],
            "BLOCKED_BY_CANONICAL_ACCOUNTING_READINESS",
        )
        self.assertEqual(
            assessment["disposition"]["status"],
            "PARTIAL_SERIES_AVAILABLE",
        )
        self.assertFalse(
            accounting["current_expected_state"][
                "canonical_multi_instrument_stock_initialization_ready"
            ]
        )
        self.assertFalse(
            accounting["current_expected_state"][
                "canonical_full_2025_stock_flow_benchmark_ready"
            ]
        )
        self.assertFalse(
            model["dynamic_core"][
                "canonical_multi_instrument_stock_initialization_ready"
            ]
        )
        self.assertFalse(
            model["dynamic_core"]["canonical_full_2025_stock_flow_benchmark_ready"]
        )
        self.assertEqual(
            assessment["current_state"]["canonical_complete_stock_and_flow_instruments"],
            ["F3"],
        )
        self.assertEqual(
            set(assessment["current_state"]["canonical_incomplete_instruments"]),
            {"F2", "F4", "F5", "F6", "F7", "F8"},
        )

    def test_eight_of_ten_is_a_ceiling_at_current_evidence_boundary(self) -> None:
        model = load("model/registries/model_contract.json")
        self.assertEqual(model["dynamic_core"]["reference_mode_ready_count"], 8)
        self.assertEqual(model["dynamic_core"]["reference_mode_required_count"], 10)
        self.assertFalse(model["dynamic_core"]["reference_mode_closure_ready"])
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])


if __name__ == "__main__":
    unittest.main()
