from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LiveSourceRefreshWorkflowTests(unittest.TestCase):
    def test_live_provider_refreshes_are_manual_only(self) -> None:
        manual_only = [
            ".github/workflows/private-credit-reference-audit.yml",
            ".github/workflows/government-interest-burden-reference-audit.yml",
            ".github/workflows/government-debt-stock-reference-audit.yml",
            ".github/workflows/f4-exact-complement-rank-audit.yml",
            ".github/workflows/f5-equity-subcomponent-bridge-audit.yml",
            ".github/workflows/f7-financial-derivatives-coverage-audit.yml",
            ".github/workflows/f8-other-accounts-coverage-audit.yml",
        ]
        for relative in manual_only:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("workflow_dispatch:", text, relative)
            self.assertNotIn("pull_request:", text, relative)
            lowered = text.lower()
            self.assertIn("refresh", lowered, relative)
            self.assertTrue(
                "live" in lowered or "provider" in lowered,
                relative,
            )

    def test_offline_reproduction_workflows_remain_automatic(self) -> None:
        offline_automatic = [
            ".github/workflows/f4-partial-materialization-audit.yml",
            ".github/workflows/f5-component-aware-rank-audit.yml",
            ".github/workflows/f6-aggregate-rank-audit.yml",
            ".github/workflows/f7-aggregate-rank-audit.yml",
            ".github/workflows/f8-aggregate-rank-audit.yml",
        ]
        for relative in offline_automatic:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("pull_request:", text, relative)
            self.assertIn("workflow_dispatch:", text, relative)

    def test_scientific_ci_does_not_call_live_source_audits(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "scientific-ci.yml"
        ).read_text(encoding="utf-8")
        forbidden = [
            "audit_ecb_private_credit_reference.py",
            "audit_eurostat_government_interest_burden_reference.py",
            "audit_eurostat_government_debt_stock_reference.py",
            "audit_qsa_f4_loans_coverage.py",
            "audit_qsa_f5_equity_subcomponents.py",
            "audit_qsa_f7_financial_derivatives_coverage.py",
            "audit_qsa_f8_other_accounts_coverage.py",
        ]
        for script in forbidden:
            self.assertNotIn(script, text)

    def test_offline_reproduction_is_still_covered_by_scientific_ci(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "scientific-ci.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", text)
        self.assertIn("python scripts/audit_accounting_readiness.py", text)
        self.assertIn("python scripts/audit_system_dynamics_conformity.py", text)
        self.assertIn(
            "python scripts/verify_validation_recovery_provenance.py",
            text,
        )


if __name__ == "__main__":
    unittest.main()
