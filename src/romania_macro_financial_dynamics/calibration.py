"""Calibration and validation utilities for the scientific core.

The module is intentionally dependency-light and deterministic. It supports the
small public diagnostic sample without hiding practical non-identifiability
behind a regularizer or Bayesian prior. Holdout role assignment belongs to the
frozen data manifest and is never inferred from performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable, Sequence


class PracticalIdentifiabilityError(ValueError):
    """Raised when the design cannot identify all requested parameters."""


@dataclass(frozen=True)
class PartialAdjustmentFit:
    intercept_target: float
    long_run_pass_through: float
    adjustment_speed: float
    transformed_intercept: float
    transformed_policy: float
    transformed_lagged_rate: float
    rank: int
    condition_proxy: float
    n_targets: int
    rmse: float
    mae: float


def _finite(values: Iterable[float]) -> None:
    if not all(isfinite(float(value)) for value in values):
        raise ValueError("Calibration inputs must be finite")


def matrix_rank(matrix: Sequence[Sequence[float]], tol: float = 1e-10) -> int:
    """Small deterministic row-reduction rank used for identifiability gates."""

    rows = [list(map(float, row)) for row in matrix]
    if not rows:
        return 0
    n_rows = len(rows)
    n_cols = len(rows[0])
    if any(len(row) != n_cols for row in rows):
        raise ValueError("Matrix must be rectangular")

    pivot_row = 0
    column = 0
    while pivot_row < n_rows and column < n_cols:
        pivot = max(range(pivot_row, n_rows), key=lambda r: abs(rows[r][column]))
        if abs(rows[pivot][column]) <= tol:
            column += 1
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        scale = rows[pivot_row][column]
        for j in range(column, n_cols):
            rows[pivot_row][j] /= scale
        for r in range(n_rows):
            if r == pivot_row:
                continue
            factor = rows[r][column]
            if abs(factor) <= tol:
                continue
            for j in range(column, n_cols):
                rows[r][j] -= factor * rows[pivot_row][j]
        pivot_row += 1
        column += 1
    return pivot_row


def _solve_square(matrix: Sequence[Sequence[float]], vector: Sequence[float], tol: float = 1e-12) -> list[float]:
    a = [list(map(float, row)) for row in matrix]
    b = list(map(float, vector))
    n = len(b)
    if len(a) != n or any(len(row) != n for row in a):
        raise ValueError("Linear system must be square")
    for column in range(n):
        pivot = max(range(column, n), key=lambda r: abs(a[r][column]))
        if abs(a[pivot][column]) <= tol:
            raise PracticalIdentifiabilityError("Singular normal-equation system")
        a[column], a[pivot] = a[pivot], a[column]
        b[column], b[pivot] = b[pivot], b[column]
        scale = a[column][column]
        for j in range(column, n):
            a[column][j] /= scale
        b[column] /= scale
        for r in range(n):
            if r == column:
                continue
            factor = a[r][column]
            for j in range(column, n):
                a[r][j] -= factor * a[column][j]
            b[r] -= factor * b[column]
    return b


def _gram_condition_proxy(x: Sequence[Sequence[float]]) -> float:
    """Infinity-norm condition proxy based on X'X, square-rooted to X scale."""

    cols = len(x[0])
    gram = [[sum(row[i] * row[j] for row in x) for j in range(cols)] for i in range(cols)]
    norm = max(sum(abs(value) for value in row) for row in gram)
    if matrix_rank(gram) < cols:
        return float("inf")
    inverse_columns: list[list[float]] = []
    for i in range(cols):
        unit = [0.0] * cols
        unit[i] = 1.0
        inverse_columns.append(_solve_square(gram, unit))
    inverse = [[inverse_columns[j][i] for j in range(cols)] for i in range(cols)]
    inverse_norm = max(sum(abs(value) for value in row) for row in inverse)
    return sqrt(norm * inverse_norm)


def error_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float | int]:
    if len(actual) != len(predicted) or not actual:
        raise ValueError("actual and predicted must be non-empty and equal length")
    _finite(actual)
    _finite(predicted)
    errors = [a - p for a, p in zip(actual, predicted)]
    return {
        "n": len(errors),
        "rmse": sqrt(sum(error * error for error in errors) / len(errors)),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "bias_actual_minus_predicted": sum(errors) / len(errors),
    }


def partial_adjustment_prediction(
    previous_rate: float,
    policy_rate: float,
    *,
    intercept_target: float,
    long_run_pass_through: float,
    adjustment_speed: float,
) -> float:
    _finite((previous_rate, policy_rate, intercept_target, long_run_pass_through, adjustment_speed))
    return previous_rate + adjustment_speed * (
        intercept_target + long_run_pass_through * policy_rate - previous_rate
    )


