"""Accounting/SFC spine primitives for the scientific core.

This module deliberately separates observed values, derived values, identified
source series and unresolved cells. Missing bilateral data are never coerced to
zero and are never silently imputed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

SECTOR_IDS = ("H", "C", "F", "G", "X", "BNR")
INSTRUMENT_PRIORITY = ("F3", "F2", "F4", "F8", "F5", "F6", "F7")
MEASURES = ("stock", "flow")
CELL_STATUSES = (
    "TBD",
    "SOURCE_SERIES_IDENTIFIED",
    "OBSERVED",
    "DERIVED",
    "NOT_APPLICABLE",
)


@dataclass(frozen=True)
class AccountingCell:
    """One holder-by-issuer matrix cell."""

    holder: str
    issuer: str
    instrument: str
    measure: str
    status: str
    value: float | None = None
    unit: str = "million_RON"
    source_series_key: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.holder not in SECTOR_IDS:
            raise ValueError(f"Unknown holder sector: {self.holder}")
        if self.issuer not in SECTOR_IDS:
            raise ValueError(f"Unknown issuer sector: {self.issuer}")
        if self.instrument not in INSTRUMENT_PRIORITY:
            raise ValueError(f"Unknown accounting instrument: {self.instrument}")
        if self.measure not in MEASURES:
            raise ValueError(f"Unknown measure: {self.measure}")
        if self.status not in CELL_STATUSES:
            raise ValueError(f"Unknown cell status: {self.status}")
        if self.status in {"TBD", "SOURCE_SERIES_IDENTIFIED", "NOT_APPLICABLE"} and self.value is not None:
            raise ValueError(f"Status {self.status} must not carry a numeric value")
        if self.status in {"OBSERVED", "DERIVED"} and self.value is None:
            raise ValueError(f"Status {self.status} requires a numeric value")
        if self.status == "SOURCE_SERIES_IDENTIFIED" and not self.source_series_key:
            raise ValueError("SOURCE_SERIES_IDENTIFIED requires source_series_key")


def expand_matrix(
    instrument: str,
    measure: str,
    matrix_spec: Mapping[str, Any],
) -> tuple[AccountingCell, ...]:
    """Expand a compact matrix specification into all 36 bilateral cells.

    A matrix has an explicit default cell rule plus zero or more overrides. This
    makes unresolved cells machine-explicit without storing 36 repetitive JSON
    objects per matrix.
    """

    if instrument not in INSTRUMENT_PRIORITY:
        raise ValueError(f"Unknown accounting instrument: {instrument}")
    if measure not in MEASURES:
        raise ValueError(f"Unknown measure: {measure}")

    default = matrix_spec.get("default")
    if not isinstance(default, Mapping):
        raise ValueError("matrix_spec.default must be an object")

    overrides: dict[tuple[str, str], Mapping[str, Any]] = {}
    for raw in matrix_spec.get("overrides", []):
        key = (raw["holder"], raw["issuer"])
        if key in overrides:
            raise ValueError(f"Duplicate override for {key[0]}->{key[1]}")
        overrides[key] = raw

    cells: list[AccountingCell] = []
    for holder in SECTOR_IDS:
        for issuer in SECTOR_IDS:
            override = overrides.get((holder, issuer), {})
            cell = AccountingCell(
                holder=holder,
                issuer=issuer,
                instrument=instrument,
                measure=measure,
                status=override.get("status", default.get("status", "TBD")),
                value=override.get("value", default.get("value")),
                unit=override.get("unit", default.get("unit", "million_RON")),
                source_series_key=override.get("source_series_key"),
                note=override.get("note"),
            )
            cells.append(cell)

    if len(cells) != 36:
        raise AssertionError("A canonical bilateral matrix must contain 36 cells")
    return tuple(cells)


def observed_sum(cells: Iterable[AccountingCell]) -> float | None:
    """Return a sum only when every included cell is numeric.

    This intentionally refuses partial sums that could be misread as a complete
    accounting total.
    """

    cells = tuple(cells)
    if not cells:
        return 0.0
    if any(cell.status not in {"OBSERVED", "DERIVED", "NOT_APPLICABLE"} for cell in cells):
        return None
    return sum(cell.value or 0.0 for cell in cells)


def reconciliation_residual(asset_total: float | None, liability_total: float | None) -> float | None:
    """Return assets minus liabilities when both sides are available."""

    if asset_total is None or liability_total is None:
        return None
    return asset_total - liability_total


def b9f(net_acquisition_assets: float | None, net_incurrence_liabilities: float | None) -> float | None:
    """Financial-account net lending(+)/net borrowing(-): assets minus liabilities."""

    if net_acquisition_assets is None or net_incurrence_liabilities is None:
        return None
    return net_acquisition_assets - net_incurrence_liabilities


def validate_benchmark_spec(spec: Mapping[str, Any]) -> None:
    """Validate the benchmark contract without pretending data completeness."""

    benchmark = spec.get("benchmark", {})
    if benchmark.get("stock_date") != "2025-12-31":
        raise ValueError("Accounting benchmark stock date must be 2025-12-31")
    if benchmark.get("flow_period") != "2025-01-01/2025-12-31":
        raise ValueError("Accounting benchmark flow period must cover calendar 2025")

    axes = spec.get("matrix_axes", {})
    if tuple(axes.get("holders", ())) != SECTOR_IDS:
        raise ValueError("Holder axis must match canonical sector order")
    if tuple(axes.get("issuers", ())) != SECTOR_IDS:
        raise ValueError("Issuer axis must match canonical sector order")
    if tuple(spec.get("instrument_priority", ())) != INSTRUMENT_PRIORITY:
        raise ValueError("Instrument priority drifted from the 0.2 roadmap")

    matrices = spec.get("matrices", {})
    if set(matrices) != set(INSTRUMENT_PRIORITY):
        raise ValueError("All canonical accounting instruments must have a matrix spec")

    for instrument in INSTRUMENT_PRIORITY:
        instrument_spec = matrices[instrument]
        for measure in MEASURES:
            matrix_spec = instrument_spec.get(measure)
            if not isinstance(matrix_spec, Mapping):
                raise ValueError(f"Missing {instrument}.{measure} matrix")
            cells = expand_matrix(instrument, measure, matrix_spec)
            if len(cells) != 36:
                raise AssertionError("Matrix expansion failure")

    closure = spec.get("closure", {})
    if closure.get("unresolved_cells_are_not_imputed") is not True:
        raise ValueError("Benchmark must prohibit silent imputation")
