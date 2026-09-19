from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

OUT = Path(os.environ.get("F7_AUDIT_OUT", "f7_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F7 coverage audit)"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
INSTRUMENT = "F7"
TOL = 0.1


@dataclass(frozen=True)
class Term:
    coefficient: float
    key: str


def sector_terms(sector: str) -> tuple[tuple[str, float], ...]:
    if sector in DIRECT:
        return ((DIRECT[sector], 1.0),)
    if sector in COMPOSITE:
        return COMPOSITE[sector]
    raise ValueError(sector)


def key(
    area: str,
    ref: str,
    counterpart: str,
    entry: str,
    measure: str,
) -> str:
    return ".".join(
        (
            "Q",
            "N",
            "RO",
            area,
            ref,
            counterpart,
            "N",
            entry,
            measure,
            INSTRUMENT,
            "T",
            "_Z",
            "XDC",
            "_T",
            "S",
            "V",
            "N",
            "_T",
        )
    )


def candidate_terms(
    holder: str,
    issuer: str,
    measure: str,
) -> dict[str, tuple[Term, ...]]:
    if holder == "X" and issuer == "X":
        return {}

    if holder == "X":
        return {
            "issuer_liability_W1": tuple(
                Term(coefficient, key("W1", code, "S1", "L", measure))
                for code, coefficient in sector_terms(issuer)
            )
        }

    if issuer == "X":
        return {
            "holder_asset_W1": tuple(
                Term(coefficient, key("W1", code, "S1", "A", measure))
                for code, coefficient in sector_terms(holder)
            )
        }

    asset_terms: list[Term] = []
    liability_terms: list[Term] = []
    for holder_code, holder_coefficient in sector_terms(holder):
        for issuer_code, issuer_coefficient in sector_terms(issuer):
            coefficient = holder_coefficient * issuer_coefficient
            asset_terms.append(
                Term(
                    coefficient,
                    key("W2", holder_code, issuer_code, "A", measure),
                )
            )
            liability_terms.append(
                Term(
                    coefficient,
                    key("W2", issuer_code, holder_code, "L", measure),
                )
            )
    return {
        "holder_asset_W2": tuple(asset_terms),
        "issuer_liability_W2": tuple(liability_terms),
    }


def aggregate_terms(
    sector: str,
    entry: str,
    measure: str,
) -> tuple[Term, ...]:
    return tuple(
        Term(coefficient, key("W0", code, "S1", entry, measure))
        for code, coefficient in sector_terms(sector)
    )


def total_terms(
    area: str,
    entry: str,
    measure: str,
) -> tuple[Term, ...]:
    return (Term(1.0, key(area, "S1", "S1", entry, measure)),)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(series_key: str) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {
            "startPeriod": "2025-Q1",
            "endPeriod": "2025-Q4",
            "format": "csvdata",
        }
    )
    url = f"{API}{series_key}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv",
        },
    )

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                status = int(response.status)
                headers = dict(response.headers.items())
            break
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
            headers = dict(exc.headers.items())
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                return {
                    "key": series_key,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "rows": [],
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_path = OUT / "raw" / f"{sha256(series_key.encode())[:16]}.raw"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": series_key,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "content_type": headers.get("Content-Type"),
        "rows": [],
    }

    if status != 200:
        result["status"] = "HTTP_ERROR"
        return result

    parsed: list[dict[str, object]] = []
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        period = row.get("TIME_PERIOD")
        raw_value = row.get("OBS_VALUE")
        if not period or raw_value in (None, ""):
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        parsed.append(
            {
                "period": period,
                "value": value,
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "instrument": row.get("INSTR_ASSET"),
                "entry": row.get("ACCOUNTING_ENTRY"),
                "measure": row.get("STO"),
                "maturity": row.get("MATURITY"),
                "custom_breakdown": row.get("CUSTOM_BREAKDOWN"),
            }
        )

    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def usable_values(
    series: dict[str, object],
    measure: str,
) -> list[float] | None:
    if series.get("status") != "AVAILABLE":
        return None

    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != INSTRUMENT
        or row.get("maturity") != "T"
        for row in rows
    ):
        return None

    needed = (
        ("2025-Q4",)
        if measure == "LE"
        else ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
    )
    mapping = {
        str(row["period"]): float(row["value"])
        for row in rows
    }
    if not all(
        period in mapping and math.isfinite(mapping[period])
        for period in needed
    ):
        return None
    return [mapping[period] for period in needed]