def fit_partial_adjustment(
    lending_rates: Sequence[float],
    policy_rates: Sequence[float],
    target_indices: Sequence[int] | None = None,
) -> PartialAdjustmentFit:
    """OLS fit of the declared partial-adjustment form.

    The regression is estimated in the linear reparameterization
    Δr_t = c + b*policy_t + d*r_(t-1), where lambda=-d,
    beta=b/lambda and alpha=c/lambda. Rank deficiency is a scientific result and
    causes a hard failure rather than automatic regularisation.
    """

    if len(lending_rates) != len(policy_rates) or len(lending_rates) < 2:
        raise ValueError("Aligned lending/policy series with at least two observations are required")
    _finite(lending_rates)
    _finite(policy_rates)
    indices = list(target_indices) if target_indices is not None else list(range(1, len(lending_rates)))
    if not indices or min(indices) < 1 or max(indices) >= len(lending_rates):
        raise ValueError("target_indices must address observations after the first")

    x = [[1.0, float(policy_rates[i]), float(lending_rates[i - 1])] for i in indices]
    z = [float(lending_rates[i] - lending_rates[i - 1]) for i in indices]
    rank = matrix_rank(x)
    if rank < 3:
        raise PracticalIdentifiabilityError(
            f"Partial-adjustment design rank {rank}/3: intercept, policy pass-through and lag adjustment are not separately identifiable"
        )

    gram = [[sum(row[a] * row[b] for row in x) for b in range(3)] for a in range(3)]
    cross = [sum(row[a] * outcome for row, outcome in zip(x, z)) for a in range(3)]
    c, b, d = _solve_square(gram, cross)
    adjustment_speed = -d
    if abs(adjustment_speed) <= 1e-12:
        raise PracticalIdentifiabilityError("Adjustment speed is numerically zero, so long-run coefficients are unidentified")
    intercept_target = c / adjustment_speed
    pass_through = b / adjustment_speed

    predictions = [
        partial_adjustment_prediction(
            lending_rates[i - 1],
            policy_rates[i],
            intercept_target=intercept_target,
            long_run_pass_through=pass_through,
            adjustment_speed=adjustment_speed,
        )
        for i in indices
    ]
    metrics = error_metrics([lending_rates[i] for i in indices], predictions)
    return PartialAdjustmentFit(
        intercept_target=intercept_target,
        long_run_pass_through=pass_through,
        adjustment_speed=adjustment_speed,
        transformed_intercept=c,
        transformed_policy=b,
        transformed_lagged_rate=d,
        rank=rank,
        condition_proxy=_gram_condition_proxy(x),
        n_targets=len(indices),
        rmse=float(metrics["rmse"]),
        mae=float(metrics["mae"]),
    )


def persistence_predictions(lending_rates: Sequence[float], target_indices: Sequence[int]) -> list[float]:
    return [float(lending_rates[i - 1]) for i in target_indices]


def fit_constant_policy_spread(
    lending_rates: Sequence[float], policy_rates: Sequence[float], observation_indices: Sequence[int]
) -> float:
    if not observation_indices:
        raise ValueError("observation_indices must not be empty")
    return sum(lending_rates[i] - policy_rates[i] for i in observation_indices) / len(observation_indices)


def constant_spread_predictions(
    policy_rates: Sequence[float], target_indices: Sequence[int], calibrated_spread: float
) -> list[float]:
    return [float(policy_rates[i] + calibrated_spread) for i in target_indices]


def one_step_predictions(
    fit: PartialAdjustmentFit,
    lending_rates: Sequence[float],
    policy_rates: Sequence[float],
    target_indices: Sequence[int],
) -> list[float]:
    return [
        partial_adjustment_prediction(
            lending_rates[i - 1],
            policy_rates[i],
            intercept_target=fit.intercept_target,
            long_run_pass_through=fit.long_run_pass_through,
            adjustment_speed=fit.adjustment_speed,
        )
        for i in target_indices
    ]


def rolling_origin_diagnostics(
    lending_rates: Sequence[float],
    policy_rates: Sequence[float],
    selection_indices: Sequence[int],
) -> list[dict[str, float | int | str | None]]:
    """Expanding-window one-step diagnostics using only information before each origin."""

    results: list[dict[str, float | int | str | None]] = []
    for target in selection_indices:
        prior_targets = list(range(1, target))
        design = [[1.0, policy_rates[i], lending_rates[i - 1]] for i in prior_targets]
        rank = matrix_rank(design)
        if rank < 3:
            results.append({"target_index": target, "status": "NOT_IDENTIFIABLE", "rank": rank, "prediction": None})
            continue
        fit = fit_partial_adjustment(lending_rates, policy_rates, prior_targets)
        prediction = one_step_predictions(fit, lending_rates, policy_rates, [target])[0]
        results.append(
            {
                "target_index": target,
                "status": "ESTIMATED",
                "rank": fit.rank,
                "condition_proxy": fit.condition_proxy,
                "intercept_target": fit.intercept_target,
                "long_run_pass_through": fit.long_run_pass_through,
                "adjustment_speed": fit.adjustment_speed,
                "prediction": prediction,
                "actual": float(lending_rates[target]),
            }
        )
    return results


def local_sensitivity_rmse(
    fit: PartialAdjustmentFit,
    lending_rates: Sequence[float],
    policy_rates: Sequence[float],
    target_indices: Sequence[int],
    fraction: float = 0.10,
) -> dict[str, dict[str, float]]:
    """One-at-a-time ±fraction parameter perturbation on a fixed evaluation slice."""

    if fraction <= 0:
        raise ValueError("fraction must be positive")
    actual = [lending_rates[i] for i in target_indices]
    result: dict[str, dict[str, float]] = {}
    params = {
        "intercept_target": fit.intercept_target,
        "long_run_pass_through": fit.long_run_pass_through,
        "adjustment_speed": fit.adjustment_speed,
    }
    for name in params:
        values: dict[str, float] = {}
        for label, factor in (("minus", 1.0 - fraction), ("plus", 1.0 + fraction)):
            altered = dict(params)
            altered[name] *= factor
            predictions = [
                partial_adjustment_prediction(
                    lending_rates[i - 1],
                    policy_rates[i],
                    intercept_target=altered["intercept_target"],
                    long_run_pass_through=altered["long_run_pass_through"],
                    adjustment_speed=altered["adjustment_speed"],
                )
                for i in target_indices
            ]
            values[label] = float(error_metrics(actual, predictions)["rmse"])
        result[name] = values
    return result
