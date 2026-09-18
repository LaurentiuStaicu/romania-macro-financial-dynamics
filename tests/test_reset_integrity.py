from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ResetIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "registries" / "reset_integrity_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_top_level_repository_scope_matches_explicit_allowlist(self) -> None:
        allowed = set(self.contract["allowed_top_level_paths"])
        actual = {
            path.name
            for path in ROOT.iterdir()
            if path.name != ".git"
            and not path.name.startswith(".pytest_cache")
            and not path.name.startswith("__pycache__")
        }
        unexpected = sorted(actual - allowed)
        self.assertEqual(
            unexpected,
            [],
            msg=f"Unexpected top-level paths require Reset Integrity review: {unexpected}",
        )

    def test_required_scientific_roots_exist(self) -> None:
        for relative in self.contract["required_scientific_roots"]:
            self.assertTrue(
                (ROOT / relative).is_dir(),
                msg=f"Missing required scientific root: {relative}",
            )

    def test_removed_product_and_historical_roots_remain_absent(self) -> None:
        prohibited = (
            self.contract["prohibited_product_roots"]
            + self.contract["prohibited_historical_roots"]
        )
        present = [
            relative
            for relative in prohibited
            if (ROOT / relative).exists()
        ]
        self.assertEqual(
            present,
            [],
            msg=f"Reset-excluded repository roots reappeared: {present}",
        )

    def test_reset_does_not_authorize_evidence_removal(self) -> None:
        rules = self.contract["rules"]
        self.assertTrue(
            rules["scientific_evidence_and_provenance_may_not_be_removed_to_satisfy_reset"]
        )
        self.assertTrue(rules["reset_integrity_does_not_freeze_scientific_development"])


if __name__ == "__main__":
    unittest.main()
