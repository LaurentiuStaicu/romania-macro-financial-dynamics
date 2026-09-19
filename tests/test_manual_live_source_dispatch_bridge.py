from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scientific-ci.yml"
AUDIT_BRANCH = "audit/scientific-integrity-2026-09-18"


class ManualLiveSourceDispatchBridgeTests(unittest.TestCase):
    def test_scientific_ci_remains_dispatchable_and_hosts_manual_live_jobs(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("manual-eurostat-counterpart-probe:", text)
        self.assertIn("manual-oecd-counterpart-probe:", text)
        guard = (
            "github.event_name == 'workflow_dispatch' && "
            f"github.ref_name == '{AUDIT_BRANCH}'"
        )
        self.assertGreaterEqual(text.count(guard), 2)
        self.assertIn(
            "scripts/audit_eurostat_sectoral_financial_positions_counterpart_probe.py",
            text,
        )
        self.assertIn(
            "scripts/audit_oecd_sectoral_financial_positions_counterpart_probe.py",
            text,
        )

    def test_probe_contracts_point_to_same_manual_dispatch_bridge(self) -> None:
        for relative, expected_job in [
            (
                "model/dynamics/"
                "sectoral_financial_positions_eurostat_counterpart_probe_contract.json",
                "manual-eurostat-counterpart-probe",
            ),
            (
                "model/dynamics/"
                "sectoral_financial_positions_oecd_counterpart_probe_contract.json",
                "manual-oecd-counterpart-probe",
            ),
        ]:
            contract = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            policy = contract["execution_policy"]
            bridge = policy["manual_dispatch_bridge"]
            self.assertEqual(
                policy["current_execution_state"],
                "READY_FOR_MANUAL_DISPATCH_VIA_EXISTING_DEFAULT_BRANCH_WORKFLOW",
            )
            self.assertEqual(
                bridge["workflow"],
                ".github/workflows/scientific-ci.yml",
            )
            self.assertTrue(bridge["workflow_exists_on_default_branch"])
            self.assertEqual(bridge["dispatch_ref"], AUDIT_BRANCH)
            self.assertEqual(bridge["branch_job"], expected_job)
            self.assertFalse(
                bridge["automatic_pull_request_or_push_execution"]
            )
            self.assertIn("workflow_dispatch", bridge["activation_condition"])
            self.assertIn(AUDIT_BRANCH, bridge["activation_condition"])


if __name__ == "__main__":
    unittest.main()
