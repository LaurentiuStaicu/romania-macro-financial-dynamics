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

OUT = Path(os.environ.get("F4_AUDIT_OUT", "f4_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F4 loans audit)"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
MATURITIES = ("T", "S", "L")
TOL = 0.1


@dataclass(frozen=True)
class Term:
    coefficient: float
    key: str


def sector_terms(sector: str) -> tuple[tuple[str, float], ...]:
    if sector in DIRECT:
        return ((DIRECT[sector], 1.0),)
    return COMPOSITE[sector]


def key(
    area: str,
    ref: str,
    cp: str,
    entry: str,
    measure: str,
    maturity: str,
) -> str:
    return ".".join(
        (
            "Q", "N", "RO", area, ref, cp, "N", entry, measure, "F4",
            maturity, "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def candidate_terms(
    holder: str,
    issuer: str,
    measure: str,
    maturity: str,
) -> dict[str, tuple[Term, ...]]:
    if holder == "X" and issuer == "X":
        return {}
    if holder == "X":
        return {
            "issuer_liability_W1": tuple(
                Term(coeff, key("W1", code, "S1", "L", measure, maturity))
                for code, coeff in sector_terms(issuer)
            )
        }
    if issuer == "X":
        return {
            "holder_asset_W1": tuple(
                Term(coeff, key("W1", code, "S1", "A", measure, maturity))
                for code, coeff in sector_terms(holder)
            )
        }

    asset_terms: list[Term] = []
    liability_terms: list[Term] = []
    for h_code, h_coeff in sector_terms(holder):
        for i_code, i_coeff in sector_terms(issuer):
            coeff = h_coeff * i_coeff
            asset_terms.append(
                Term(coeff, key("W2", h_code, i_code, "A", measure, maturity))
            )
            liability_terms.append(
                Term(coeff, key("W2", i_code, h_code, "L", measure, maturity))
            )
    return {
        "holder_asset_W2": tuple(asset_terms),
        "issuer_liability_W2": tuple(liability_terms),
    }


def aggregate_terms(
    sector: str,
    entry: str,
    measure: str,
    maturity: str,
) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key("W0", code, "S1", entry, measure, maturity))
        for code, coeff in sector_terms(sector)
    )


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

    parsed = []
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
            }
        )
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def values(
    series: dict[str, object],
    measure: str,
    maturity: str,
) -> list[float] | None:
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != "F4"
        or row.get("maturity") != maturity
        for row in rows
    ):
        return None
    needed = (
        ("2025-Q4",)
        if measure == "LE"
        else ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
    )
    mapping = {str(row["period"]): float(row["value"]) for row in rows}
    if not all(p in mapping and math.isfinite(mapping[p]) for p in needed):
        return None
    return [mapping[p] for p in needed]


def evaluate(
    terms: tuple[Term, ...],
    series_by_key: dict[str, dict[str, object]],
    measure: str,
    maturity: str,
) -> tuple[float | None, list[dict[str, object]]]:
    total = 0.0
    detail = []
    for term in terms:
        vals = values(series_by_key[term.key], measure, maturity)
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


def evaluate_orientation(
    formulas: dict[str, dict[str, tuple[Term, ...]]],
    orientation: str,
    series_by_key: dict[str, dict[str, object]],
    measure: str,
) -> dict[str, object]:
    by_mat = {}
    for maturity in MATURITIES:
        terms = formulas[maturity].get(orientation)
        if terms is None:
            by_mat[maturity] = {"value": None, "terms": []}
        else:
            value, detail = evaluate(terms, series_by_key, measure, maturity)
            by_mat[maturity] = {"value": value, "terms": detail}

    direct = by_mat["T"]["value"]
    short = by_mat["S"]["value"]
    long = by_mat["L"]["value"]
    maturity_residual = (
        None
        if direct is None or short is None or long is None
        else float(direct) - float(short) - float(long)
    )
    maturity_status = (
        "CONTROL_UNAVAILABLE"
        if maturity_residual is None
        else "PASS"
        if abs(maturity_residual) <= TOL
        else "FAIL"
    )

    if direct is not None and maturity_status != "FAIL":
        selected = float(direct)
        derivation = "DIRECT_T"
    elif direct is None and short is not None and long is not None:
        selected = float(short) + float(long)
        derivation = "EXACT_S_PLUS_L"
    else:
        selected = None
        derivation = "UNAVAILABLE"

    return {
        "selected_value": selected,
        "derivation": derivation,
        "maturity_values": {
            m: by_mat[m]["value"] for m in MATURITIES
        },
        "maturity_residual_T_minus_S_minus_L": maturity_residual,
        "maturity_control_status": maturity_status,
        "terms": by_mat,
    }


