"""Dependency-free FX-inflation structural-selection primitives."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean
from typing import Sequence


class FxInflationIdentifiabilityError(ValueError):
    """Raised when a frozen monthly model is not identifiable."""


SEASONAL_FEATURES = tuple(f"month_{m:02d}" for m in range(2, 13))
MODEL_FEATURES = {
    "ar2_seasonal": (
        *SEASONAL_FEATURES,
        "pi_lag1",
        "pi_lag2",
    ),
    "external_price_baseline": (
        *SEASONAL_FEATURES,
        "pi_lag1",
        "pi_lag2",
        "dpstar_0",
        "dpstar_1_3_mean",
    ),
    "fx_candidate": (
        *SEASONAL_FEATURES,
        "pi_lag1",
        "pi_lag2",
        "dpstar_0",
        "dpstar_1_3_mean",
        "de_0",
        "de_1_3_mean",
        "de_4_6_mean",
        "de_7_12_mean",
    ),
}


@dataclass(frozen=True)
class FxInflationFit:
    model_id: str
    parameters: dict[str, float]
    training_observations: int
    design_rank: int
    standardized_condition_number: float


def _features(
    model_id: str,
    row: dict[str, float | str],
) -> list[float]:
    if model_id not in MODEL_FEATURES:
        raise ValueError(f"unknown frozen FX-inflation model: {model_id}")
    return [1.0] + [
        float(row[name]) for name in MODEL_FEATURES[model_id]
    ]


def _parameter_names(model_id: str) -> tuple[str, ...]:
    if model_id not in MODEL_FEATURES:
        raise ValueError(f"unknown frozen FX-inflation model: {model_id}")
    return ("alpha", *MODEL_FEATURES[model_id])


def _matrix_rank(
    matrix: Sequence[Sequence[float]],
    tol: float = 1e-10,
) -> int:
    if not matrix:
        return 0
    work = [list(map(float, row)) for row in matrix]
    rows = len(work)
    cols = len(work[0])
    rank = 0
    for col in range(cols):
        if rank >= rows:
            break
        pivot = max(range(rank, rows), key=lambda r: abs(work[r][col]))
        if abs(work[pivot][col]) <= tol:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        pivot_value = work[rank][col]
        for j in range(col, cols):
            work[rank][j] /= pivot_value
        for r in range(rows):
            if r == rank:
                continue
            factor = work[r][col]
            if abs(factor) <= tol:
                continue
            for j in range(col, cols):
                work[r][j] -= factor * work[rank][j]
        rank += 1
    return rank


def _solve_linear(
    system: Sequence[Sequence[float]],
    rhs: Sequence[float],
) -> list[float]:
    n = len(rhs)
    if len(system) != n or any(len(row) != n for row in system):
        raise ValueError("linear system must be square")
    aug = [
        list(map(float, row)) + [float(rhs[i])]
        for i, row in enumerate(system)
    ]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= 1e-12:
            raise FxInflationIdentifiabilityError(
                "singular normal equations"
            )
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pivot_value
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if abs(factor) <= 1e-15:
                continue
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def _jacobi_eigenvalues_symmetric(
    matrix: Sequence[Sequence[float]],
    *,
    tol: float = 1e-12,
    max_iter: int = 30000,
) -> list[float]:
    a = [list(map(float, row)) for row in matrix]
    n = len(a)
    if n == 0 or any(len(row) != n for row in a):
        raise ValueError("Jacobi input must be square")
    if n == 1:
        return [a[0][0]]

    for _ in range(max_iter):
        p, q = 0, 1
        largest = abs(a[p][q])
        for i in range(n):
            for j in range(i + 1, n):
                if abs(a[i][j]) > largest:
                    largest = abs(a[i][j])
                    p, q = i, j
        if largest <= tol:
            return [a[i][i] for i in range(n)]

        app = a[p][p]
        aqq = a[q][q]
        apq = a[p][q]
        tau = (aqq - app) / (2.0 * apq)
        t = (1.0 if tau >= 0.0 else -1.0) / (
            abs(tau) + sqrt(1.0 + tau * tau)
        )
        c = 1.0 / sqrt(1.0 + t * t)
        s = t * c

        for k in range(n):
            if k in (p, q):
                continue
            akp = a[k][p]
            akq = a[k][q]
            a[k][p] = a[p][k] = c * akp - s * akq
            a[k][q] = a[q][k] = s * akp + c * akq

        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0

    raise RuntimeError("Jacobi eigenvalue iteration did not converge")


def standardized_condition_number(
    design: Sequence[Sequence[float]],
) -> float:
    if not design:
        raise ValueError("empty design")
    cols = len(design[0])
    if cols < 2 or any(len(row) != cols for row in design):
        raise ValueError("invalid design matrix")

    standardized_columns: list[list[float]] = []
    for j in range(1, cols):
        values = [float(row[j]) for row in design]
        mu = mean(values)
        variance = sum((value - mu) ** 2 for value in values) / len(values)
        if variance <= 1e-14:
            raise FxInflationIdentifiabilityError(
                "non-intercept predictor has no identifying variance"
            )
        sd = sqrt(variance)
        standardized_columns.append(
            [(value - mu) / sd for value in values]
        )

    z = [
        [1.0]
        + [
            standardized_columns[j][i]
            for j in range(cols - 1)
        ]
        for i in range(len(design))
    ]
    gram = [
        [
            sum(row[i] * row[j] for row in z)
            for j in range(cols)
        ]
        for i in range(cols)
    ]
    eigenvalues = _jacobi_eigenvalues_symmetric(gram)
    positive = [value for value in eigenvalues if value > 1e-10]
    if len(positive) != cols:
        raise FxInflationIdentifiabilityError(
            "standardized design is rank deficient"
        )
    return sqrt(max(positive) / min(positive))


def fit_ols(
    model_id: str,
    rows: Sequence[dict[str, float | str]],
    *,
    condition_number_max: float,
) -> FxInflationFit:
    if not rows:
        raise FxInflationIdentifiabilityError("no training observations")
    x = [_features(model_id, row) for row in rows]
    y = [float(row["y"]) for row in rows]
    if not all(
        isfinite(value)
        for row in x
        for value in row
    ) or not all(isfinite(value) for value in y):
        raise ValueError("non-finite design or target")

    columns = len(x[0])
    rank = _matrix_rank(x)
    if rank != columns:
        raise FxInflationIdentifiabilityError(
            f"design rank {rank} does not equal required {columns}"
        )
    condition = standardized_condition_number(x)
    if condition > condition_number_max:
        raise FxInflationIdentifiabilityError(
            f"standardized condition number {condition:.6g} exceeds "
            f"frozen maximum {condition_number_max:.6g}"
        )

    xtx = [
        [
            sum(row[i] * row[j] for row in x)
            for j in range(columns)
        ]
        for i in range(columns)
    ]
    xty = [
        sum(row[i] * target for row, target in zip(x, y))
        for i in range(columns)
    ]
    coefficients = _solve_linear(xtx, xty)
    if not all(isfinite(value) for value in coefficients):
        raise FxInflationIdentifiabilityError("non-finite coefficients")
    return FxInflationFit(
        model_id=model_id,
        parameters=dict(zip(_parameter_names(model_id), coefficients)),
        training_observations=len(rows),
        design_rank=rank,
        standardized_condition_number=condition,
    )


def predict(
    model_id: str,
    row: dict[str, float | str],
    fit: FxInflationFit | None = None,
) -> float:
    if model_id == "persistence":
        return float(row["pi_lag1"])
    if fit is None or fit.model_id != model_id:
        raise ValueError("matching fit is required")
    features = _features(model_id, row)
    names = _parameter_names(model_id)
    value = sum(
        fit.parameters[name] * feature
        for name, feature in zip(names, features)
    )
    if not isfinite(value):
        raise ValueError("non-finite prediction")
    return float(value)


def expanding_origin_predictions(
    model_id: str,
    rows: Sequence[dict[str, float | str]],
    *,
    selection_start: str,
    selection_end: str,
    minimum_training_observations: int,
    condition_number_max: float,
) -> tuple[
    list[str],
    list[float],
    list[float],
    list[FxInflationFit],
]:
    periods: list[str] = []
    actual: list[float] = []
    predicted: list[float] = []
    fits: list[FxInflationFit] = []
    for index, row in enumerate(rows):
        period = str(row["period"])
        if not (selection_start <= period <= selection_end):
            continue
        training = list(rows[:index])
        if len(training) < minimum_training_observations:
            raise FxInflationIdentifiabilityError(
                f"{period}: only {len(training)} training observations"
            )
        fit = None
        if model_id != "persistence":
            fit = fit_ols(
                model_id,
                training,
                condition_number_max=condition_number_max,
            )
            fits.append(fit)
        periods.append(period)
        actual.append(float(row["y"]))
        predicted.append(predict(model_id, row, fit))
    if not periods:
        raise FxInflationIdentifiabilityError("no selection origins")
    return periods, actual, predicted, fits


def error_metrics(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> dict[str, float | int]:
    if not actual or len(actual) != len(predicted):
        raise ValueError("actual/predicted length mismatch")
    errors = [
        float(a - p)
        for a, p in zip(actual, predicted)
    ]
    return {
        "n": len(errors),
        "rmse": sqrt(
            sum(error * error for error in errors) / len(errors)
        ),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "bias_actual_minus_predicted": sum(errors) / len(errors),
    }


def improvement(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return float("-inf")
    return 1.0 - candidate / baseline


def cumulative_fx_effects(
    fit: FxInflationFit,
) -> tuple[float, float]:
    p = fit.parameters
    short = p["de_0"] + p["de_1_3_mean"]
    full = (
        short
        + p["de_4_6_mean"]
        + p["de_7_12_mean"]
    )
    return short, full
