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

OUT = Path(os.environ.get("F6_AUDIT_OUT", "f6_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F6 coverage audit)"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
SUBCOMPONENTS = ("F61", "F62", "F63", "F64", "F65", "F66")
PENSION_BLOCK = "F63_F64_F65"
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
    cp: str,
    entry: str,
    measure: str,
    instrument: str,
) -> str:
    return ".".join(
        (
            "Q", "N", "RO", area, ref, cp, "N", entry, measure,
            instrument, "_Z", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def candidate_terms(
    holder: str,
    issuer: str,
    measure: str,
    instrument: str = "F6",
) -> dict[str, tuple[Term, ...]]:
    if holder == "X" and issuer == "X":
        return {}
    if holder == "X":
        return {
            "issuer_liability_W1": tuple(
                Term(coeff, key("W1", code, "S1", "L", measure, instrument))
                for code, coeff in sector_terms(issuer)
            )
        }
    if issuer == "X":
        return {
            "holder_asset_W1": tuple(
                Term(coeff, key("W1", code, "S1", "A", measure, instrument))
                for code, coeff in sector_terms(holder)
            )
        }

    asset_terms: list[Term] = []
    liability_terms: list[Term] = []
    for h_code, h_coeff in sector_terms(holder):
        for i_code, i_coeff in sector_terms(issuer):
            coeff = h_coeff * i_coeff
            asset_terms.append(
                Term(coeff, key("W2", h_code, i_code, "A", measure, instrument))
            )
            liability_terms.append(
                Term(coeff, key("W2", i_code, h_code, "L", measure, instrument))
            )
    return {
        "holder_asset_W2": tuple(asset_terms),
        "issuer_liability_W2": tuple(liability_terms),
    }


def aggregate_terms(
    sector: str,
    entry: str,
    measure: str,
    instrument: str,
) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key("W0", code, "S1", entry, measure, instrument))
        for code, coeff in sector_terms(sector)
    )


def total_terms(
    area: str,
    entry: str,
    measure: str,
    instrument: str,
) -> tuple[Term, ...]:
    return (Term(1.0, key(area, "S1", "S1", entry, measure, instrument)),)


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
                "expenditure": row.get("EXPENDITURE"),
            }
        )
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def values(
    series: dict[str, object],
    measure: str,
    instrument: str,
) -> list[float] | None:
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != instrument
        or row.get("maturity") not in {"_Z", None}
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
    instrument: str,
) -> tuple[float | None, list[dict[str, object]]]:
    total = 0.0
    detail = []
    for term in terms:
        vals = values(series_by_key[term.key], measure, instrument)
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


def resolve_total_cell(
    formulas: dict[str, tuple[Term, ...]],
    series_by_key: dict[str, dict[str, object]],
    measure: str,
) -> dict[str, object]:
    orientation_results = {}
    for orientation, terms in formulas.items():
        value, detail = evaluate(terms, series_by_key, measure, "F6")
        orientation_results[orientation] = {
            "value_million_RON": value,
            "terms": detail,
        }
    usable = {
        name: item
        for name, item in orientation_results.items()
        if item["value_million_RON"] is not None
    }
    if not usable:
        return {
            "status": "UNRESOLVED_SOURCE_COVERAGE",
            "value_million_RON": None,
            "selected_orientation": None,
            "orientation_results": orientation_results,
        }
    vals = [float(item["value_million_RON"]) for item in usable.values()]
    if len(vals) > 1 and max(vals) - min(vals) > TOL:
        return {
            "status": "ORIENTATION_CONFLICT",
            "value_million_RON": None,
            "selected_orientation": None,
            "orientation_results": orientation_results,
        }
    selected = (
        "holder_asset_W2"
        if "holder_asset_W2" in usable
        else next(iter(usable))
    )
    return {
        "status": "OBSERVABLE_OR_EXACT_DERIVATION",
        "value_million_RON": usable[selected]["value_million_RON"],
        "selected_orientation": selected,
        "orientation_results": orientation_results,
    }


def decomposition_status(vals: dict[str, float | None]) -> dict[str, object]:
    full_keys = ("F6", "F61", "F62", "F63", "F64", "F65", "F66")
    block_keys = ("F6", "F61", "F62", PENSION_BLOCK, "F66")
    pension_keys = (PENSION_BLOCK, "F63", "F64", "F65")

    result = {}
    if all(vals.get(k) is not None for k in full_keys):
        residual = (
            float(vals["F6"])
            - sum(float(vals[k]) for k in ("F61", "F62", "F63", "F64", "F65", "F66"))
        )
        result["full_six_component"] = {
            "status": "PASS" if abs(residual) <= TOL else "FAIL",
            "residual_million_RON": residual,
        }
    else:
        result["full_six_component"] = {
            "status": "CONTROL_INCOMPLETE",
            "residual_million_RON": None,
        }

    if all(vals.get(k) is not None for k in block_keys):
        residual = (
            float(vals["F6"])
            - float(vals["F61"])
            - float(vals["F62"])
            - float(vals[PENSION_BLOCK])
            - float(vals["F66"])
        )
        result["transmission_block"] = {
            "status": "PASS" if abs(residual) <= TOL else "FAIL",
            "residual_million_RON": residual,
        }
    else:
        result["transmission_block"] = {
            "status": "CONTROL_INCOMPLETE",
            "residual_million_RON": None,
        }

    if all(vals.get(k) is not None for k in pension_keys):
        residual = (
            float(vals[PENSION_BLOCK])
            - float(vals["F63"])
            - float(vals["F64"])
            - float(vals["F65"])
        )
        result["pension_block"] = {
            "status": "PASS" if abs(residual) <= TOL else "FAIL",
            "residual_million_RON": residual,
        }
    else:
        result["pension_block"] = {
            "status": "CONTROL_INCOMPLETE",
            "residual_million_RON": None,
        }
    return result


