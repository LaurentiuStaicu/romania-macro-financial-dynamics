from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "calibration_validation"
            / "fiscal_reaction_annual_structural_selection_contract.json"
        ).read_text(encoding="utf-8")
    )


class FiscalReactionAnnualStructuralSelectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load()

    def test_contract_does_not_authorize_estimation_or_activation(self) -> None:
        self.assertFalse(
            self.contract["estimation_authorization"]["authorized_by_this_contract"]
        )
        hard = self.contract["hard_rules"]
        self.assertTrue(hard["no_holdout_peeking_before_selection_pass"])
        self.assertTrue(hard["no_causal_fiscal_claim"])
        self.assertTrue(hard["no_debt_sustainability_claim_from_coefficient"])
        self.assertTrue(hard["no_system_dynamics_activation"])
        self.assertTrue(hard["no_behavioural_closure_change"])

    def test_exact_retained_actual_only_source_is_required(self) -> None:
        source = self.contract["prerequisite_source_vintage"]
        self.assertEqual(source["rows"], 30)
        self.assertEqual(source["first_year"], 1995)
        self.assertEqual(source["last_year"], 2024)
        self.assertEqual(
            source["normalized_csv_sha256"],
            "4d6ab4c737ffb50d48d4866539e6f069b03bc90945bc7a645ac4bd7f88ef2193",
        )
        self.assertTrue(source["exact_raw_reproducibility_required"])
        self.assertFalse(
            self.contract["measurement_boundary"]["forecast_years_allowed"]
        )

    def test_candidate_is_parsimonious_and_uses_only_lagged_states(self) -> None:
        candidate = self.contract["candidate_models"][0]
        self.assertEqual(candidate["estimated_parameters"], 4)
        timing = self.contract["information_timing"]
        self.assertEqual(timing["all_candidate_predictors"], "t-1 only")
        self.assertTrue(timing["no_same_year_output_gap"])
        self.assertTrue(timing["no_same_year_debt"])
        self.assertTrue(timing["no_future_leakage"])

    def test_windows_keep_final_evaluation_locked(self) -> None:
        windows = self.contract["windows"]
        self.assertEqual(windows["initial_calibration"], "1996..2009")
        self.assertEqual(windows["structural_selection"], "2010..2017")
        self.assertEqual(windows["final_evaluation"], "2018..2024")
        self.assertIn(
            "only if",
            windows["final_evaluation_open_rule"].lower(),
        )

    def test_candidate_must_beat_estimated_ar_baseline(self) -> None:
        gates = self.contract["structural_selection_gates"]
        self.assertGreater(
            gates[
                "candidate_rmse_improvement_vs_primary_balance_ar_fraction_min"
            ],
            0,
        )
        self.assertTrue(gates["all_parameter_domains_must_pass"])
        self.assertTrue(self.contract["hard_rules"]["no_regime_coefficients"])
        self.assertTrue(
            self.contract["hard_rules"]["no_debt_gap_60pct_substitution"]
        )


if __name__ == "__main__":
    unittest.main()
