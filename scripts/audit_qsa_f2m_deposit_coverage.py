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
from dataclasses import dataclass
from pathlib import Path

OUT = Path(os.environ.get("F2M_AUDIT_OUT", "f2m_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F2M deposit audit)"

SECTORS = ("H", "C", "F", "G", "X", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
STRUCTURAL_NON_ISSUERS = {"H", "C"}
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
            "Q", "N", "RO", area, ref, cp, "N", entry, measure, "F2M",
            "T", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def formula(holder: str, issuer: str, measure: str) -> tuple[Term, ...]:
    if holder == "X" and issuer == "X":
        return ()
    if issuer in STRUCTURAL_NON_ISSUERS:
        return ()

    if holder == "X":
        return tuple(
            Term(
                coeff,
                key("W1", issuer_code, "S1", "L", measure),
            )
            for issuer_code, coeff in sector_terms(issuer)
        )

    if issuer == "X":
        return tuple(
            Term(
                coeff,
                key("W1", holder_code, "S1", "A", measure),
            )
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(series_key: str) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {"startPeriod": "2025-Q1", "endPeriod": "2025-Q4", "format": "csvdata"}
    )
    url = f"{API}{series_key}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
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
        return {"key": series_key, "status": "NETWORK_ERROR", "error": str(exc), "rows": []}

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
            }
        )

    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def values(series: dict[str, object], measure: str) -> list[float] | None:
    needed = ["2025-Q4"] if measure == "LE" else ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
    if series.get("status") != "AVAILABLE":
        return None

    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != "F2M"
        for row in series.get("rows", [])
    ):
        return None

    mapping = {str(row["period"]): float(row["value"]) for row in series["rows"]}
    if not all(period in mapping and math.isfinite(mapping[period]) for period in needed):
        return None
    return [mapping[period] for period in needed]


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


def aggregate_terms(sector: str, entry: str, measure: str) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key("W0", code, "S1", entry, measure))
        for code, coeff in sector_terms(sector)
    )


def main() -> None:
    plans = []
    required = set()
    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                terms = formula(holder, issuer, measure)
                plans.append((measure, holder, issuer, terms))
                required.update(term.key for term in terms)

    controls = []
    for measure in ("LE", "F"):
        for sector in ("H", "C", "F", "G", "BNR"):
            holder_terms = aggregate_terms(sector, "A", measure)
            issuer_terms = aggregate_terms(sector, "L", measure)
            controls.append((measure, "holder_total", sector, holder_terms))
            controls.append((measure, "issuer_total", sector, issuer_terms))
            required.update(term.key for term in holder_terms)
            required.update(term.key for term in issuer_terms)

    series_by_key = {}
    for index, series_key in enumerate(sorted(required), start=1):
        print(f"[{index}/{len(required)}] {series_key}", flush=True)
        series_by_key[series_key] = fetch(series_key)

    cells = []
    for measure, holder, issuer, terms in plans:
        value, detail = evaluate(terms, series_by_key, measure)
        if holder == "X" and issuer == "X":
            status = "OUTSIDE_BOUNDARY_CANDIDATE_NOT_APPLICABLE"
        elif issuer in STRUCTURAL_NON_ISSUERS:
            status = "STRUCTURAL_NOT_APPLICABLE_ESA"
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
        if kind == "holder_total":
            bilateral = sum(
                float(cell["value_million_RON"])
                for cell in cells
                if cell["measure"] == label
                and cell["holder"] == sector
                and cell["value_million_RON"] is not None
            )
        else:
            bilateral = sum(
                float(cell["value_million_RON"])
                for cell in cells
                if cell["measure"] == label
                and cell["issuer"] == sector
                and cell["value_million_RON"] is not None
            )
        residual = None if official is None else bilateral - official
        external_cell = next(
            (
                cell
                for cell in cells
                if cell["measure"] == label
                and cell["holder"] == sector
                and cell["issuer"] == "X"
            ),
            None,
        )

        if kind == "issuer_total" and sector in STRUCTURAL_NON_ISSUERS:
            if official is None:
                status = "STRUCTURAL_NOT_APPLICABLE_ESA"
            elif abs(float(official)) <= TOL:
                status = "STRUCTURAL_NOT_APPLICABLE_CONFIRMED_ZERO"
            else:
                status = "STRUCTURAL_DEFINITION_CONFLICT_REQUIRES_AUDIT"
        elif official is None:
            status = "CONTROL_UNAVAILABLE"
        elif abs(residual) <= TOL:
            status = "PASS"
        elif (
            kind == "holder_total"
            and external_cell is not None
            and external_cell["status"] == "UNRESOLVED_SOURCE_COVERAGE"
        ):
            status = "INCOMPLETE_EXTERNAL_ISSUER_COLUMN"
        else:
            status = "FAIL"
        reconciliation.append(
            {
                "measure": label,
                "kind": kind,
                "sector": sector,
                "bilateral_sum_million_RON": bilateral,
                "official_aggregate_million_RON": official,
                "residual_million_RON": residual,
                "status": status,
                "terms": detail,
            }
        )

    report = {
        "audit_version": "0.1",
        "instrument": "F2M",
        "benchmark_changed": False,
        "total_F2_materialization_allowed": False,
        "currency_F21_status": "SEPARATE_UNRESOLVED_IDENTIFICATION_PROBLEM",
        "external_F2M_asset_status": "UNRESOLVED_OFFICIAL_SOURCE_IDENTIFICATION",
        "series_requested": len(required),
        "series_status_counts": {},
        "cell_status_counts": {},
        "reconciliation_status_counts": {},
        "cells": cells,
        "aggregate_reconciliation": reconciliation,
    }

    for series in series_by_key.values():
        status = str(series.get("status"))
        report["series_status_counts"][status] = report["series_status_counts"].get(status, 0) + 1
    for cell in cells:
        status = cell["status"]
        report["cell_status_counts"][status] = report["cell_status_counts"].get(status, 0) + 1
    for item in reconciliation:
        status = item["status"]
        report["reconciliation_status_counts"][status] = (
            report["reconciliation_status_counts"].get(status, 0) + 1
        )

    (OUT / "f2m_deposit_coverage_audit.json").write_text(
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
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
