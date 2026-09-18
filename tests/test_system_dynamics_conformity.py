from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from scripts.audit_system_dynamics_conformity import (
    implied_loop_polarity,
    path_is_closed,
    path_is_contiguous,
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


if __name__ == "__main__":
    unittest.main()
