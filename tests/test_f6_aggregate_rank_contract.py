from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class F6AggregateRankContractTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((ROOT/"model"/"accounting"/"f6_aggregate_rank_contract.json").read_text(encoding="utf-8"))
    def test_system_size(self):
        self.assertEqual(self.c["variables_per_measure"],35); self.assertEqual(self.c["equations_per_measure"],12)
    def test_exact_unconditional_rank(self):
        r=self.c["hard_rules"]; self.assertTrue(r["exact_rational_coefficient_rank"]); self.assertTrue(r["unique_cell_requires_zero_loading_on_every_nullspace_basis_vector"])
    def test_no_structural_shortcuts(self):
        r=self.c["hard_rules"]; self.assertTrue(r["no_issuer_applicability_zero_in_unconditional_system"]); self.assertTrue(r["no_nonnegativity_inference_in_unconditional_system"]); self.assertTrue(r["zero_aggregate_flow_must_not_create_bilateral_zero_equations"])
    def test_no_materialization_or_behavioural_change(self):
        r=self.c["hard_rules"]; self.assertTrue(r["no_materialization_in_phase_C"]); self.assertFalse(r["behavioural_closure_may_change"])
if __name__=="__main__": unittest.main()
