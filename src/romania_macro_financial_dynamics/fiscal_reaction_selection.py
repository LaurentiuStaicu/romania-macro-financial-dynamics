"""Dependency-free annual fiscal-reaction selection primitives.

Implements only the forms frozen in the 2026-09-19 annual fiscal-reaction
structural-selection contract. No function in this module opens final
evaluation, searches alternative forms, or activates System Dynamics closure.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean
from typing import Iterable, Sequence


class FiscalReactionIdentifiabilityError(ValueError):
    """Raised when a frozen annual model is not estimable."""


@dataclass(frozen=True)
class FiscalReactionFit:
    model_id: str
    parameters: dict[str, float]
    training_observations: int
    design_rank: int
    standardized_condition_number: float


PARAMETER_ORDER = {
    "primary_balance_ar": ("alpha", "rho"),
    "lagged_state_fiscal_balance_ar": (
        "alpha",
        "rho",
        "beta_d",
        "beta_y",
    ),
}


def _finite(values: Iterable[float]) -> None:
    if not all(isfinite(float(value)) for value in values):
        raise ValueError("annual fiscal-reaction inputs must be finite")


def build_lagged_rows(
    records: Sequence[dict[str, object]],
) -> list[dict[str, float | int]]:
    if len(records) < 2:
        raise ValueError("at least two annual records are required")
    ordered = sorted(records, key=lambda row: int(row["year"]))
    years = [int(row["year"]) for row in ordered]
    if len(years) != len(set(years)):
        raise ValueError("duplicate annual periods are not allowed")
    for left, right in zip(years, years[1:]):
        if right != left + 1:
            raise ValueError(
                f"annual history is not contiguous: {left} -> {right}"
            )

    result: list[dict[str, float | int]] = []
    for previous, current in zip(ordered, ordered[1:]):
        current_pb = float(current["primary_balance_pct_gdp"])
        previous_values = [
            float(previous["primary_balance_pct_gdp"]),
            float(previous["debt_pct_gdp"]),
            float(previous["output_gap_pct_potential_gdp"]),
        ]
        _finite([current_pb, *previous_values])
        result.append(
            {
                "year": int(current["year"]),
                "y": current_pb,
                "y_lag": previous_values[0],
                "debt_lag": previous_values[1],
                "output_gap_lag": previous_values[2],
            }
        )
    return result


def _features(
    model_id: str,
    row: dict[str, float | int],
) -> list[float]:
    if model_id == "primary_balance_ar":
        return [1.0, float(row["y_lag"])]
    if model_id == "lagged_state_fiscal_balance_ar":
        return [
            1.0,
            float(row["y_lag"]),
            float(row["debt_lag"]),
            float(row["output_gap_lag"]),
        ]
    raise ValueError(f"unknown frozen fiscal-reaction model: {model_id}")


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
        value = work[rank][col]
        for j in range(col, cols):
            work[rank][j] /= value
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
            raise FiscalReactionIdentifiabilityError(
                "singular normal equations"
            )
        aug[col], aug[pivot] = aug[pivot], aug[col]
        value = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= value
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
    max_iter: int = 10000,
) -> list[float]:
    a = [list(map(float, row)) for row in matrix]
    n = len(a)
    if n == 0 or any(len(row) != n for row in a):
        raise ValueError("Jacobi eigenvalue input must be square")
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

    predictors = [
        [float(row[j]) for row in design]
        for j in range(1, cols)
    ]
    standardized_columns: list[list[float]] = []
    for values in predictors:
        mu = mean(values)
        variance = (
            sum((value - mu) ** 2 for value in values) / len(values)
        )
        if variance <= 1e-14:
            raise FiscalReactionIdentifiabilityError(
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
        raise FiscalReactionIdentifiabilityError(
            "standardized design is rank deficient"
        )
    return sqrt(max(positive) / min(positive))


def fit_ols(
    model_id: str,
    rows: Sequence[dict[str, float | int]],
    *,
    condition_number_max: float,
) -> FiscalReactionFit:
    if model_id not in PARAMETER_ORDER:
        raise ValueError(f"unknown frozen fiscal-reaction model: {model_id}")
    if not rows:
        raise FiscalReactionIdentifiabilityError(
            "no training observations"
        )

    x = [_features(model_id, row) for row in rows]
    y = [float(row["y"]) for row in rows]
    _finite(value for row in x for value in row)
    _finite(y)

    columns = len(x[0])
    rank = _matrix_rank(x)
    if rank != columns:
        raise FiscalReactionIdentifiabilityError(
            f"design rank {rank} does not equal required {columns}"
        )
    condition = standardized_condition_number(x)
    if condition > condition_number_max:
        raise FiscalReactionIdentifiabilityError(
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
    _finite(coefficients)
    names = PARAMETER_ORDER[model_id]
    return FiscalReactionFit(
        model_id=model_id,
        parameters=dict(zip(names, coefficients)),
        training_observations=len(rows),
        design_rank=rank,
        standardized_condition_number=condition,
    )


def predict(
    model_id: str,
    row: dict[str, float | int],
    fit: FiscalReactionFit | None,
) -> float:
    if model_id == "persistence":
        return float(row["y_lag"])
    if fit is None or fit.model_id != model_id:
        raise ValueError("matching fitted parameters are required")
    features = _features(model_id, row)
    names = PARAMETER_ORDER[model_id]
    value = sum(
        fit.parameters[name] * feature
        for name, feature in zip(names, features)
    )
    if not isfinite(value):
        raise ValueError("non-finite prediction")
    return float(value)


def expanding_origin_predictions(
    model_id: str,
    rows: Sequence[dict[str, float | int]],
    target_start: int,
    target_end: int,
    *,
    minimum_training_observations: int,
    condition_number_max: float,
) -> tuple[
    list[int],
    list[float],
    list[float],
    list[FiscalReactionFit],
]:
    years: list[int] = []
    actual: list[float] = []
    predicted: list[float] = []
    fits: list[FiscalReactionFit] = []

    for target_index, row in enumerate(rows):
        year = int(row["year"])
        if not (target_start <= year <= target_end):
            continue
        training = list(rows[:target_index])
        if len(training) < minimum_training_observations:
            raise FiscalReactionIdentifiabilityError(
                f"{year}: only {len(training)} training observations"
            )
        fit = None
        if model_id != "persistence":
            fit = fit_ols(
                model_id,
                training,
                condition_number_max=condition_number_max,
            )
            fits.append(fit)
        years.append(year)
        actual.append(float(row["y"]))
        predicted.append(predict(model_id, row, fit))

    if not years:
        raise FiscalReactionIdentifiabilityError(
            f"no target observations in {target_start}..{target_end}"
        )
    return years, actual, predicted, fits


def error_metrics(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> dict[str, float | int]:
    if not actual or len(actual) != len(predicted):
        raise ValueError(
            "actual/predicted must be non-empty and equal length"
        )
    _finite(actual)
    _finite(predicted)
    errors = [
        float(a - p)
        for a, p in zip(actual, predicted)
    ]
    return {
        "n": len(errors),
        "rmse": sqrt(
            sum(error * error for error in errors) / len(errors)
        ),
        "mae": (
            sum(abs(error) for error in errors) / len(errors)
        ),
        "bias_actual_minus_predicted": (
            sum(errors) / len(errors)
        ),
    }


def improvement(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return float("-inf")
    return 1.0 - candidate / baseline


def parameter_domain_fraction(
    fits: Sequence[FiscalReactionFit],
    parameter: str,
    lower: float | None,
    upper: float | None,
) -> float:
    if not fits:
        return 0.0
    valid = 0
    for fit in fits:
        value = fit.parameters[parameter]
        ok = (
            (lower is None or value >= lower)
            and (upper is None or value <= upper)
        )
        valid += int(ok)
    return valid / len(fits)