def main() -> None:
    plans = []
    required: set[str] = set()
    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                formulas = {
                    maturity: candidate_terms(holder, issuer, measure, maturity)
                    for maturity in MATURITIES
                }
                plans.append((measure, holder, issuer, formulas))
                for candidate in formulas.values():
                    for terms in candidate.values():
                        required.update(term.key for term in terms)

    controls = []
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for kind, entry in (("holder_total", "A"), ("issuer_total", "L")):
                formulas = {
                    maturity: aggregate_terms(sector, entry, measure, maturity)
                    for maturity in MATURITIES
                }
                controls.append((measure, kind, sector, formulas))
                for terms in formulas.values():
                    required.update(term.key for term in terms)

    series_by_key = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, k): k for k in sorted(required)}
        for index, future in enumerate(as_completed(futures), start=1):
            k = futures[future]
            series_by_key[k] = future.result()
            print(f"[{index}/{len(futures)}] {k}", flush=True)

    cells = []
    for measure, holder, issuer, formulas in plans:
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
                    "derivation": None,
                    "orientations": {},
                }
            )
            continue

        orientations = sorted(
            set().union(*(set(x.keys()) for x in formulas.values()))
        )
        results = {
            orientation: evaluate_orientation(
                formulas, orientation, series_by_key, measure
            )
            for orientation in orientations
        }
        usable = {
            k: v for k, v in results.items()
            if v["selected_value"] is not None
            and v["maturity_control_status"] != "FAIL"
        }

        if not usable:
            status = "UNRESOLVED_SOURCE_COVERAGE"
            value = None
            selected_orientation = None
            derivation = None
        else:
            vals = [float(v["selected_value"]) for v in usable.values()]
            if len(vals) > 1 and max(vals) - min(vals) > TOL:
                status = "ORIENTATION_CONFLICT"
                value = None
                selected_orientation = None
                derivation = None
            else:
                status = "OBSERVABLE_OR_EXACT_DERIVATION"
                selected_orientation = (
                    "holder_asset_W2"
                    if "holder_asset_W2" in usable
                    else next(iter(usable))
                )
                selected = usable[selected_orientation]
                value = selected["selected_value"]
                derivation = selected["derivation"]

        cells.append(
            {
                "measure": label,
                "holder": holder,
                "issuer": issuer,
                "status": status,
                "value_million_RON": value,
                "selected_orientation": selected_orientation,
                "derivation": derivation,
                "orientations": results,
            }
        )

    reconciliation = []
    for measure, kind, sector, formulas in controls:
        label = "stock" if measure == "LE" else "flow"
        aggregate = evaluate_orientation(
            {m: {"aggregate_W0": formulas[m]} for m in MATURITIES},
            "aggregate_W0",
            series_by_key,
            measure,
        )
        official = aggregate["selected_value"]
        related = [
            c for c in cells
            if c["measure"] == label
            and (
                c["holder"] == sector
                if kind == "holder_total"
                else c["issuer"] == sector
            )
            and c["status"] != "OUTSIDE_BOUNDARY_NOT_APPLICABLE"
        ]
        complete = all(
            c["status"] == "OBSERVABLE_OR_EXACT_DERIVATION"
            for c in related
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
                "aggregate_maturity": aggregate,
            }
        )

    series_counts = Counter(str(x.get("status")) for x in series_by_key.values())
    cell_counts = Counter(x["status"] for x in cells)
    rec_counts = Counter(x["status"] for x in reconciliation)
    network_errors = any(
        x.get("status") == "NETWORK_ERROR" for x in series_by_key.values()
    )
    maturity_conflicts = sum(
        1
        for c in cells
        for o in c["orientations"].values()
        if o["maturity_control_status"] == "FAIL"
    )

    report = {
        "audit_version": "0.1",
        "instrument": "F4",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": dict(series_counts),
        "cell_status_counts": dict(cell_counts),
        "reconciliation_status_counts": dict(rec_counts),
        "network_errors_present": network_errors,
        "maturity_conflict_count": maturity_conflicts,
        "cells": cells,
        "aggregate_reconciliation": reconciliation,
        "rule": (
            "Coverage only. A cell may use direct all-maturity T or exact S+L. "
            "Missing data, maturity conflicts and orientation conflicts are never "
            "converted to zero or synthetic allocations."
        ),
    }
    (OUT / "f4_loans_coverage_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_requested": report["series_requested"],
                "series_status_counts": report["series_status_counts"],
                "cell_status_counts": report["cell_status_counts"],
                "reconciliation_status_counts":
                    report["reconciliation_status_counts"],
                "network_errors_present": network_errors,
                "maturity_conflict_count": maturity_conflicts,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
