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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

OUT = Path(os.environ.get("F21_AUDIT_OUT", "f21_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F21 currency audit)"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
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


def key(area: str, ref: str, cp: str, entry: str, measure: str) -> str:
    return ".".join(
        (
            "Q", "N", "RO", area, ref, cp, "N", entry, measure, "F21",
            "T", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def formula(holder: str, issuer: str, measure: str) -> tuple[Term, ...]:
    if holder == "X" and issuer == "X":
        return ()
    if holder == "X":
        return tuple(
            Term(coeff, key("W1", issuer_code, "S1", "L", measure))
            for issuer_code, coeff in sector_terms(issuer)
        )
    if issuer == "X":
        return tuple(
            Term(coeff, key("W1", holder_code, "S1", "A", measure))
            for holder_code, coeff in sector_terms(holder)
        )

    terms: list[Term] = []
    for issuer_code, issuer_coeff in sector_terms(issuer):
        for holder_code, holder_coeff in sector_terms(holder):
            terms.append(
                Term(
                    issuer_coeff * holder_coeff,
                    key("W2", issuer_code, holder_code, "L", measure),
                )
            )
    return tuple(terms)


def aggregate_terms(sector: str, entry: str, measure: str) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key("W0", code, "S1", entry, measure))
        for code, coeff in sector_terms(sector)
    )


def total_economy_term(area: str, entry: str, measure: str) -> tuple[Term, ...]:
    return (Term(1.0, key(area, "S1", "S1", entry, measure)),)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(series_key: str) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {"startPeriod": "2025-Q1", "endPeriod": "2025-Q4", "format": "csvdata"}
    )
    url = f"{API}{series_key}?{query}"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"}
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
            status = int(response.status)
            headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = int(exc.code)
        headers = dict(exc.headers.items())
    except urllib.error.URLError as exc:
        return {
            "key": series_key,
            "status": "NETWORK_ERROR",
            "error": str(exc),
            "rows": [],
        }

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

    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    parsed = []
    for row in rows:
        period = row.get("TIME_PERIOD")
        value = row.get("OBS_VALUE")
        if not period or value in (None, ""):
            continue
        try:
            numeric = float(value)
        except ValueError:
            continue
        parsed.append(
            {
                "period": period,
                "value": numeric,
                "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
                "unit_mult": row.get("UNIT_MULT"),
                "instrument": row.get("INSTR_ASSET"),
                "entry": row.get("ACCOUNTING_ENTRY"),
                "measure": row.get("STO"),
                "counterpart_area": row.get("COUNTERPART_AREA"),
                "reference_sector": row.get("REF_SECTOR"),
                "counterpart_sector": row.get("COUNTERPART_SECTOR"),
            }
        )
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def values(series: dict[str, object], measure: str) -> list[float] | None:
    needed = (
        ["2025-Q4"]
        if measure == "LE"
        else ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
    )
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != "F21"
        for row in rows
    ):
        return None
    mapping = {str(row["period"]): float(row["value"]) for row in rows}
    if not all(p in mapping and math.isfinite(mapping[p]) for p in needed):
        return None
    return [mapping[p] for p in needed]


def evaluate(
    terms: tuple[Term, ...],
    series_by_key: dict[str, dict[str, object]],
    measure: str,
) -> tuple[float | None, list[dict[str, object]]]:
    if not terms:
        return None, []
    total = 0.0
    detail = []
    for term in terms:
        vals = values(series_by_key[term.key], measure)
        detail.append(
            {
                "coefficient": term.coefficient,
                "key": term.key,
                "usable": vals is not None,
                "values": vals,
            }
        )
        if vals is None:
            return None, detail
        component = vals[0] if measure == "LE" else sum(vals)
        total += term.coefficient * component
    return total, detail


