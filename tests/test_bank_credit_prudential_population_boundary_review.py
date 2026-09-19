from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "model" / "calibration_validation" / "bank_credit_prudential_population_boundary_review.json"

class BankCreditPrudentialPopulationBoundaryReviewTests(unittest.TestCase):
    def setUp(self):
        self.review=json.loads(REVIEW.read_text(encoding="utf-8"))

    def test_direct_population_equivalence_is_rejected_on_semantics(self):
        self.assertEqual(self.review["verdict"],"DIRECT_CBD2_TO_BNR_POPULATION_EQUIVALENCE_REJECTED_NEW_MATCHED_SOURCE_REQUIRED")
        eq=self.review["structural_comparison"]["exact_equivalence"]
        for key in ("population_match","control_basis_match","consolidation_perimeter_match","reporting_population_match","direct_series_substitution_allowed","numeric_similarity_can_override_semantics"):
            self.assertFalse(eq[key])

    def test_official_evidence_captures_population_mismatch(self):
        bnr=" ".join(" ".join(x["findings"]) for x in self.review["official_evidence"] if x["institution"]=="National Bank of Romania").lower()
        ecb=" ".join(" ".join(x["findings"]) for x in self.review["official_evidence"] if x["institution"]=="European Central Bank").lower()
        self.assertIn("romanian legal entities",bnr)
        self.assertIn("majority foreign capital",bnr)
        self.assertIn("domestically controlled",ecb)
        self.assertIn("cross-border",ecb)

    def test_bnr_exact_table_path_is_preferred_without_claiming_machine_readable_history(self):
        state=self.review["current_source_disposition"]
        self.assertEqual(state["bnr_table_source_status"],"EXACT_TABULAR_OFFICIAL_SOURCE_FAMILY_IDENTIFIED_MACHINE_READABLE_HISTORY_NOT_RETAINED")
        self.assertFalse(state["machine_readable_bnr_source_identified_in_this_review"])
        self.assertFalse(state["chart_digitisation_required"])
        self.assertIn("source enumeration",state["next_admissible_source_task"].lower())
        action=state["next_admissible_source_task"].lower()
        self.assertIn("extract numeric values",action)
        self.assertIn("until the full year-source map is frozen",action)

    def test_no_model_or_sd_activation_follows(self):
        effect=self.review["modelling_effect"]
        for key in ("estimation_or_refit_authorized","current_aggregate_equation_authorized","structural_selection_authorized","causal_identification_claim_allowed","bank_credit_feedback_activation","system_dynamics_activation","behavioural_closure_change"):
            self.assertFalse(effect[key])

if __name__=="__main__":
    unittest.main()
