from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F2MExternalIdentityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f2m_external_identity_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_audit_does_not_mutate_benchmark(self) -> None:
        self.assertTrue(self.contract["no_benchmark_mutation"])

    def test_direct_w2_is_not_required_when_unpublished(self) -> None:
        gates = " ".join(self.contract["required_gates"])
        self.assertIn("W0 minus W1", gates)
        self.assertIn("directly published W2 aggregate", gates)

    def test_external_control_is_independent(self) -> None:
        rule = self.contract["control_independence_rule"]
        self.assertIn("without using any holder→X candidate", rule)
        self.assertIn("published independently", rule)

    def test_residual_allocation_remains_prohibited(self) -> None:
        prohibited = " ".join(self.contract["prohibited"])
        self.assertIn("more than one issuer cell is unresolved", prohibited)
        self.assertIn("unavailable direct W2 aggregate as zero", prohibited)

    def test_total_f2_population_remains_prohibited(self) -> None:
        self.assertIn("populating total F2 from F2M", self.contract["prohibited"])


if __name__ == "__main__":
    unittest.main()
