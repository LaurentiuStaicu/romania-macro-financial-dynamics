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
            ".github/workflows/provenance-audit.yml",
            ".github/workflows/f4-exact-complement-rank-audit.yml",
            ".github/workflows/f5-equity-subcomponent-bridge-audit.yml",
            ".github/workflows/f7-financial-derivatives-coverage-audit.yml",
            ".github/workflows/f8-other-accounts-coverage-audit.yml",
            ".github/workflows/sectoral-financial-positions-reference-audit.yml",
            ".github/workflows/sectoral-financial-positions-aggregate-identity-audit.yml",
            ".github/workflows/sectoral-financial-positions-rounding-consistency-audit.yml",
            ".github/workflows/sectoral-financial-positions-source-discrepancy-audit.yml",
            ".github/workflows/sectoral-financial-positions-esa-f1-applicability-reaudit.yml",
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


    def test_sectoral_position_has_no_parallel_phase_aliases(self) -> None:
        forbidden_paths = [
            ".github/workflows/sectoral-financial-positions-phase-b-audit.yml",
            "scripts/audit_ecb_sectoral_financial_positions_phase_b.py",
            "model/dynamics/sectoral_financial_positions_phase_b_assessment.json",
            ".github/workflows/sectoral-financial-positions-phase-c-diagnostic.yml",
            "scripts/audit_ecb_sectoral_financial_positions_phase_c.py",
            "model/dynamics/sectoral_financial_positions_phase_c_diagnostic_contract.json",
            "tests/test_sectoral_financial_positions_phase_c_diagnostic_contract.py",
        ]
        for relative in forbidden_paths:
            self.assertFalse((ROOT / relative).exists(), relative)

        registry = (
            ROOT / "model" / "dynamics" / "reference_modes.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"phase_b_assessment"', registry)
        self.assertIn(
            '"historical_phase_b_assessment": '
            '"model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"',
            registry,
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
            "audit_ecb_sectoral_financial_positions_reference.py",
            "audit_ecb_sectoral_financial_positions_aggregate_identity.py",
            "audit_ecb_sectoral_financial_positions_rounding_consistency.py",
            "audit_ecb_sectoral_financial_positions_source_discrepancy.py",
            "audit_ecb_sectoral_financial_positions_esa_f1_applicability_reaudit.py",
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
