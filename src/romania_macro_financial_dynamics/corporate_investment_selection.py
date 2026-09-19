"""Dependency-free corporate-investment structural-selection primitives.

Implements only model forms frozen in the 2026-09-19 corporate-investment
structural-selection contract. No function opens the final evaluation window,
searches alternative lags/forms, or activates System Dynamics feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean
from typing import Iterable, Sequence


class CorporateInvestmentIdentifiabilityError(ValueError):
    """Raised when a frozen investment model is not estimable."""


@dataclass(frozen=True)
class InvestmentFit:
    model_id: str
    parameters: dict[str, float]
    training_observations: int
    design_rank: int
    standardized_condition_number: float


PARAMETER_ORDER = {
    "investment_rate_ar": ("alpha", "rho"),
    "core_lagged_drivers_ar": ("alpha", "rho", "beta_g", "beta_r"),
    "support_augmented_lagged_drivers_ar": (
        "alpha", "rho", "beta_g", "beta_r", "beta_s"
    ),
}


def _finite(values: Iterable[float]) -> None:
    if not all(isfinite(float(value)) for value in values):
        raise ValueError("corporate-investment inputs must be finite")


def quarter_index(period: str) -> int:
    if len(period) != 7 or period[4:6] != "-Q" or period[6] not in "1234":
        raise ValueError(f"invalid quarterly period: {period!r}")
    return int(period[:4]) * 4 + int(period[6]) - 1


def build_lagged_rows(
    records: Sequence[dict[str, object]],
) -> list[dict[str, float | str]]:
    if len(records) < 2:
        raise ValueError("at least two quarterly records are required")
    ordered = sorted(records, key=lambda row: quarter_index(str(row["period"])))
    periods = [str(row["period"]) for row in ordered]
    if len(periods) != len(set(periods)):
        raise ValueError("duplicate quarterly periods are not allowed")
    for left, right in zip(periods, periods[1:]):
        if quarter_index(right) != quarter_index(left) + 1:
            raise ValueError(
                f"quarterly investment history is not contiguous: {left} -> {right}"
            )

    result: list[dict[str, float | str]] = []
    required = (
        "nfc_investment_rate",
        "real_gdp_yoy_growth",
        "investment_grants_support_intensity",
        "nfc_new_business_lending_rate_up_to_one_year_quarterly_mean",
    )
    for previous, current in zip(ordered, ordered[1:]):
        y = float(current["nfc_investment_rate"])
        previous_values = [float(previous[name]) for name in required]
        _finite([y, *previous_values])
        result.append(
            {
                "period": str(current["period"]),
                "y": y,
                "y_lag": previous_values[0],
                "gdp_lag": previous_values[1],
                "support_lag": previous_values[2],
                "rate_lag": previous_values[3],
            }
        )
    return result


def _features(model_id: str, row: dict[str, float | str]) -> list[float]:
    if model_id == "investment_rate_ar":
        return [1.0, float(row["y_lag"])]
    if model_id == "core_lagged_drivers_ar":
        return [
            1.0,
            float(row["y_lag"]),
            float(row["gdp_lag"]),
            float(row["rate_lag"]),
        ]
    if model_id == "support_augmented_lagged_drivers_ar":
        return [
            1.0,
            float(row["y_lag"]),
            float(row["gdp_lag"]),
            float(row["rate_lag"]),
            float(row["support_lag"]),
        ]
    raise ValueError(f"unknown frozen corporate-investment model: {model_id}")


def _matrix_rank(matrix: Sequence[Sequence[float]], tol: float = 1e-10) -> int:
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
            raise CorporateInvestmentIdentifiabilityError(
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
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        tau = (aqq - app) / (2.0 * apq)
        t = (1.0 if tau >= 0.0 else -1.0) / (
            abs(tau) + sqrt(1.0 + tau * tau)
        )
        c = 1.0 / sqrt(1.0 + t * t)
        ss = t * c
        for k in range(n):
            if k in (p, q):
                continue
            akp, akq = a[k][p], a[k][q]
            a[k][p] = a[p][k] = c * akp - ss * akq
            a[k][q] = a[q][k] = ss * akp + c * akq
        a[p][p] = c*c*app - 2.0*ss*c*apq + ss*ss*aqq
        a[q][q] = ss*ss*app + 2.0*ss*c*apq + c*c*aqq
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
    predictors = [[float(row[j]) for row in design] for j in range(1, cols)]
    standardized_columns: list[list[float]] = []
    for values in predictors:
        mu = mean(values)
        variance = sum((value-mu)**2 for value in values) / len(values)
        if variance <= 1e-14:
            raise CorporateInvestmentIdentifiabilityError(
                "non-intercept predictor has no identifying variance"
            )
        sd = sqrt(variance)
        standardized_columns.append([(value-mu)/sd for value in values])
    z = [
        [1.0] + [standardized_columns[j][i] for j in range(cols-1)]
        for i in range(len(design))
    ]
    gram = [
        [sum(row[i]*row[j] for row in z) for j in range(cols)]
        for i in range(cols)
    ]
    eigenvalues = _jacobi_eigenvalues_symmetric(gram)
    positive = [v for v in eigenvalues if v > 1e-10]
    if len(positive) != cols:
        raise CorporateInvestmentIdentifiabilityError(
            "standardized design is rank deficient"
        )
    return sqrt(max(positive)/min(positive))


def fit_ols(
    model_id: str,
    rows: Sequence[dict[str, float | str]],
    *,
    condition_number_max: float,
) -> InvestmentFit:
    if model_id not in PARAMETER_ORDER:
        raise ValueError(f"unknown frozen corporate-investment model: {model_id}")
    if not rows:
        raise CorporateInvestmentIdentifiabilityError("no training observations")
    x = [_features(model_id, row) for row in rows]
    y = [float(row["y"]) for row in rows]
    _finite(v for row in x for v in row)
    _finite(y)
    columns = len(x[0])
    rank = _matrix_rank(x)
    if rank != columns:
        raise CorporateInvestmentIdentifiabilityError(
            f"design rank {rank} does not equal required {columns}"
        )
    condition = standardized_condition_number(x)
    if condition > condition_number_max:
        raise CorporateInvestmentIdentifiabilityError(
            f"standardized condition number {condition:.6g} exceeds "
            f"frozen maximum {condition_number_max:.6g}"
        )
    xtx = [
        [sum(row[i]*row[j] for row in x) for j in range(columns)]
        for i in range(columns)
    ]
    xty = [
        sum(row[i]*target for row,target in zip(x,y))
        for i in range(columns)
    ]
    coefficients = _solve_linear(xtx, xty)
    _finite(coefficients)
    return InvestmentFit(
        model_id=model_id,
        parameters=dict(zip(PARAMETER_ORDER[model_id], coefficients)),
        training_observations=len(rows),
        design_rank=rank,
        standardized_condition_number=condition,
    )


def predict(
    model_id: str,
    row: dict[str, float | str],
    fit: InvestmentFit | None,
) -> float:
    if model_id == "persistence":
        return float(row["y_lag"])
    if fit is None or fit.model_id != model_id:
        raise ValueError("matching fitted parameters are required")
    value = sum(
        fit.parameters[name] * feature
        for name,feature in zip(PARAMETER_ORDER[model_id], _features(model_id,row))
    )
    if not isfinite(value):
        raise ValueError("non-finite prediction")
    return float(value)


def expanding_origin_predictions(
    model_id: str,
    rows: Sequence[dict[str, float | str]],
    target_start: str,
    target_end: str,
    *,
    minimum_training_observations: int,
    condition_number_max: float,
) -> tuple[list[str],list[float],list[float],list[InvestmentFit]]:
    periods: list[str]=[]
    actual: list[float]=[]
    predicted: list[float]=[]
    fits: list[InvestmentFit]=[]
    for target_index,row in enumerate(rows):
        period=str(row["period"])
        if not (target_start <= period <= target_end):
            continue
        training=list(rows[:target_index])
        if len(training) < minimum_training_observations:
            raise CorporateInvestmentIdentifiabilityError(
                f"{period}: only {len(training)} training observations"
            )
        fit=None
        if model_id != "persistence":
            fit=fit_ols(
                model_id,training,condition_number_max=condition_number_max
            )
            fits.append(fit)
        periods.append(period)
        actual.append(float(row["y"]))
        predicted.append(predict(model_id,row,fit))
    if not periods:
        raise CorporateInvestmentIdentifiabilityError(
            f"no target observations in {target_start}..{target_end}"
        )
    return periods,actual,predicted,fits


def error_metrics(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> dict[str,float|int]:
    if not actual or len(actual) != len(predicted):
        raise ValueError("actual/predicted must be non-empty and equal length")
    _finite(actual); _finite(predicted)
    errors=[float(a-p) for a,p in zip(actual,predicted)]
    return {
        "n":len(errors),
        "rmse":sqrt(sum(e*e for e in errors)/len(errors)),
        "mae":sum(abs(e) for e in errors)/len(errors),
        "bias_actual_minus_predicted":sum(errors)/len(errors),
    }


def improvement(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return float("-inf")
    return 1.0 - candidate/baseline


def parameter_domain_fraction(
    fits: Sequence[InvestmentFit],
    parameter: str,
    lower: float | None,
    upper: float | None,
) -> float:
    if not fits:
        return 0.0
    valid=0
    for fit in fits:
        value=fit.parameters[parameter]
        ok=(lower is None or value >= lower) and (upper is None or value <= upper)
        valid += int(ok)
    return valid/len(fits)
