from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F8AggregateRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f8_aggregate_rank_contract.json"
            ).read_text(encoding="utf-8")
        )
        snapshot_path = ROOT / self.contract["inputs"]["retained_rank_source_snapshot"]
        self.snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assessment = json.loads(
            (
                ROOT
                / "model"
                / "accounting"
                / "f8_aggregate_rank_assessment.json"
            ).read_text(encoding="utf-8")
        )
        self.workflow = (
            ROOT / ".github" / "workflows" / "f8-aggregate-rank-audit.yml"
        ).read_text(encoding="utf-8")

    def test_exact_rank_rule(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["rank_and_nullity_must_use_exact_rational_coefficient_arithmetic"])
        self.assertTrue(rules["unique_cell_status_requires_zero_loading_on_every_nullspace_basis_vector"])

    def test_aggregate_equations_do_not_become_allocations(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_unconditional_bilateral_value_from_aggregate_equations_unless_rank_unique"])
        self.assertTrue(rules["no_synthetic_allocation"])
        self.assertTrue(rules["no_materialization_in_phase_C"])
        self.assertTrue(rules["missing_to_zero_forbidden"])

    def test_bnr_scenario_is_stock_only_and_not_promoted(self) -> None:
        scenario = self.contract["stock_BNR_zero_scenario"]
        self.assertEqual(scenario["scope"], "stock only")
        self.assertFalse(scenario["promotion"])
        self.assertTrue(self.contract["hard_rules"]["conditional_BNR_zero_stock_cells_must_not_be_promoted"])
        self.assertTrue(self.contract["hard_rules"]["zero_BNR_aggregate_flow_must_not_create_bilateral_flow_zeros"])

    def test_behavioural_closure_cannot_change(self) -> None:
        self.assertFalse(self.contract["hard_rules"]["behavioural_closure_may_change"])

    def test_retained_snapshot_matches_successful_rank_artifact(self) -> None:
        provenance = self.snapshot["provenance"]
        self.assertEqual(self.snapshot["instrument"], "F8")
        self.assertEqual(
            provenance["workflow_run_id"],
            self.assessment["workflow_run_id"],
        )
        self.assertEqual(
            provenance["workflow_artifact_id"],
            self.assessment["workflow_artifact_id"],
        )
        self.assertEqual(
            provenance["workflow_artifact_sha256"],
            self.assessment["workflow_artifact_sha256"],
        )
        self.assertEqual(
            provenance["series_requested"],
            self.assessment["source_reproduction"]["series_requested"],
        )
        self.assertEqual(
            provenance["series_status_counts"],
            self.assessment["source_reproduction"]["series_status_counts"],
        )
        self.assertFalse(provenance["network_errors_present"])
        self.assertEqual(provenance["bilateral_total_F8_cells_resolved"], 0)

    def test_rank_workflow_is_offline_and_live_refresh_remains_separate(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["historical_rank_reproduction_must_not_require_live_network"])
        self.assertNotIn("audit_qsa_f8_other_accounts_coverage.py", self.workflow)
        self.assertIn("audit_f8_aggregate_rank.py", self.workflow)
        self.assertIn("retention-days: 90", self.workflow)
        self.assertTrue(self.contract["reproduction_boundary"]["live_source_refresh_is_separate"])


if __name__ == "__main__":
    unittest.main()
