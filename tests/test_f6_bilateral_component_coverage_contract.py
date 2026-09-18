from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class F6BilateralComponentContractTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads((ROOT/"model"/"accounting"/"f6_bilateral_component_coverage_contract.json").read_text(encoding="utf-8"))
    def test_exact_identities(self):
        self.assertIn("F61 + F62 + F63 + F64 + F65 + F66",self.c["exact_identities"]["six_component"])
        self.assertIn("F63_F64_F65",self.c["exact_identities"]["transmission_block"])
    def test_no_synthetic_or_issuer_assumptions(self):
        r=self.c["hard_rules"]; self.assertTrue(r["no_missing_to_zero"]); self.assertTrue(r["no_synthetic_allocation"]); self.assertTrue(r["no_issuer_applicability_assumption"])
    def test_complete_components_required(self):
        r=self.c["hard_rules"]; self.assertTrue(r["six_component_F6_requires_all_six_components"]); self.assertTrue(r["block_F6_requires_F61_F62_F63_F64_F65_block_F66"]); self.assertTrue(r["two_available_F6_derivations_must_agree_within_tolerance"])
    def test_no_materialization_or_behavioural_change(self):
        r=self.c["hard_rules"]; self.assertTrue(r["no_materialization_in_phase_B"]); self.assertFalse(r["behavioural_closure_may_change"])
if __name__=="__main__": unittest.main()
