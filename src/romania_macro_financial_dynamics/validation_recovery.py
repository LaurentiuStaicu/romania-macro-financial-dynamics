"""Parsimonious validation-recovery estimators for Alpha 0.5.x.

This module is deliberately small and dependency-free. It supports predeclared
one- and two-parameter monetary pass-through candidates, simple baselines and
expanding-origin diagnostics. It contains no holdout-specific tuning logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean, median
from typing import Iterable, Sequence


class RecoveryIdentifiabilityError(ValueError):
    """Raised when a predeclared recovery form cannot be estimated."""


@dataclass(frozen=True)
class Fit:
    model_id: str
    parameters: dict[str, float]
    training_observations: int
    driver_sum_squares: float | None = None
    design_rank: int | None = None


def _finite(values: Iterable[float]) -> None:
    if not all(isfinite(float(value)) for value in values):
        raise ValueError("Recovery inputs must be finite")


def error_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float | int]:
    if len(actual) != len(predicted) or not actual:
        raise ValueError("actual/predicted must be non-empty and equal length")
    _finite(actual)
    _finite(predicted)
    errors = [float(a - p) for a, p in zip(actual, predicted)]
    return {
        "n": len(errors),
        "rmse": sqrt(sum(error * error for error in errors) / len(errors)),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "bias_actual_minus_predicted": sum(errors) / len(errors),
    }


def persistence_prediction(lending: Sequence[float], target_index: int) -> float:
    if target_index < 1:
        raise ValueError("Persistence requires a lagged observation")
    return float(lending[target_index - 1])


def fit_constant_spread(
    lending: Sequence[float], policy: Sequence[float], observation_indices: Sequence[int]
) -> Fit:
    if not observation_indices:
        raise RecoveryIdentifiabilityError("No observations for constant-spread fit")
    spreads = [float(lending[i] - policy[i]) for i in observation_indices]
    _finite(spreads)
    return Fit(
        model_id="constant_policy_spread",
        parameters={"spread": mean(spreads)},
        training_observations=len(spreads),
    )


def predict_constant_spread(policy: Sequence[float], target_index: int, fit: Fit) -> float:
    return float(policy[target_index] + fit.parameters["spread"])


def _delta_driver(policy: Sequence[float], target_index: int, lag: int) -> float:
    if lag == 0:
        if target_index < 1:
            raise ValueError("Contemporaneous delta requires t>=1")
        return float(policy[target_index] - policy[target_index - 1])
    if lag == 1:
        if target_index < 2:
            raise ValueError("Lag-1 delta requires t>=2")
        return float(policy[target_index - 1] - policy[target_index - 2])
    raise ValueError("Only lag 0 or 1 is preregistered")


def fit_delta_policy(
    lending: Sequence[float],
    policy: Sequence[float],
    transition_indices: Sequence[int],
    *,
    lag: int,
) -> Fit:
    usable = [i for i in transition_indices if i >= 1 + lag]
    if not usable:
        raise RecoveryIdentifiabilityError("No usable transitions for delta-policy fit")
    x = [_delta_driver(policy, i, lag) for i in usable]
    y = [float(lending[i] - lending[i - 1]) for i in usable]
    _finite(x)
    _finite(y)
    denominator = sum(value * value for value in x)
    if denominator <= 1e-12:
        raise RecoveryIdentifiabilityError("Policy-change driver has no identifying variation")
    beta = sum(driver * outcome for driver, outcome in zip(x, y)) / denominator
    return Fit(
        model_id="delta_policy_contemporaneous" if lag == 0 else "delta_policy_lag1",
        parameters={"beta": beta},
        training_observations=len(usable),
        driver_sum_squares=denominator,
        design_rank=1,
    )


def predict_delta_policy(
    lending: Sequence[float], policy: Sequence[float], target_index: int, fit: Fit, *, lag: int
) -> float:
    return float(
        lending[target_index - 1]
        + fit.parameters["beta"] * _delta_driver(policy, target_index, lag)
    )


def fit_anchored_adjustment(
    lending: Sequence[float],
    policy: Sequence[float],
    observation_indices: Sequence[int],
    transition_indices: Sequence[int],
) -> Fit:
    spread_fit = fit_constant_spread(lending, policy, observation_indices)
    spread = spread_fit.parameters["spread"]
    usable = [i for i in transition_indices if i >= 1]
    if not usable:
        raise RecoveryIdentifiabilityError("No transitions for anchored adjustment")
    gaps = [float(policy[i] + spread - lending[i - 1]) for i in usable]
    changes = [float(lending[i] - lending[i - 1]) for i in usable]
    denominator = sum(gap * gap for gap in gaps)
    if denominator <= 1e-12:
        raise RecoveryIdentifiabilityError("Anchored adjustment gap has no identifying variation")
    adjustment = sum(gap * change for gap, change in zip(gaps, changes)) / denominator
    return Fit(
        model_id="anchored_partial_adjustment",
        parameters={"spread": spread, "lambda": adjustment},
        training_observations=len(usable),
        driver_sum_squares=denominator,
        design_rank=1,
    )


def predict_anchored_adjustment(
    lending: Sequence[float], policy: Sequence[float], target_index: int, fit: Fit
) -> float:
    previous = float(lending[target_index - 1])
    target = float(policy[target_index] + fit.parameters["spread"])
    return previous + fit.parameters["lambda"] * (target - previous)


def fit_static_affine(
    lending: Sequence[float], policy: Sequence[float], observation_indices: Sequence[int]
) -> Fit:
    if len(observation_indices) < 2:
        raise RecoveryIdentifiabilityError("Static affine fit requires at least two observations")
    x = [float(policy[i]) for i in observation_indices]
    y = [float(lending[i]) for i in observation_indices]
    xbar = mean(x)
    ybar = mean(y)
    denominator = sum((value - xbar) ** 2 for value in x)
    if denominator <= 1e-12:
        raise RecoveryIdentifiabilityError("Policy level is constant; affine beta is unidentified")
    beta = sum((xi - xbar) * (yi - ybar) for xi, yi in zip(x, y)) / denominator
    alpha = ybar - beta * xbar
    return Fit(
        model_id="static_affine_policy_level",
        parameters={"alpha": alpha, "beta": beta},
        training_observations=len(x),
        driver_sum_squares=denominator,
        design_rank=2,
    )


def predict_static_affine(policy: Sequence[float], target_index: int, fit: Fit) -> float:
    return float(fit.parameters["alpha"] + fit.parameters["beta"] * policy[target_index])


def fit_model(
    model_id: str,
    lending: Sequence[float],
    policy: Sequence[float],
    observation_indices: Sequence[int],
    transition_indices: Sequence[int],
) -> Fit:
    if model_id == "constant_policy_spread":
        return fit_constant_spread(lending, policy, observation_indices)
    if model_id == "delta_policy_contemporaneous":
        return fit_delta_policy(lending, policy, transition_indices, lag=0)
    if model_id == "delta_policy_lag1":
        return fit_delta_policy(lending, policy, transition_indices, lag=1)
    if model_id == "anchored_partial_adjustment":
        return fit_anchored_adjustment(
            lending, policy, observation_indices, transition_indices
        )
    if model_id == "static_affine_policy_level":
        return fit_static_affine(lending, policy, observation_indices)
    raise ValueError(f"Unknown preregistered recovery model: {model_id}")


def predict_model(
    model_id: str,
    lending: Sequence[float],
    policy: Sequence[float],
    target_index: int,
    fit: Fit | None = None,
) -> float:
    if model_id == "persistence":
        return persistence_prediction(lending, target_index)
    if fit is None:
        raise ValueError("Fitted parameters required")
    if model_id == "constant_policy_spread":
        return predict_constant_spread(policy, target_index, fit)
    if model_id == "delta_policy_contemporaneous":
        return predict_delta_policy(lending, policy, target_index, fit, lag=0)
    if model_id == "delta_policy_lag1":
        return predict_delta_policy(lending, policy, target_index, fit, lag=1)
    if model_id == "anchored_partial_adjustment":
        return predict_anchored_adjustment(lending, policy, target_index, fit)
    if model_id == "static_affine_policy_level":
        return predict_static_affine(policy, target_index, fit)
    raise ValueError(f"Unknown preregistered recovery model: {model_id}")


def parameter_domain_fraction(model_id: str, fits: Sequence[Fit]) -> float:
    if not fits:
        return 0.0
    valid = 0
    for fit in fits:
        if model_id in {"delta_policy_contemporaneous", "delta_policy_lag1", "static_affine_policy_level"}:
            beta = fit.parameters["beta"]
            ok = 0.0 <= beta <= 2.0
        elif model_id == "anchored_partial_adjustment":
            value = fit.parameters["lambda"]
            ok = 0.0 <= value <= 1.0
        else:
            ok = True
        valid += int(ok)
    return valid / len(fits)


def parameter_summary(model_id: str, fits: Sequence[Fit]) -> dict[str, object]:
    if not fits:
        return {"n": 0}
    names = sorted({name for fit in fits for name in fit.parameters})
    result: dict[str, object] = {
        "n": len(fits),
        "domain_fraction": parameter_domain_fraction(model_id, fits),
    }
    for name in names:
        values = [fit.parameters[name] for fit in fits if name in fit.parameters]
        result[name] = {
            "median": median(values),
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
        }
    return result


def expanding_origin_predictions(
    model_id: str,
    lending: Sequence[float],
    policy: Sequence[float],
    target_indices: Sequence[int],
) -> tuple[list[float], list[Fit]]:
    predictions: list[float] = []
    fits: list[Fit] = []
    for target in target_indices:
        if target < 2:
            raise ValueError("Selection targets require at least two prior months")
        if model_id == "persistence":
            predictions.append(persistence_prediction(lending, target))
            continue
        observation_indices = list(range(0, target))
        transition_indices = list(range(1, target))
        fit = fit_model(
            model_id,
            lending,
            policy,
            observation_indices,
            transition_indices,
        )
        predictions.append(predict_model(model_id, lending, policy, target, fit))
        fits.append(fit)
    return predictions, fits


def count_nonzero_policy_changes(policy: Sequence[float], indices: Sequence[int]) -> int:
    return sum(
        1
        for i in indices
        if i >= 1 and abs(float(policy[i] - policy[i - 1])) > 1e-12
    )
