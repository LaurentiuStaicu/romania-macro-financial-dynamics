from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.validation_recovery import (
    fit_delta_policy,
    persistence_prediction,
    predict_delta_policy,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "validation_recovery"


def read_series(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8") as handle:
        return {
            row["period"]: float(row["value_pct"])
            for row in csv.DictReader(handle)
        }


class ValidationRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.split = json.loads(
            (ROOT / "data" / "provenance" / "validation_recovery_split.json").read_text(
                encoding="utf-8"
            )
        )
        self.policy = read_series(DATA / "policy_rate_bis_monthly.csv")
        self.household = read_series(DATA / "household_housing_mir_monthly.csv")

    def test_household_holdout_has_zero_policy_rate_changes(self) -> None:
        start = self.split["roles"]["final_evaluation_holdout"]["start"]
        end = self.split["roles"]["final_evaluation_holdout"]["end"]
        periods = sorted(set(self.policy) & set(self.household))
        holdout = [
            i for i, period in enumerate(periods)
            if start <= period <= end
        ]
        policy = [self.policy[p] for p in periods]
        self.assertEqual(
            sum(
                1
                for i in holdout
                if abs(policy[i] - policy[i - 1]) > 1e-12
            ),
            0,
        )

    def test_household_candidate_equals_persistence_on_holdout(self) -> None:
        selection_end = self.split["roles"]["structural_selection"]["end"]
        holdout_start = self.split["roles"]["final_evaluation_holdout"]["start"]
        holdout_end = self.split["roles"]["final_evaluation_holdout"]["end"]

        periods = sorted(
            p
            for p in set(self.policy) & set(self.household)
            if p <= holdout_end
        )
        policy = [self.policy[p] for p in periods]
        lending = [self.household[p] for p in periods]

        training = [
            i for i, period in enumerate(periods)
            if period <= selection_end
        ]
        transitions = [i for i in training if i >= 1]
        holdout = [
            i for i, period in enumerate(periods)
            if holdout_start <= period <= holdout_end
        ]

        fit = fit_delta_policy(lending, policy, transitions, lag=0)
        for i in holdout:
            self.assertEqual(
                predict_delta_policy(lending, policy, i, fit, lag=0),
                persistence_prediction(lending, i),
            )

    def test_nfc_holdout_remains_unopened_after_selection_failure(self) -> None:
        selection = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "validation_recovery_selection.json"
            ).read_text(encoding="utf-8")
        )
        freeze = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "validation_recovery_selection_freeze.json"
            ).read_text(encoding="utf-8")
        )
        candidate_results = selection["targets"]["nfc_upto1y"]["candidate_results"]
        self.assertEqual(
            set(candidate_results),
            {
                "delta_policy_contemporaneous",
                "delta_policy_lag1",
                "anchored_partial_adjustment",
                "static_affine_policy_level",
            },
        )
        self.assertTrue(
            all(
                not result["passes_all_selection_gates"]
                for result in candidate_results.values()
            )
        )
        self.assertFalse(
            freeze["targets"]["nfc_upto1y"]["final_holdout_may_be_opened"]
        )

    def test_prospective_confirmation_starts_2026_08(self) -> None:
        self.assertEqual(
            self.split["roles"]["future_confirmation_holdout"]["start"],
            "2026-08",
        )

    def test_no_validated_reference_behavioural_mechanism(self) -> None:
        disposition = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "validation_recovery_disposition.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            disposition["validated_reference_behavioural_mechanisms"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
