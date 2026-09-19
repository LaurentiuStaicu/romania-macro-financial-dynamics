from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model"/"calibration_validation"/"bnr_bls_cross_round_mapping_contract.json"

class BNRBLSCrossRoundMappingContractTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_mapping_is_frozen_to_independently_defined_question_ids(self):
        obs={item["id"]:item for item in self.c["realised_observables"]}
        self.assertEqual(obs["nfc_credit_standards"]["question_id"],"C01")
        self.assertEqual(obs["nfc_credit_standards"]["net_percentage_cell"],"C13")
        self.assertEqual(obs["nfc_loan_demand"]["question_id"],"C05")
        self.assertEqual(obs["nfc_loan_demand"]["net_percentage_cell"],"C235")
        self.assertEqual(obs["household_mortgage_loan_demand"]["question_id"],"P06")
        self.assertEqual(obs["household_mortgage_loan_demand"]["net_percentage_cell"],"C99")
        self.assertEqual(obs["household_consumer_loan_demand"]["question_id"],"P13")
        self.assertEqual(obs["household_consumer_loan_demand"]["net_percentage_cell"],"C303")

    def test_dsti_term_change_is_excluded_from_level_claims(self):
        boundary=self.c["dsti_boundary"]
        self.assertEqual(boundary["legacy_question_ids"],["P0303","P1103"])
        self.assertEqual(boundary["status"],"EXCLUDED_FROM_BORROWER_DSTI_LEVEL_PANEL")
        self.assertTrue(self.c["hard_rules"]["no_dsti_level_claim"])

    def test_missing_rounds_may_not_be_filled(self):
        rule=self.c["completeness_rule"]
        self.assertFalse(rule["infer_missing_round_values"])
        self.assertFalse(rule["interpolation_allowed"])
        self.assertFalse(rule["forward_fill_allowed"])
        self.assertFalse(rule["synthetic_quarter_creation"])

    def test_mapping_authorizes_no_fit_or_aggregation(self):
        hard=self.c["hard_rules"]
        self.assertTrue(hard["no_nfc_household_signal_aggregation"])
        self.assertTrue(hard["no_parameter_estimation"])
        self.assertTrue(hard["no_model_selection"])
        self.assertTrue(hard["no_lag_selection"])
        self.assertTrue(hard["no_holdout_opening"])
        self.assertTrue(hard["no_system_dynamics_activation"])

if __name__=="__main__":
    unittest.main()
