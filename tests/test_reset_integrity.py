from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tracked_paths() -> tuple[Path, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return tuple(
        Path(raw.decode("utf-8"))
        for raw in completed.stdout.split(b"\0")
        if raw
    )


class ResetIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "registries" / "reset_integrity_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.tracked = tracked_paths()

    def test_top_level_repository_scope_matches_explicit_allowlist(self) -> None:
        allowed = set(self.contract["allowed_top_level_paths"])
        actual = {path.parts[0] for path in self.tracked if path.parts}
        unexpected = sorted(actual - allowed)
        self.assertEqual(
            unexpected,
            [],
            msg=(
                "Unexpected tracked top-level paths require Reset Integrity "
                f"review: {unexpected}"
            ),
        )

    def test_required_scientific_roots_have_tracked_content(self) -> None:
        tracked_roots = {path.parts[0] for path in self.tracked if path.parts}
        for relative in self.contract["required_scientific_roots"]:
            self.assertIn(
                relative,
                tracked_roots,
                msg=f"Missing tracked scientific root: {relative}",
            )

    def test_removed_product_and_historical_roots_remain_untracked(self) -> None:
        prohibited = set(
            self.contract["prohibited_product_roots"]
            + self.contract["prohibited_historical_roots"]
        )
        tracked_roots = {path.parts[0] for path in self.tracked if path.parts}
        present = sorted(prohibited & tracked_roots)
        self.assertEqual(
            present,
            [],
            msg=f"Reset-excluded tracked repository roots reappeared: {present}",
        )

    def test_generated_runtime_directories_do_not_count_as_scope_drift(self) -> None:
        tracked_roots = {path.parts[0] for path in self.tracked if path.parts}
        self.assertNotIn("dist", tracked_roots)
        self.assertFalse(
            any(root.endswith("_audit_artifacts") for root in tracked_roots)
        )

    def test_reset_does_not_authorize_evidence_removal(self) -> None:
        rules = self.contract["rules"]
        self.assertTrue(
            rules[
                "scientific_evidence_and_provenance_may_not_be_removed_to_satisfy_reset"
            ]
        )
        self.assertTrue(
            rules["reset_integrity_does_not_freeze_scientific_development"]
        )


if __name__ == "__main__":
    unittest.main()
