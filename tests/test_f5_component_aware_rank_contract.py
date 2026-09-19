from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class F5ComponentAwareRankContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f5_component_aware_rank_contract.json"
            ).read_text(encoding="utf-8")
        )
        snapshot_path = (
            ROOT
            / self.contract["inputs"]["retained_rank_topology_snapshot"]
        )
        self.snapshot = json.loads(
            snapshot_path.read_text(encoding="utf-8")
        )
        self.assessment = json.loads(
            (
                ROOT / "model" / "accounting"
                / "f5_component_aware_rank_assessment.json"
            ).read_text(encoding="utf-8")
        )
        self.workflow = (
            ROOT / ".github" / "workflows"
            / "f5-component-aware-rank-audit.yml"
        ).read_text(encoding="utf-8")

    def test_rank_uses_component_variables(self) -> None:
        self.assertEqual(
            self.contract["component_variables"],
            ["F511", "F512", "F519", "F52"],
        )
        self.assertEqual(
            self.contract["expected_variable_count_per_measure"],
            140,
        )

    def test_total_uniqueness_uses_nullspace_linear_form(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["exact_rational_coefficient_rank"])
        self.assertTrue(
            rules[
                "total_F5_unique_only_if_linear_form_annihilates_every_nullspace_basis_vector"
            ]
        )
        self.assertTrue(
            rules[
                "F51_unique_only_if_F511_F512_F519_linear_form_annihilates_every_nullspace_basis_vector"
            ]
        )

    def test_source_and_structural_boundaries(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(
            rules["direct_F511_equations_only_from_phase_C_resolved_cells"]
        )
        self.assertTrue(
            rules[
                "F52_equations_only_from_phase_C_resolved_or_structural_cells"
            ]
        )
        self.assertTrue(rules["F52_structural_scope_must_not_expand"])
        self.assertTrue(
            rules[
                "zero_aggregate_flow_must_not_create_bilateral_zero_equations"
            ]
        )
        self.assertTrue(rules["missing_to_zero_forbidden"])

        topology = self.snapshot["coefficient_topology"]
        self.assertEqual(
            topology["F52"]["structural_nonfund_resident_issuers"],
            ["H", "C", "G", "BNR"],
        )
        self.assertEqual(
            len(topology["direct_equity_component_cells"]["F511"]),
            11,
        )
        self.assertEqual(len(topology["F52"]["direct_cells"]), 7)

    def test_no_materialization_or_behavioural_change(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_materialization_in_phase_D"])
        self.assertFalse(rules["behavioural_closure_may_change"])

    def test_retained_topology_matches_successful_phase_D_artifact(self) -> None:
        provenance = self.snapshot["provenance"]
        self.assertEqual(self.snapshot["instrument"], "F5")
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
            self.assessment["source_reproduction"][
                "phase_C_series_requested"
            ],
        )
        self.assertEqual(
            provenance["series_status_counts"],
            self.assessment["source_reproduction"][
                "phase_C_series_status_counts"
            ],
        )
        self.assertFalse(provenance["network_errors_present"])

    def test_rank_workflow_is_offline_and_refresh_remains_separate(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(
            rules[
                "historical_rank_reproduction_must_not_require_live_network"
            ]
        )
        self.assertNotIn(
            "audit_qsa_f5_equity_subcomponents.py",
            self.workflow,
        )
        self.assertIn(
            "audit_f5_component_aware_rank.py",
            self.workflow,
        )
        self.assertIn("retention-days: 90", self.workflow)
        self.assertTrue(
            self.contract["reproduction_boundary"][
                "live_source_refresh_is_separate"
            ]
        )


if __name__ == "__main__":
    unittest.main()