def main() -> None:
    plans = []
    required: set[str] = set()
    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                terms = formula(holder, issuer, measure)
                plans.append((measure, holder, issuer, terms))
                required.update(term.key for term in terms)

    controls = []
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for kind, entry in (("holder_total", "A"), ("issuer_total", "L")):
                terms = aggregate_terms(sector, entry, measure)
                controls.append((measure, kind, sector, terms))
                required.update(term.key for term in terms)

    economy_controls = []
    for measure in ("LE", "F"):
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                terms = total_economy_term(area, entry, measure)
                economy_controls.append((measure, area, entry, terms))
                required.update(term.key for term in terms)

    series_by_key = {}
    ordered_keys = sorted(required)
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_key = {
            executor.submit(fetch, series_key): series_key
            for series_key in ordered_keys
        }
        completed = 0
        for future in as_completed(future_to_key):
            series_key = future_to_key[future]
            series_by_key[series_key] = future.result()
            completed += 1
            print(f"[{completed}/{len(ordered_keys)}] {series_key}", flush=True)

    cells = []
    for measure, holder, issuer, terms in plans:
        value, detail = evaluate(terms, series_by_key, measure)
        if holder == "X" and issuer == "X":
            status = "OUTSIDE_BOUNDARY_NOT_APPLICABLE"
        elif value is None:
            status = "UNRESOLVED_SOURCE_COVERAGE"
        else:
            status = "OBSERVABLE_OR_EXACT_DERIVATION"
        cells.append(
            {
                "measure": "stock" if measure == "LE" else "flow",
                "holder": holder,
                "issuer": issuer,
                "status": status,
                "value_million_RON": value,
                "terms": detail,
            }
        )

    reconciliation = []
    for measure, kind, sector, terms in controls:
        official, detail = evaluate(terms, series_by_key, measure)
        label = "stock" if measure == "LE" else "flow"
        related = [
            c
            for c in cells
            if c["measure"] == label
            and (
                c["holder"] == sector
                if kind == "holder_total"
                else c["issuer"] == sector
            )
            and not (c["holder"] == "X" and c["issuer"] == "X")
        ]
        complete = all(
            c["status"] != "UNRESOLVED_SOURCE_COVERAGE" for c in related
        )
        bilateral = (
            sum(float(c["value_million_RON"]) for c in related)
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
        reconciliation.append(
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

    total_controls = []
    for measure, area, entry, terms in economy_controls:
        value, detail = evaluate(terms, series_by_key, measure)
        total_controls.append(
            {
                "measure": "stock" if measure == "LE" else "flow",
                "counterpart_area": area,
                "entry": entry,
                "value_million_RON": value,
                "status": "AVAILABLE" if value is not None else "UNAVAILABLE",
                "terms": detail,
            }
        )

    report = {
        "audit_version": "0.1",
        "instrument": "F21",
        "benchmark_changed": False,
        "total_F2_materialization_allowed": False,
        "F2M_component_changed": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": {},
        "cell_status_counts": {},
        "reconciliation_status_counts": {},
        "cells": cells,
        "aggregate_reconciliation": reconciliation,
        "total_economy_controls": total_controls,
        "rule": (
            "Coverage only. No missing bilateral F21 cell is converted to zero, "
            "and no aggregate currency control is allocated across holder or issuer sectors."
        ),
    }
    for series in series_by_key.values():
        status = str(series.get("status"))
        report["series_status_counts"][status] = (
            report["series_status_counts"].get(status, 0) + 1
        )
    for cell in cells:
        status = cell["status"]
        report["cell_status_counts"][status] = (
            report["cell_status_counts"].get(status, 0) + 1
        )
    for item in reconciliation:
        status = item["status"]
        report["reconciliation_status_counts"][status] = (
            report["reconciliation_status_counts"].get(status, 0) + 1
        )

    (OUT / "f21_currency_coverage_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_requested": report["series_requested"],
                "series_status_counts": report["series_status_counts"],
                "cell_status_counts": report["cell_status_counts"],
                "reconciliation_status_counts": report["reconciliation_status_counts"],
                "total_economy_controls": total_controls,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
