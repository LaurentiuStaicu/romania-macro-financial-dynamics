from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class FiscalPrimaryBalanceSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/calibration_validation/"
            "fiscal_primary_balance_source_boundary_review.json"
        )

    def test_fiscal_components_are_observed_but_primary_balance_is_not_mismatched(self) -> None:
        inputs = self.review["observed_fiscal_inputs"]
        self.assertEqual(
            inputs["interest_expenditure"]["na_item"],
            "D41PAY",
        )
        self.assertEqual(
            inputs["net_lending_borrowing"]["example_exact_key"],
            "QSA.Q.Y.RO.W0.S13.S1._Z.B.B9._Z._Z._Z.XDC._T.S.V.N._T",
        )
        boundary = self.review["primary_balance_measurement_boundary"]
        self.assertEqual(
            boundary["current_status"],
            "MATCHED_NSA_PC_GDP_MATERIALISATION_CONTRACT_FROZEN_"
            "MANUAL_LIVE_RUN_PENDING",
        )
        self.assertEqual(
            boundary["materialisation_contract"],
            "model/calibration_validation/"
            "fiscal_primary_balance_materialisation_contract.json",
        )
        contract = load(boundary["materialisation_contract"])
        self.assertFalse(contract["estimation_authorized"])
        self.assertTrue(
            contract["hard_rules"]["live_provider_work_manual_only"]
        )
        self.assertFalse(
            contract["result_effect"]["calibration_cycle_open"]
        )

    def test_output_gap_cannot_be_relabelled_from_growth(self) -> None:
        output = self.review["output_gap_boundary"]
        self.assertEqual(
            output["status"],
            "MODEL_BASED_LATENT_OR_ESTIMATED_VARIABLE_NOT_DIRECTLY_OBSERVED",
        )
        self.assertIn("Do not treat real GDP growth", output["rule"])

    def test_observed_fiscal_data_do_not_authorize_taylor_rule(self) -> None:
        admissibility = self.review["source_admissibility"]
        self.assertFalse(admissibility["registered_full_form_admissible"])
        self.assertFalse(
            admissibility["simple_taylor_style_rule_automatically_authorized"]
        )
        self.assertIn("regime-aware", admissibility["rule"])
        self.assertFalse(
            self.review["disposition"]["estimation_or_refit_allowed"]
        )

    def test_mechanism_remains_deferred(self) -> None:
        registry = load("model/empirical_dynamics/mechanism_registry.json")
        mechanism = next(
            item for item in registry["mechanisms"]
            if item["id"] == "fiscal_primary_balance_reaction"
        )
        self.assertEqual(mechanism["classification"], "DEFERRED")
        self.assertFalse(mechanism["central_feedback"])
        self.assertEqual(
            mechanism["source_boundary_review"],
            "model/calibration_validation/fiscal_primary_balance_source_boundary_review.json",
        )


if __name__ == "__main__":
    unittest.main()
