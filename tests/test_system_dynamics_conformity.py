from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.audit_system_dynamics_conformity import (
    REQUIRED_REFERENCE_MODES,
    implied_loop_polarity,
    path_is_closed,
    path_is_contiguous,
    reference_mode_readiness,
)

ROOT = Path(__file__).resolve().parents[1]


class SystemDynamicsConformityTests(unittest.TestCase):
    def test_conformity_gate_passes(self) -> None:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "audit_system_dynamics_conformity.py"),
            ],
            cwd=ROOT,
            check=True,
        )

    def test_loop_polarity_is_computed_from_signed_path(self) -> None:
        reinforcing = [
            {"from": "a", "to": "b", "sign": "+"},
            {"from": "b", "to": "a", "sign": "+_candidate"},
        ]
        balancing = [
            {"from": "a", "to": "b", "sign": "+"},
            {"from": "b", "to": "c", "sign": "-_candidate"},
            {"from": "c", "to": "a", "sign": "+"},
        ]
        self.assertEqual(implied_loop_polarity(reinforcing), "reinforcing")
        self.assertEqual(implied_loop_polarity(balancing), "balancing")

    def test_open_chain_is_not_a_loop(self) -> None:
        path = [
            {"from": "a", "to": "b", "sign": "+"},
            {"from": "b", "to": "c", "sign": "+"},
        ]
        self.assertTrue(path_is_contiguous(path))
        self.assertFalse(path_is_closed(path))
        with self.assertRaises(RuntimeError):
            implied_loop_polarity(path)


    def test_reference_mode_readiness_is_explicitly_blocked(self) -> None:
        references = json.loads(
            (
                ROOT / "model" / "dynamics" / "reference_modes.json"
            ).read_text(encoding="utf-8")
        )
        readiness = reference_mode_readiness(
            references,
            REQUIRED_REFERENCE_MODES,
        )
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(
            set(readiness["ready_modes"]),
            {
                "policy_rate",
                "household_lending_rate",
                "nfc_lending_rate",
            },
        )
        self.assertEqual(
            set(readiness["blocking_modes"]),
            {
                "credit_stock",
                "credit_flow",
                "government_debt_stock",
                "government_interest_burden",
                "government_refinancing_need",
                "government_effective_interest_rate",
                "sectoral_financial_positions",
            },
        )

    def test_qualitative_reference_exception_requires_explicit_basis(self) -> None:
        references = json.loads(
            (
                ROOT / "model" / "dynamics" / "reference_modes.json"
            ).read_text(encoding="utf-8")
        )
        mutated = copy.deepcopy(references)
        mutated["closure_readiness_policy"][
            "current_qualitative_exceptions"
        ] = [{"id": "credit_stock"}]
        with self.assertRaises(RuntimeError):
            reference_mode_readiness(
                mutated,
                REQUIRED_REFERENCE_MODES,
            )


if __name__ == "__main__":
    unittest.main()
