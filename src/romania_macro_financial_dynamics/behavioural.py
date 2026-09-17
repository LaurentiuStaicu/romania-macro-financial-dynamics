"""Empirical-dynamics behavioural forms for Alpha 0.4.0a0.

These are transparent candidate/admitted functional forms. They never invent
parameter values: every coefficient required for numerical use must be supplied
explicitly by a calibration/validation layer. Accounting Spine and Dynamic Core
identities remain hard constraints.
"""

from __future__ import annotations

from math import isfinite


class InvalidBehaviouralInput(ValueError):
    """Raised when a behavioural equation receives an invalid input/parameter."""


def _finite(*values: float) -> None:
    if not all(isfinite(value) for value in values):
        raise InvalidBehaviouralInput("Behavioural inputs and parameters must be finite")


def _unit_interval(value: float, name: str) -> None:
    _finite(value)
    if not 0.0 <= value <= 1.0:
        raise InvalidBehaviouralInput(f"{name} must lie in [0, 1]")


def partial_adjustment_rate(
    previous_rate: float,
    policy_rate: float,
    *,
    intercept: float,
    long_run_pass_through: float,
    adjustment_speed: float,
) -> float:
    """Partial-adjustment pass-through from policy to a bank lending rate.

    r_t = r_(t-1) + lambda * (alpha + beta * policy_t - r_(t-1))

    Rates are percentage points per annum. ``adjustment_speed`` is a fraction of
    the remaining gap closed per observation period.
    """

    _finite(previous_rate, policy_rate, intercept, long_run_pass_through)
    _unit_interval(adjustment_speed, "adjustment_speed")
    target = intercept + long_run_pass_through * policy_rate
    return previous_rate + adjustment_speed * (target - previous_rate)


def refinancing_effective_rate(
    previous_effective_rate: float,
    marginal_market_yield: float,
    *,
    refinancing_share: float,
) -> float:
    """Weighted repricing of the effective debt rate as debt is refinanced.

    This is a stock-composition mechanism, not a fiscal reaction function.
    ``refinancing_share`` must be supported by maturity/refinancing data.
    """

    _finite(previous_effective_rate, marginal_market_yield)
    _unit_interval(refinancing_share, "refinancing_share")
    return (1.0 - refinancing_share) * previous_effective_rate + refinancing_share * marginal_market_yield


def household_consumption_growth(
    *,
    disposable_income_growth: float,
    real_borrowing_rate: float,
    debt_service_ratio: float,
    intercept: float,
    income_sensitivity: float,
    rate_sensitivity: float,
    debt_service_sensitivity: float,
) -> float:
    """Candidate reduced-form household consumption-growth equation."""

    _finite(
        disposable_income_growth,
        real_borrowing_rate,
        debt_service_ratio,
        intercept,
        income_sensitivity,
        rate_sensitivity,
        debt_service_sensitivity,
    )
    return (
        intercept
        + income_sensitivity * disposable_income_growth
        - rate_sensitivity * real_borrowing_rate
        - debt_service_sensitivity * debt_service_ratio
    )


def corporate_investment_growth(
    *,
    demand_growth: float,
    real_corporate_lending_rate: float,
    eu_fund_impulse: float,
    intercept: float,
    demand_sensitivity: float,
    rate_sensitivity: float,
    eu_fund_sensitivity: float,
) -> float:
    """Candidate reduced-form non-financial-corporate investment equation."""

    _finite(
        demand_growth,
        real_corporate_lending_rate,
        eu_fund_impulse,
        intercept,
        demand_sensitivity,
        rate_sensitivity,
        eu_fund_sensitivity,
    )
    return (
        intercept
        + demand_sensitivity * demand_growth
        - rate_sensitivity * real_corporate_lending_rate
        + eu_fund_sensitivity * eu_fund_impulse
    )


def aggregate_credit_growth(
    *,
    activity_growth: float,
    real_lending_rate: float,
    npl_ratio: float,
    capital_buffer: float,
    intercept: float,
    activity_sensitivity: float,
    rate_sensitivity: float,
    npl_sensitivity: float,
    capital_sensitivity: float,
) -> float:
    """Candidate aggregate bank-credit growth equation.

    Bank-level evidence does not by itself identify this aggregate relation; it
    remains a candidate until the Alpha 0.5 data/identifiability gates pass.
    """

    _finite(
        activity_growth,
        real_lending_rate,
        npl_ratio,
        capital_buffer,
        intercept,
        activity_sensitivity,
        rate_sensitivity,
        npl_sensitivity,
        capital_sensitivity,
    )
    return (
        intercept
        + activity_sensitivity * activity_growth
        - rate_sensitivity * real_lending_rate
        - npl_sensitivity * npl_ratio
        + capital_sensitivity * capital_buffer
    )


def sovereign_spread(
    *,
    debt_to_gdp: float,
    deficit_to_gdp: float,
    external_risk_proxy: float,
    intercept: float,
    debt_sensitivity: float,
    deficit_sensitivity: float,
    external_risk_sensitivity: float,
) -> float:
    """Candidate reduced-form sovereign-spread equation."""

    _finite(
        debt_to_gdp,
        deficit_to_gdp,
        external_risk_proxy,
        intercept,
        debt_sensitivity,
        deficit_sensitivity,
        external_risk_sensitivity,
    )
    return (
        intercept
        + debt_sensitivity * debt_to_gdp
        + deficit_sensitivity * deficit_to_gdp
        + external_risk_sensitivity * external_risk_proxy
    )


def fx_pass_through_inflation(
    *,
    baseline_inflation: float,
    depreciation_lags: tuple[float, ...],
    lag_weights: tuple[float, ...],
) -> float:
    """Candidate distributed-lag FX pass-through contribution to inflation.

    No historical pass-through coefficient is hard-coded because published
    Romanian evidence indicates regime dependence over time.
    """

    _finite(baseline_inflation, *depreciation_lags, *lag_weights)
    if len(depreciation_lags) != len(lag_weights) or not lag_weights:
        raise InvalidBehaviouralInput("depreciation_lags and lag_weights must be non-empty and equal length")
    return baseline_inflation + sum(change * weight for change, weight in zip(depreciation_lags, lag_weights))


def npl_ratio_change(
    *,
    output_growth: float,
    debt_service_burden: float,
    previous_npl_ratio: float,
    intercept: float,
    output_sensitivity: float,
    debt_service_sensitivity: float,
    persistence: float,
) -> float:
    """Candidate credit-risk/NPL change equation; not admitted to the core yet."""

    _finite(
        output_growth,
        debt_service_burden,
        previous_npl_ratio,
        intercept,
        output_sensitivity,
        debt_service_sensitivity,
    )
    _unit_interval(persistence, "persistence")
    return (
        intercept
        - output_sensitivity * output_growth
        + debt_service_sensitivity * debt_service_burden
        + persistence * previous_npl_ratio
    )
