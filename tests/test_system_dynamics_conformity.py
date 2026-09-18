from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
