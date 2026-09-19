"""Accounting-constrained System Dynamics primitives for the scientific core.

The module provides structure, conservation and time-step mechanics only.
Behavioural closure remains outside this stage: no consumption, investment,
credit, fiscal-reaction, policy-rate, FX or risk response function is silently
introduced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping

from .accounting import AccountingCell, INSTRUMENT_PRIORITY, SECTOR_IDS

DEFAULT_DT_YEARS = 0.25
MAX_EULER_DELAY_DT_FRACTION = 1.0 / 3.0


class IncompleteEmpiricalState(ValueError):
    """Raised when unresolved accounting data are passed into a numeric simulation."""


@dataclass(frozen=True, order=True)
class PositionKey:
    """One bilateral financial position: holder asset against issuer liability."""

    holder: str
    issuer: str
    instrument: str

    def __post_init__(self) -> None:
        if self.holder not in SECTOR_IDS:
            raise ValueError(f"Unknown holder sector: {self.holder}")
        if self.issuer not in SECTOR_IDS:
            raise ValueError(f"Unknown issuer sector: {self.issuer}")
        if self.instrument not in INSTRUMENT_PRIORITY:
            raise ValueError(f"Unknown instrument: {self.instrument}")


@dataclass(frozen=True)
class PositionChange:
    """Period changes expressed as amounts in the same currency unit as the stock."""

    transactions: float = 0.0
    revaluations: float = 0.0
    other_changes: float = 0.0

    @property
    def total(self) -> float:
        return self.transactions + self.revaluations + self.other_changes


def advance_position(opening: float, change: PositionChange) -> float:
    """Apply the canonical financial-account stock identity for one period."""

    values = (opening, change.transactions, change.revaluations, change.other_changes)
    if not all(isfinite(value) for value in values):
        raise ValueError("Dynamic position inputs must be finite")
    closing = opening + change.total
    if not isfinite(closing):
        raise ValueError("Dynamic position result must be finite")
    return closing


def rate_to_period_amount(rate_per_year: float, dt_years: float = DEFAULT_DT_YEARS) -> float:
    """Convert a currency/year flow rate to a currency amount over dt years."""

    if not isfinite(rate_per_year):
        raise ValueError("Flow rate must be finite")
    if not isfinite(dt_years) or dt_years <= 0:
        raise ValueError("dt_years must be finite and positive")
    return rate_per_year * dt_years


def advance_position_rates(
    opening: float,
    *,
    transaction_rate: float = 0.0,
    revaluation_rate: float = 0.0,
    other_change_rate: float = 0.0,
    dt_years: float = DEFAULT_DT_YEARS,
) -> float:
    """Advance a financial stock from rates while keeping units explicit."""

    return advance_position(
        opening,
        PositionChange(
            transactions=rate_to_period_amount(transaction_rate, dt_years),
            revaluations=rate_to_period_amount(revaluation_rate, dt_years),
            other_changes=rate_to_period_amount(other_change_rate, dt_years),
        ),
    )


def apply_period_changes(
    opening: Mapping[PositionKey, float],
    changes: Mapping[PositionKey, PositionChange],
) -> dict[PositionKey, float]:
    """Advance all explicitly represented bilateral positions by one period.

    A key absent from ``opening`` but explicitly present in ``changes`` starts at
    numeric zero. This API is for an already-initialized simulation state, not
    for raw empirical data. Use ``empirical_cells_to_state`` for the guarded
    bridge from the Accounting Spine.
    """

    keys = set(opening) | set(changes)
    result: dict[PositionKey, float] = {}
    for key in keys:
        opening_value = opening.get(key, 0.0)
        if not isfinite(opening_value):
            raise ValueError(f"Non-finite opening position for {key}")
        result[key] = advance_position(opening_value, changes.get(key, PositionChange()))
    return result


def sector_balance_sheets(
    positions: Mapping[PositionKey, float],
) -> dict[str, dict[str, float]]:
    """Derive sector assets, liabilities and net financial worth.

    Each bilateral position is represented once. The same value is an asset of
    the holder and a liability of the issuer, which enforces double-entry
    conservation structurally.
    """

    result = {
        sector: {"assets": 0.0, "liabilities": 0.0, "net_financial_worth": 0.0}
        for sector in SECTOR_IDS
    }
    for key, value in positions.items():
        if not isfinite(value):
            raise ValueError(f"Non-finite position for {key}")
        result[key.holder]["assets"] += value
        result[key.issuer]["liabilities"] += value

    for sector in SECTOR_IDS:
        row = result[sector]
        row["net_financial_worth"] = row["assets"] - row["liabilities"]
    return result


def system_net_financial_worth(positions: Mapping[PositionKey, float]) -> float:
    """Return the sum of sector net financial worth over the closed model boundary."""

    return sum(
        row["net_financial_worth"] for row in sector_balance_sheets(positions).values()
    )


def empirical_cells_to_state(cells: Iterable[AccountingCell]) -> dict[PositionKey, float]:
    """Bridge one complete observed/derived stock matrix into a numeric state.

    Unresolved or source-identified-only cells cause a hard failure. This keeps
    the dynamic layer from interpreting absence as zero. Duplicate matrix cells
    are also rejected so later entries cannot silently overwrite earlier ones.
    """

    cells = tuple(cells)
    if not cells:
        raise IncompleteEmpiricalState("No accounting cells supplied")
    if any(cell.measure != "stock" for cell in cells):
        raise ValueError("Dynamic initial positions must come from stock cells")
    instruments = {cell.instrument for cell in cells}
    if len(instruments) != 1:
        raise ValueError("Bridge one instrument matrix at a time")

    expected = {(holder, issuer) for holder in SECTOR_IDS for issuer in SECTOR_IDS}
    addresses = [(cell.holder, cell.issuer) for cell in cells]
    observed = set(addresses)
    if len(cells) != len(expected) or len(observed) != len(addresses):
        raise IncompleteEmpiricalState("Matrix must contain exactly one cell for every holder×issuer address")
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise IncompleteEmpiricalState(f"Matrix address space mismatch; missing={missing}, extra={extra}")

    unresolved = [
        cell
        for cell in cells
        if cell.status not in {"OBSERVED", "DERIVED", "NOT_APPLICABLE"}
    ]
    if unresolved:
        raise IncompleteEmpiricalState(
            f"Cannot initialize numeric dynamics with {len(unresolved)} unresolved cells"
        )

    state: dict[PositionKey, float] = {}
    for cell in cells:
        value = 0.0 if cell.status == "NOT_APPLICABLE" else cell.value
        if value is None or not isfinite(value):
            raise IncompleteEmpiricalState(f"Cell {cell.holder}->{cell.issuer} lacks a finite value")
        state[PositionKey(cell.holder, cell.issuer, cell.instrument)] = value
    return state


def euler_step(value: float, derivative_per_year: float, dt_years: float) -> float:
    """One explicit-Euler step for a scalar stock."""

    return advance_position_rates(
        value,
        transaction_rate=derivative_per_year,
        dt_years=dt_years,
    )


def first_order_delay_derivative(input_value: float, delayed_value: float, tau_years: float) -> float:
    """Standard first-order information/material delay derivative.

    Input and delayed value share a unit; the result has that unit per year.
    """

    if not all(isfinite(value) for value in (input_value, delayed_value, tau_years)):
        raise ValueError("Delay inputs must be finite")
    if tau_years <= 0:
        raise ValueError("tau_years must be positive")
    return (input_value - delayed_value) / tau_years


def first_order_delay_timestep_ratio(dt_years: float, tau_years: float) -> float:
    """Return dt/tau for explicit-Euler first-order delay adequacy checks."""

    if not all(isfinite(value) for value in (dt_years, tau_years)):
        raise ValueError("Delay time-step inputs must be finite")
    if dt_years <= 0:
        raise ValueError("dt_years must be positive")
    if tau_years <= 0:
        raise ValueError("tau_years must be positive")
    return dt_years / tau_years


def first_order_delay_timestep_is_adequate(
    dt_years: float,
    tau_years: float,
    *,
    max_fraction: float = MAX_EULER_DELAY_DT_FRACTION,
) -> bool:
    """Conservative explicit-Euler gate for a first-order delay.

    RMD uses a strict dt/tau < 1/3 reference rule. This is a numerical
    adequacy guard, not an empirical parameter assumption.
    """

    if not isfinite(max_fraction) or max_fraction <= 0:
        raise ValueError("max_fraction must be finite and positive")
    return first_order_delay_timestep_ratio(dt_years, tau_years) < max_fraction


def simulate_first_order_delay_euler(
    *,
    initial: float,
    input_value: float,
    tau_years: float,
    horizon_years: float,
    dt_years: float = DEFAULT_DT_YEARS,
) -> float:
    """Integrate a constant-input first-order delay for structural tests.

    The reference helper rejects a time step that violates the conservative
    RMD Euler delay rule instead of returning a numerically unstable or
    qualitatively distorted path.
    """

    if horizon_years < 0 or not isfinite(horizon_years):
        raise ValueError("horizon_years must be finite and non-negative")
    if dt_years <= 0 or not isfinite(dt_years):
        raise ValueError("dt_years must be finite and positive")
    if not first_order_delay_timestep_is_adequate(dt_years, tau_years):
        raise ValueError(
            "Explicit-Euler delay time step must satisfy dt/tau < 1/3 "
            "for the RMD reference structural simulation"
        )
    if horizon_years == 0:
        return initial

    steps = round(horizon_years / dt_years)
    if steps <= 0 or abs(steps * dt_years - horizon_years) > 1e-12:
        raise ValueError("horizon_years must be an integer multiple of dt_years")

    value = initial
    for _ in range(steps):
        derivative = first_order_delay_derivative(input_value, value, tau_years)
        value = euler_step(value, derivative, dt_years)
    return value


def safe_ratio(numerator: float, denominator: float) -> float | None:
    """Dimensionless auxiliary with explicit zero-denominator semantics."""

    if not all(isfinite(value) for value in (numerator, denominator)):
        raise ValueError("Ratio inputs must be finite")
    if denominator == 0:
        return None
    return numerator / denominator
