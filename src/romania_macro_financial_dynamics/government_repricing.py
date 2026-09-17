"""Boundary-safe utilities for the Alpha 0.5.2 government repricing ledger."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping


class RepricingIdentifiabilityError(ValueError):
    """Raised when a repricing calculation would require unmatched or synthetic inputs."""


def _clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def load_ledger(path: str | Path) -> list[dict[str, str]]:
    """Load the audited ledger while preserving source blanks as missing values."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [{key: _clean(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def _as_float(row: Mapping[str, str], field: str) -> float | None:
    value = _clean(row.get(field))
    return None if value == "" else float(value)


def validate_no_synthetic_allocations(rows: Iterable[Mapping[str, str]]) -> None:
    """Fail loudly if a row claims any synthetic allocation."""
    for row in rows:
        if _clean(row.get("synthetic_allocation")).lower() not in {"false", "0", "no"}:
            raise RepricingIdentifiabilityError(
                f"Synthetic allocation is forbidden: {row.get('record_id', '<unknown>')}"
            )


def matched_repricing_rows(rows: Iterable[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Return only rows carrying the exact principal and old/new rate match required by the mechanism."""
    matched: list[Mapping[str, str]] = []
    for row in rows:
        opening = _as_float(row, "opening_outstanding_principal")
        repriced = _as_float(row, "principal_repriced")
        old_rate = _as_float(row, "old_effective_rate_pct")
        new_rate = _as_float(row, "new_or_marginal_rate_pct")
        if opening is None or repriced is None or old_rate is None:
            continue
        if repriced < 0 or opening <= 0 or repriced > opening:
            raise RepricingIdentifiabilityError(
                f"Invalid principal relationship in {row.get('record_id', '<unknown>')}"
            )
        if repriced > 0 and new_rate is None:
            continue
        matched.append(row)
    return matched


def ledger_diagnostics(rows: Iterable[Mapping[str, str]]) -> dict[str, object]:
    rows = list(rows)
    validate_no_synthetic_allocations(rows)
    currencies = sorted({_clean(row.get("currency")) for row in rows if _clean(row.get("currency"))})
    rate_types = sorted(
        {_clean(row.get("fixed_or_floating")) for row in rows if _clean(row.get("fixed_or_floating"))}
    )
    return {
        "rows": len(rows),
        "currencies": currencies,
        "rate_types_observed": rate_types,
        "rows_with_issue_size": sum(_as_float(row, "issued_principal") is not None for row in rows),
        "rows_with_announced_principal": sum(_as_float(row, "announced_principal") is not None for row in rows),
        "rows_with_opening_outstanding_principal": sum(
            _as_float(row, "opening_outstanding_principal") is not None for row in rows
        ),
        "rows_with_principal_repriced": sum(_as_float(row, "principal_repriced") is not None for row in rows),
        "rows_with_matched_repricing": len(matched_repricing_rows(rows)),
        "rows_with_contractual_refixing_date": sum(
            bool(_clean(row.get("contractual_refixing_date"))) for row in rows
        ),
    }


def reconstructed_effective_rate_pct(rows: Iterable[Mapping[str, str]]) -> float:
    """Reconstruct a same-currency portfolio rate from complete matched ledger blocks.

    The function deliberately refuses cross-currency aggregation and incomplete blocks.
    A row with zero repriced principal may omit ``new_or_marginal_rate_pct`` because its old
    rate remains applicable to the whole represented principal.
    """
    rows = list(rows)
    validate_no_synthetic_allocations(rows)
    if not rows:
        raise RepricingIdentifiabilityError("No ledger rows supplied")

    currencies = {_clean(row.get("currency")) for row in rows if _clean(row.get("currency"))}
    if len(currencies) != 1:
        raise RepricingIdentifiabilityError(
            "Cross-currency aggregation requires an explicit same-date valuation basis"
        )

    total_principal = 0.0
    total_interest = 0.0
    for row in rows:
        opening = _as_float(row, "opening_outstanding_principal")
        repriced = _as_float(row, "principal_repriced")
        old_rate = _as_float(row, "old_effective_rate_pct")
        new_rate = _as_float(row, "new_or_marginal_rate_pct")
        if opening is None or repriced is None or old_rate is None:
            raise RepricingIdentifiabilityError(
                f"Incomplete matched block: {row.get('record_id', '<unknown>')}"
            )
        if opening <= 0 or repriced < 0 or repriced > opening:
            raise RepricingIdentifiabilityError(
                f"Invalid principal relationship: {row.get('record_id', '<unknown>')}"
            )
        if repriced > 0 and new_rate is None:
            raise RepricingIdentifiabilityError(
                f"Missing new/reset rate: {row.get('record_id', '<unknown>')}"
            )
        effective_new_rate = old_rate if repriced == 0 else new_rate
        unchanged = opening - repriced
        total_interest += unchanged * old_rate / 100.0
        total_interest += repriced * float(effective_new_rate) / 100.0
        total_principal += opening

    return 100.0 * total_interest / total_principal
