from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class GovernmentDebtStockReferenceAssessmentTests(unittest.TestCase):
    def test_retained_snapshot_matches_assessment_and_reference_registry(self) -> None:
        assessment = load(
            "model/dynamics/government_debt_stock_reference_assessment.json"
        )
        snapshot = load(
            "model/dynamics/government_debt_stock_reference_snapshot.json"
        )
        references = load("model/dynamics/reference_modes.json")

        self.assertEqual(
            assessment["verdict"],
            "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE",
        )
        self.assertEqual(
            assessment["source_basis"]["workflow_artifact_sha256"],
            snapshot["provenance"]["workflow_artifact_sha256"],
        )

        for unit in ("MIO_NAC", "PC_GDP"):
            observations = snapshot["series"][unit]["observations"]
            self.assertEqual(len(observations), 105)
            self.assertEqual(
                assessment["coverage"][unit]["observations"],
                len(observations),
            )
            for period, value in assessment["benchmark_2025"][unit].items():
                self.assertEqual(observations[period], value)

        mode = next(
            item
            for item in references["modes"]
            if item["id"] == "government_debt_stock"
        )
        self.assertEqual(mode["status"], "OBSERVED_SERIES_AVAILABLE")
        self.assertEqual(mode["time_resolution"], "quarterly")
        self.assertEqual(
            mode["assessment"],
            "model/dynamics/government_debt_stock_reference_assessment.json",
        )
        self.assertEqual(
            mode["retained_snapshot"],
            "model/dynamics/government_debt_stock_reference_snapshot.json",
        )

    def test_promotion_does_not_complete_accounting_or_behaviour(self) -> None:
        assessment = load(
            "model/dynamics/government_debt_stock_reference_assessment.json"
        )
        snapshot = load(
            "model/dynamics/government_debt_stock_reference_snapshot.json"
        )
        model = load("model/registries/model_contract.json")

        self.assertEqual(
            assessment["disposition"]["accounting_spine"],
            "UNCHANGED_INCOMPLETE_MULTI_INSTRUMENT",
        )
        self.assertFalse(snapshot["hard_boundary"]["accounting_spine_changed"])
        self.assertFalse(
            snapshot["hard_boundary"][
                "financial_accounts_total_liabilities_substitution"
            ]
        )
        self.assertFalse(model["dynamic_core"]["behavioural_closure_active"])
        self.assertFalse(
            model["dynamic_core"][
                "canonical_multi_instrument_stock_initialization_ready"
            ]
        )
        self.assertEqual(
            model["dynamic_core"]["reference_mode_ready_count"],
            5,
        )


if __name__ == "__main__":
    unittest.main()