def evaluate(
    terms: tuple[Term, ...],
    series_by_key: dict[str, dict[str, object]],
    measure: str,
) -> tuple[float | None, list[dict[str, object]]]:
    total = 0.0
    detail: list[dict[str, object]] = []

    for term in terms:
        values = usable_values(series_by_key[term.key], measure)
        detail.append(
            {
                "coefficient": term.coefficient,
                "key": term.key,
                "usable": values is not None,
                "values": values,
            }
        )
        if values is None:
            return None, detail
        period_value = values[0] if measure == "LE" else sum(values)
        total += term.coefficient * period_value

    if not math.isfinite(total):
        return None, detail
    return total, detail


def main() -> None:
    cell_plans: list[
        tuple[str, str, str, dict[str, tuple[Term, ...]]]
    ] = []
    required: set[str] = set()

    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                formulas = candidate_terms(holder, issuer, measure)
                cell_plans.append((measure, holder, issuer, formulas))
                for terms in formulas.values():
                    required.update(term.key for term in terms)

    aggregate_plans: list[
        tuple[str, str, str, tuple[Term, ...]]
    ] = []
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for kind, entry in (
                ("holder_total", "A"),
                ("issuer_total", "L"),
            ):
                terms = aggregate_terms(sector, entry, measure)
                aggregate_plans.append((measure, kind, sector, terms))
                required.update(term.key for term in terms)

    total_plans: list[
        tuple[str, str, str, tuple[Term, ...]]
    ] = []
    for measure in ("LE", "F"):
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                terms = total_terms(area, entry, measure)
                total_plans.append((measure, area, entry, terms))
                required.update(term.key for term in terms)

    series_by_key: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(fetch, series_key): series_key
            for series_key in sorted(required)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            series_key = futures[future]
            series_by_key[series_key] = future.result()
            print(
                f"[{index}/{len(futures)}] {series_key}",
                flush=True,
            )

    cells: list[dict[str, object]] = []
    for measure, holder, issuer, formulas in cell_plans:
        label = "stock" if measure == "LE" else "flow"

        if holder == "X" and issuer == "X":
            cells.append(
                {
                    "measure": label,
                    "holder": holder,
                    "issuer": issuer,
                    "status": "OUTSIDE_BOUNDARY_NOT_APPLICABLE",
                    "value_million_RON": None,
                    "selected_orientation": None,
                    "orientation_results": {},
                }
            )
            continue

        orientation_results: dict[str, object] = {}
        usable: dict[str, float] = {}

        for orientation, terms in formulas.items():
            value, detail = evaluate(terms, series_by_key, measure)
            orientation_results[orientation] = {
                "value_million_RON": value,
                "terms": detail,
            }
            if value is not None:
                usable[orientation] = float(value)

        if not usable:
            status = "UNRESOLVED_SOURCE_COVERAGE"
            value = None
            selected = None
        else:
            values = list(usable.values())
            if len(values) > 1 and max(values) - min(values) > TOL:
                status = "ORIENTATION_CONFLICT"
                value = None
                selected = None
            else:
                status = "OBSERVABLE_OR_EXACT_SECTOR_DERIVATION"
                selected = (
                    "holder_asset_W2"
                    if "holder_asset_W2" in usable
                    else next(iter(usable))
                )
                value = usable[selected]

        cells.append(
            {
                "measure": label,
                "holder": holder,
                "issuer": issuer,
                "status": status,
                "value_million_RON": value,
                "selected_orientation": selected,
                "orientation_results": orientation_results,
            }
        )

    aggregate_controls: list[dict[str, object]] = []
    for measure, kind, sector, terms in aggregate_plans:
        label = "stock" if measure == "LE" else "flow"
        official, detail = evaluate(terms, series_by_key, measure)
        related = [
            cell
            for cell in cells
            if cell["measure"] == label
            and (
                cell["holder"] == sector
                if kind == "holder_total"
                else cell["issuer"] == sector
            )
            and cell["status"] != "OUTSIDE_BOUNDARY_NOT_APPLICABLE"
        ]
        complete = all(
            cell["status"] == "OBSERVABLE_OR_EXACT_SECTOR_DERIVATION"
            for cell in related
        )
        bilateral = (
            sum(float(cell["value_million_RON"]) for cell in related)
            if complete
            else None
        )
        residual = (
            None
            if official is None or bilateral is None
            else bilateral - float(official)
        )

        if official is None:
            status = "CONTROL_UNAVAILABLE"
        elif not complete:
            status = "BILATERAL_COVERAGE_INCOMPLETE"
        elif abs(float(residual)) <= TOL:
            status = "PASS"
        else:
            status = "FAIL"

        aggregate_controls.append(
            {
                "measure": label,
                "kind": kind,
                "sector": sector,
                "bilateral_complete": complete,
                "bilateral_sum_million_RON": bilateral,
                "official_aggregate_million_RON": official,
                "residual_million_RON": residual,
                "status": status,
                "terms": detail,
            }
        )

    total_controls: list[dict[str, object]] = []
    for measure, area, entry, terms in total_plans:
        value, detail = evaluate(terms, series_by_key, measure)
        total_controls.append(
            {
                "measure": "stock" if measure == "LE" else "flow",
                "area": area,
                "entry": entry,
                "instrument": INSTRUMENT,
                "value_million_RON": value,
                "status": "AVAILABLE" if value is not None else "UNAVAILABLE",
                "nonzero_above_reconciliation_tolerance": (
                    None if value is None else abs(float(value)) > TOL
                ),
                "terms": detail,
            }
        )

    available_scale = [
        float(control["value_million_RON"])
        for control in total_controls
        if control["value_million_RON"] is not None
    ]
    if not available_scale:
        scale_status = "NO_USABLE_TOTAL_ECONOMY_SCALE_CONTROLS"
    elif any(abs(value) > TOL for value in available_scale):
        scale_status = "NONZERO_AGGREGATE_F7_EVIDENCE"
    else:
        scale_status = "AVAILABLE_AGGREGATES_WITHIN_RECONCILIATION_TOLERANCE_OF_ZERO"

    series_manifest = []
    for series_key in sorted(series_by_key):
        source = series_by_key[series_key]
        series_manifest.append(
            {
                key: source.get(key)
                for key in (
                    "key",
                    "url",
                    "status",
                    "http_status",
                    "raw_path",
                    "raw_sha256",
                    "raw_bytes",
                    "content_type",
                    "error",
                )
                if key in source
            }
        )

    report = {
        "audit_version": "0.1",
        "instrument": INSTRUMENT,
        "phase": "source-coverage and scale screening",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": dict(
            Counter(
                str(source.get("status"))
                for source in series_by_key.values()
            )
        ),
        "cell_status_counts": dict(
            Counter(str(cell["status"]) for cell in cells)
        ),
        "aggregate_reconciliation_status_counts": dict(
            Counter(str(item["status"]) for item in aggregate_controls)
        ),
        "network_errors_present": any(
            source.get("status") == "NETWORK_ERROR"
            for source in series_by_key.values()
        ),
        "scale_screening": {
            "status": scale_status,
            "materiality_verdict": "NOT_ASSIGNED_IN_PHASE_A",
            "rule": (
                "Aggregate magnitudes are retained as scale evidence only. "
                "No materiality threshold is invented, and zero/small aggregate "
                "values do not create bilateral zeros or justify excluding F7."
            ),
        },
        "cells": cells,
        "aggregate_reconciliation": aggregate_controls,
        "total_economy_controls": total_controls,
        "series_manifest": series_manifest,
        "rule": (
            "Coverage only. Missing source series remain unresolved; no missing "
            "value becomes zero, no aggregate is distributed across counterparties, "
            "and no behavioural status changes."
        ),
    }

    output = OUT / "f7_financial_derivatives_coverage_audit.json"
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with (OUT / "f7_cell_summary.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "measure",
                "holder",
                "issuer",
                "status",
                "value_million_RON",
                "selected_orientation",
            ],
        )
        writer.writeheader()
        for cell in cells:
            writer.writerow(
                {
                    field: cell.get(field)
                    for field in writer.fieldnames
                }
            )

    print(
        json.dumps(
            {
                "series_requested": report["series_requested"],
                "series_status_counts": report["series_status_counts"],
                "cell_status_counts": report["cell_status_counts"],
                "aggregate_reconciliation_status_counts":
                    report["aggregate_reconciliation_status_counts"],
                "network_errors_present": report["network_errors_present"],
                "scale_screening": report["scale_screening"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
