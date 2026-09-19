"""Frozen monthly FX-inflation transformation/design primitives.

This module implements only the definitions preregistered on 2026-09-19.
It performs no coefficient estimation and has no function that opens the
2021-01..2026-06 final-evaluation window.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Sequence


def month_index(period: str) -> int:
    year_text, month_text = period.split("-", 1)
    year = int(year_text)
    month = int(month_text)
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {period!r}")
    return year * 12 + month - 1


def period_from_index(index: int) -> str:
    year, zero_month = divmod(index, 12)
    return f"{year:04d}-{zero_month + 1:02d}"


def read_level_records(
    path: Path,
    *,
    max_period: str,
) -> list[dict[str, float | str]]:
    records: list[dict[str, float | str]] = []
    maximum = month_index(max_period)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            period = str(row["period"])
            idx = month_index(period)
            if idx > maximum:
                break
            if row["source_completeness"] != "COMPLETE_LEVELS_ONLY":
                raise ValueError(f"incomplete source row: {period}")
            values = {
                "period": period,
                "fx": float(row["ron_per_eur_monthly_average"]),
                "hicp": float(row["hicp_total_2025_100"]),
                "uvi": float(row["import_uvi_total_world_2021_100"]),
            }
            if not all(
                math.isfinite(float(values[key])) and float(values[key]) > 0
                for key in ("fx", "hicp", "uvi")
            ):
                raise ValueError(f"non-positive/non-finite source level: {period}")
            records.append(values)
    if not records:
        raise ValueError("no source rows loaded")
    indices = [month_index(str(row["period"])) for row in records]
    if len(indices) != len(set(indices)):
        raise ValueError("duplicate monthly periods")
    for left, right in zip(indices, indices[1:]):
        if right != left + 1:
            raise ValueError(
                f"monthly source history is not contiguous: "
                f"{period_from_index(left)} -> {period_from_index(right)}"
            )
    return records


def log_change(current: float, previous: float) -> float:
    current = float(current)
    previous = float(previous)
    if (
        not math.isfinite(current)
        or not math.isfinite(previous)
        or current <= 0
        or previous <= 0
    ):
        raise ValueError("log-change inputs must be positive and finite")
    return 100.0 * (math.log(current) - math.log(previous))


def transformed_months(
    records: Sequence[dict[str, float | str]],
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for previous, current in zip(records, records[1:]):
        p0 = str(previous["period"])
        p1 = str(current["period"])
        if month_index(p1) != month_index(p0) + 1:
            raise ValueError(f"non-contiguous transform pair: {p0}, {p1}")
        result[p1] = {
            "pi": log_change(current["hicp"], previous["hicp"]),
            "de": log_change(current["fx"], previous["fx"]),
            "dpstar": log_change(current["uvi"], previous["uvi"]),
        }
    return result


def _mean_lags(
    transformed: dict[str, dict[str, float]],
    period: str,
    field: str,
    lags: Sequence[int],
) -> float:
    current = month_index(period)
    values = []
    for lag in lags:
        key = period_from_index(current - int(lag))
        if key not in transformed:
            raise ValueError(f"missing {field} lag {lag} for {period}")
        values.append(float(transformed[key][field]))
    return sum(values) / len(values)


def calendar_month_dummies(period: str) -> dict[str, float]:
    month = int(period[5:7])
    return {
        f"month_{m:02d}": 1.0 if month == m else 0.0
        for m in range(2, 13)
    }


def build_design_rows(
    records: Sequence[dict[str, float | str]],
    *,
    first_target: str = "2005-08",
    last_target: str = "2020-12",
) -> list[dict[str, float | str]]:
    transformed = transformed_months(records)
    start = month_index(first_target)
    end = month_index(last_target)
    rows: list[dict[str, float | str]] = []

    for idx in range(start, end + 1):
        period = period_from_index(idx)
        if period not in transformed:
            raise ValueError(f"missing transformed target month: {period}")
        row: dict[str, float | str] = {
            "period": period,
            "y": transformed[period]["pi"],
            "pi_lag1": _mean_lags(
                transformed, period, "pi", [1]
            ),
            "pi_lag2": _mean_lags(
                transformed, period, "pi", [2]
            ),
            "dpstar_0": _mean_lags(
                transformed, period, "dpstar", [0]
            ),
            "dpstar_1_3_mean": _mean_lags(
                transformed, period, "dpstar", [1, 2, 3]
            ),
            "de_0": _mean_lags(
                transformed, period, "de", [0]
            ),
            "de_1_3_mean": _mean_lags(
                transformed, period, "de", [1, 2, 3]
            ),
            "de_4_6_mean": _mean_lags(
                transformed, period, "de", [4, 5, 6]
            ),
            "de_7_12_mean": _mean_lags(
                transformed, period, "de", [7, 8, 9, 10, 11, 12]
            ),
        }
        row.update(calendar_month_dummies(period))
        if not all(
            math.isfinite(float(value))
            for key, value in row.items()
            if key != "period"
        ):
            raise ValueError(f"non-finite design value at {period}")
        rows.append(row)
    return rows


def rows_in_window(
    rows: Sequence[dict[str, float | str]],
    start: str,
    end: str,
) -> list[dict[str, float | str]]:
    lo = month_index(start)
    hi = month_index(end)
    return [
        row
        for row in rows
        if lo <= month_index(str(row["period"])) <= hi
    ]
