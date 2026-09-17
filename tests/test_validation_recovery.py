import json
from pathlib import Path

import pytest

from romania_macro_financial_dynamics.validation_recovery import (
    RecoveryIdentifiabilityError,
    error_metrics,
    expanding_origin_predictions,
    fit_delta_policy,
    fit_static_affine,
    parameter_domain_fraction,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_recovery_split_is_frozen_before_estimation_and_old_holdout_is_not_independent():
    split = load_json("data/provenance/validation_recovery_split_0.5.1a0.json")
    assert split["frozen_before_estimation"] is True
    assert split["roles"]["final_evaluation_holdout"]["start"] == "2025-02"
    assert split["roles"]["final_evaluation_holdout"]["inspection_status_at_freeze"] == "UNINSPECTED_FOR_VALUES"
    assert "Nov-2024..Jan-2025" in split["old_holdout_rule"]
    assert split["roles"]["future_confirmation_holdout"]["start"] == "2026-08"


def test_recovery_contract_is_parsimonious_and_keeps_simulator_gated():
    contract = load_json("model/calibration_validation/validation_recovery_contract.json")
    assert all(contract["hard_invariants"].values())
    assert len(contract["baseline_models"]) == 2
    assert all(model["estimated_parameters"] <= 2 for model in contract["candidate_models"])
    assert {m["id"] for m in contract["baseline_models"]} == {
        "persistence",
        "constant_policy_spread",
    }
    assert contract["estimation"]["final_evaluation"].startswith("2025-02..2025-11")


def test_delta_policy_recovers_known_beta():
    policy = [5.0, 5.0, 6.0, 6.0, 4.0, 4.0]
    lending = [7.0]
    beta = 0.5
    for i in range(1, len(policy)):
        lending.append(lending[-1] + beta * (policy[i] - policy[i - 1]))
    fit = fit_delta_policy(lending, policy, list(range(1, len(policy))), lag=0)
    assert fit.parameters["beta"] == pytest.approx(beta)
    assert fit.driver_sum_squares > 0


def test_delta_policy_rejects_no_policy_variation():
    with pytest.raises(RecoveryIdentifiabilityError):
        fit_delta_policy([7.0, 7.1, 7.2], [5.0, 5.0, 5.0], [1, 2], lag=0)


def test_static_affine_rejects_constant_policy():
    with pytest.raises(RecoveryIdentifiabilityError):
        fit_static_affine([7.0, 7.1, 7.2], [5.0, 5.0, 5.0], [0, 1, 2])


def test_expanding_origin_uses_only_prior_observations():
    policy = [5.0, 5.0, 6.0, 6.0, 5.0, 5.0]
    lending = [7.0, 7.0, 7.5, 7.5, 7.0, 7.0]
    predictions, fits = expanding_origin_predictions(
        "delta_policy_contemporaneous", lending, policy, [4, 5]
    )
    assert len(predictions) == 2
    assert fits[0].training_observations == 3
    assert fits[1].training_observations == 4


def test_parameter_domain_fraction_is_explicit():
    policy = [5.0, 5.0, 6.0, 6.0, 4.0, 4.0]
    lending = [7.0, 7.0, 7.5, 7.5, 6.5, 6.5]
    _, fits = expanding_origin_predictions(
        "delta_policy_contemporaneous", lending, policy, [4, 5]
    )
    assert 0.0 <= parameter_domain_fraction("delta_policy_contemporaneous", fits) <= 1.0


def test_error_metrics_are_transparent():
    metrics = error_metrics([1.0, 2.0], [1.0, 1.0])
    assert metrics["rmse"] == pytest.approx(2 ** -0.5)
    assert metrics["mae"] == pytest.approx(0.5)
    assert metrics["bias_actual_minus_predicted"] == pytest.approx(0.5)
