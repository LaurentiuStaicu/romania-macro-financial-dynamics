from __future__ import annotations

import csv
import json
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class RemainingReferenceModeBlockerTests(unittest.TestCase):
    def test_refinancing_need_remains_partial_without_semantic_substitution(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        assessment = load(
            "model/dynamics/government_refinancing_need_reference_assessment.json"
        )
        mechanisms = load("model/empirical_dynamics/mechanism_registry.json")

        mode = next(
            item for item in references["modes"]
            if item["id"] == "government_refinancing_need"
        )
        mechanism = next(
            item for item in mechanisms["mechanisms"]
            if item["id"] == "government_refinancing_effective_rate"
        )

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            assessment["verdict"],
            "REMAINS_PARTIAL_SERIES_AVAILABLE",
        )
        self.assertTrue(
            assessment["blocker"]["blocker_is_short_mixed_vintage_reference_history"]
        )
        self.assertEqual(
            assessment["observed_partial_series"]["observation_count"],
            7,
        )
        self.assertEqual(
            assessment["observed_partial_series"]["forecast_observations"],
            0,
        )
        self.assertIn(
            "treat gross financing need as realized principal refinanced",
            assessment["prohibited_shortcuts"],
        )
        self.assertEqual(mechanism["classification"], "DEFERRED")
        self.assertFalse(mechanism["central_feedback"])

    def test_partial_refinancing_series_preserves_observation_status(self) -> None:
        series_path = (
            ROOT
            / "data"
            / "processed"
            / "government_debt_refinancing_mof_2017_2023.csv"
        )
        with series_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual([row["period"] for row in rows], [str(y) for y in range(2017, 2024)])
        self.assertEqual(len(rows), 7)
        self.assertTrue(
            all(
                math.isfinite(float(row["government_debt_refinancing_bn_ron"]))
                and math.isfinite(float(row["gross_financing_need_bn_ron"]))
                for row in rows
            )
        )
        statuses = [row["observation_status"] for row in rows]
        self.assertEqual(statuses.count("FINAL_ANNUAL_REPORT"), 4)
        self.assertEqual(statuses.count("OPERATIVE_EXECUTION"), 3)
        self.assertNotIn("FORECAST", statuses)

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
        expected = accounting["current_expected_state"]

        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            assessment["verdict"],
            "BLOCKED_BY_CANONICAL_ACCOUNTING_READINESS",
        )
        self.assertEqual(
            assessment["current_state"]["canonical_incomplete_instruments"],
            expected["canonical_incomplete_instruments"],
        )
        self.assertFalse(
            expected["canonical_multi_instrument_stock_initialization_ready"]
        )
        self.assertFalse(
            expected["canonical_full_2025_stock_flow_benchmark_ready"]
        )
        self.assertFalse(
            model["dynamic_core"]["canonical_multi_instrument_stock_initialization_ready"]
        )

    def test_status_readiness_summary_is_derived_from_registry(self) -> None:
        references = load("model/dynamics/reference_modes.json")
        model = load("model/registries/model_contract.json")
        status = (ROOT / "STATUS.md").read_text(encoding="utf-8")

        ready_statuses = set(
            references["closure_readiness_policy"][
                "ready_statuses_for_integrated_quantitative_closure"
            ]
        )
        required = int(model["dynamic_core"]["reference_mode_required_count"])
        ready = sum(
            1
            for item in references["modes"]
            if item["id"] in {
                "policy_rate",
                "household_lending_rate",
                "nfc_lending_rate",
                "credit_stock",
                "credit_flow",
                "government_debt_stock",
                "government_interest_burden",
                "government_refinancing_need",
                "government_effective_interest_rate",
                "sectoral_financial_positions",
            }
            and item["status"] in ready_statuses
        )
        blockers = required - ready
        match = re.search(
            r"Canonical reference-mode readiness: \*\*(\d+)/(\d+) observed; "
            r"(\d+) blockers\*\*\.",
            status,
        )
        self.assertIsNotNone(match)
        self.assertEqual(
            tuple(map(int, match.groups())),
            (ready, required, blockers),
        )
        self.assertEqual(
            model["dynamic_core"]["reference_mode_ready_count"],
            ready,
        )


if __name__ == "__main__":
    unittest.main()
