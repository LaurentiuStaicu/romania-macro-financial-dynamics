from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class CreditRiskNplSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/calibration_validation/"
            "credit_risk_npl_source_boundary_review.json"
        )

    def test_exact_quarterly_npl_does_not_open_estimation(self) -> None:
        source = self.review["exact_risk_source"]
        self.assertEqual(
            source["series_key"],
            "CBD2.Q.RO.W0.11._Z._Z.A.F.I3632._Z._Z._Z._Z._Z._Z.PC",
        )
        self.assertEqual(source["status"], "EXACT_SERIES_CONFIRMED")
        self.assertIn("2014-Q4", source["coverage"])
        self.assertFalse(
            self.review["source_admissibility"]["registered_full_form_admissible"]
        )
        self.assertFalse(
            self.review["disposition"]["estimation_or_refit_allowed"]
        )

    def test_loan_stocks_and_transactions_are_not_debt_service(self) -> None:
        boundary = self.review["debt_service_boundary"]
        self.assertEqual(
            boundary["status"],
            "NO_EXACT_RECONCILED_ROMANIA_BORROWER_DEBT_SERVICE_SERIES_RETAINED",
        )
        descriptions = " ".join(
            item["why_not_debt_service"]
            for item in boundary["available_but_non_equivalent_sources"]
            if "why_not_debt_service" in item
        ).lower()
        self.assertIn("do not identify scheduled principal repayments", descriptions)
        self.assertIn(
            "do not synthesize debt service",
            boundary["prohibited_measurement_model"].lower(),
        )

    def test_missing_debt_service_does_not_authorize_nested_model(self) -> None:
        admissibility = self.review["source_admissibility"]
        self.assertFalse(admissibility["reduced_form_automatically_authorized"])
        self.assertIn(
            "new preregistered candidate-family contract",
            admissibility["reduced_form_rule"],
        )
        prohibited = " ".join(self.review["prohibited_shortcuts"]).lower()
        self.assertIn("assume an amortisation schedule", prohibited)
        self.assertIn("loan transactions as principal repayments", prohibited)
        self.assertIn("drop the debt-service term", prohibited)

    def test_mechanism_remains_deferred_and_closure_inactive(self) -> None:
        registry = load("model/empirical_dynamics/mechanism_registry.json")
        mechanism = next(
            item for item in registry["mechanisms"]
            if item["id"] == "credit_risk_npl_response"
        )
        self.assertEqual(mechanism["classification"], "DEFERRED")
        self.assertFalse(mechanism["central_feedback"])
        self.assertEqual(
            mechanism["source_boundary_review"],
            "model/calibration_validation/credit_risk_npl_source_boundary_review.json",
        )
        self.assertEqual(
            self.review["disposition"]["behavioural_closure"],
            "UNCHANGED_INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