def main() -> None:
    required: set[str] = set()
    plans = []

    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                formulas = candidate_terms(holder, issuer, measure, "F6")
                plans.append((measure, holder, issuer, formulas))
                for terms in formulas.values():
                    required.update(t.key for t in terms)

    sector_controls = []
    instruments = ("F6", "F61", "F62", "F63", "F64", "F65", "F66", PENSION_BLOCK)
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for entry in ("A", "L"):
                by_instrument = {}
                for instrument in instruments:
                    terms = aggregate_terms(sector, entry, measure, instrument)
                    by_instrument[instrument] = terms
                    required.update(t.key for t in terms)
                sector_controls.append((measure, sector, entry, by_instrument))

    total_controls = []
    for measure in ("LE", "F"):
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                by_instrument = {}
                for instrument in instruments:
                    terms = total_terms(area, entry, measure, instrument)
                    by_instrument[instrument] = terms
                    required.update(t.key for t in terms)
                total_controls.append((measure, area, entry, by_instrument))

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
                    "orientation_results": {},
                }
            )
            continue
        item = resolve_total_cell(formulas, series_by_key, measure)
        cells.append(
            {
                "measure": label,
                "holder": holder,
                "issuer": issuer,
                **item,
            }
        )

    sector_decomposition = []
    for measure, sector, entry, by_instrument in sector_controls:
        vals = {}
        details = {}
        for instrument, terms in by_instrument.items():
            value, detail = evaluate(terms, series_by_key, measure, instrument)
            vals[instrument] = value
            details[instrument] = detail
        sector_decomposition.append(
            {
                "measure": "stock" if measure == "LE" else "flow",
                "sector": sector,
                "entry": entry,
                "values_million_RON": vals,
                "decomposition": decomposition_status(vals),
                "terms": details,
            }
        )

    total_decomposition = []
    for measure, area, entry, by_instrument in total_controls:
        vals = {}
        details = {}
        for instrument, terms in by_instrument.items():
            value, detail = evaluate(terms, series_by_key, measure, instrument)
            vals[instrument] = value
            details[instrument] = detail
        total_decomposition.append(
            {
                "measure": "stock" if measure == "LE" else "flow",
                "area": area,
                "entry": entry,
                "values_million_RON": vals,
                "decomposition": decomposition_status(vals),
                "terms": details,
            }
        )

    reconciliation = []
    for item in sector_decomposition:
        measure = item["measure"]
        sector = item["sector"]
        entry = item["entry"]
        official = item["values_million_RON"]["F6"]
        related = [
            c for c in cells
            if c["measure"] == measure
            and (
                c["holder"] == sector if entry == "A"
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
            if complete else None
        )
        residual = (
            None if official is None or bilateral is None
            else bilateral - float(official)
        )
        status = (
            "CONTROL_UNAVAILABLE" if official is None
            else "BILATERAL_COVERAGE_INCOMPLETE" if not complete
            else "PASS" if abs(float(residual)) <= TOL
            else "FAIL"
        )
        reconciliation.append(
            {
                "measure": measure,
                "kind": "holder_total" if entry == "A" else "issuer_total",
                "sector": sector,
                "bilateral_complete": complete,
                "bilateral_sum_million_RON": bilateral,
                "official_F6_aggregate_million_RON": official,
                "residual_million_RON": residual,
                "status": status,
            }
        )

    def count_decomp(items, key):
        return dict(Counter(x["decomposition"][key]["status"] for x in items))

    report = {
        "audit_version": "0.1",
        "instrument": "F6",
        "phase": "total coverage and aggregate decomposition audit",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": dict(
            Counter(str(x.get("status")) for x in series_by_key.values())
        ),
        "cell_status_counts": dict(Counter(x["status"] for x in cells)),
        "reconciliation_status_counts": dict(
            Counter(x["status"] for x in reconciliation)
        ),
        "sector_decomposition_status_counts": {
            "full_six_component": count_decomp(sector_decomposition, "full_six_component"),
            "transmission_block": count_decomp(sector_decomposition, "transmission_block"),
            "pension_block": count_decomp(sector_decomposition, "pension_block"),
        },
        "total_decomposition_status_counts": {
            "full_six_component": count_decomp(total_decomposition, "full_six_component"),
            "transmission_block": count_decomp(total_decomposition, "transmission_block"),
            "pension_block": count_decomp(total_decomposition, "pension_block"),
        },
        "network_errors_present": any(
            x.get("status") == "NETWORK_ERROR"
            for x in series_by_key.values()
        ),
        "cells": cells,
        "aggregate_reconciliation": reconciliation,
        "sector_component_controls": sector_decomposition,
        "total_economy_component_controls": total_decomposition,
        "rule": (
            "Phase A audits direct total-F6 bilateral coverage and aggregate "
            "decomposition only. No issuer applicability or component bilateral "
            "zero is assumed. F6 decomposition may use the six-way identity or "
            "the official F63_F64_F65 transmission block only when all terms of "
            "the corresponding identity are published."
        ),
    }

    (OUT / "f6_insurance_pensions_coverage_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "series_requested": report["series_requested"],
        "series_status_counts": report["series_status_counts"],
        "cell_status_counts": report["cell_status_counts"],
        "reconciliation_status_counts": report["reconciliation_status_counts"],
        "sector_decomposition_status_counts": report["sector_decomposition_status_counts"],
        "total_decomposition_status_counts": report["total_decomposition_status_counts"],
        "network_errors_present": report["network_errors_present"],
    }, indent=2))


if __name__ == "__main__":
    main()
