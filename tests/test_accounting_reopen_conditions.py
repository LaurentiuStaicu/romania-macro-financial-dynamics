from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class AccountingReopenConditionsTests(unittest.TestCase):
    def test_registry_matches_canonical_incomplete_instruments(self) -> None:
        gate = load("model/accounting/accounting_readiness_gate.json")
        registry = load("model/accounting/reopen_conditions_registry.json")

        incomplete = set(
            gate["current_expected_state"]["canonical_incomplete_instruments"]
        )
        self.assertEqual(
            set(registry["current_incomplete_instruments"]),
            incomplete,
        )
        self.assertEqual(set(registry["instruments"]), incomplete)
        self.assertEqual(
            set(registry["current_complete_instruments"]),
            set(
                gate["current_expected_state"][
                    "canonical_complete_stock_and_flow_instruments"
                ]
            ),
        )
        self.assertNotIn("F3", registry["instruments"])

    def test_every_frozen_boundary_has_existing_evidence_and_reopen_trigger(self) -> None:
        registry = load("model/accounting/reopen_conditions_registry.json")
        for instrument, item in registry["instruments"].items():
            assessment = ROOT / item["governing_assessment"]
            self.assertTrue(assessment.is_file(), instrument)
            self.assertTrue(str(item["frozen_boundary"]).strip(), instrument)
            reopen = item["reopen_when"]
            if isinstance(reopen, list):
                self.assertTrue(reopen, instrument)
                self.assertTrue(all(str(value).strip() for value in reopen), instrument)
            else:
                self.assertTrue(str(reopen).strip(), instrument)
            self.assertTrue(item["evidence_that_does_not_reopen"], instrument)

    def test_registry_forbids_repeated_probe_and_synthetic_completion(self) -> None:
        registry = load("model/accounting/reopen_conditions_registry.json")
        governance = registry["governance"]
        self.assertTrue(
            governance[
                "no_repeated_live_probe_without_reopen_trigger_or_explicit_refresh_purpose"
            ]
        )
        self.assertTrue(
            governance[
                "live_refresh_is_new_vintage_evidence_not_historical_reproduction"
            ]
        )
        self.assertTrue(
            governance["unchanged_source_topology_does_not_reopen_a_frozen_boundary"]
        )
        self.assertTrue(governance["reopen_does_not_imply_materialization"])
        self.assertTrue(
            governance["no_reopen_condition_may_authorize_synthetic_allocation"]
        )
        self.assertTrue(
            governance[
                "behavioural_closure_may_not_override_frozen_accounting_boundaries"
            ]
        )

    def test_accounting_gate_points_to_reopen_registry(self) -> None:
        gate = load("model/accounting/accounting_readiness_gate.json")
        self.assertEqual(
            gate["reopen_conditions_registry"],
            "model/accounting/reopen_conditions_registry.json",
        )


if __name__ == "__main__":
    unittest.main()
