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

OUT = Path(os.environ.get("F8_AUDIT_OUT", "f8_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F8 coverage audit)"
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
            instrument, "T", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def candidate_terms(
    holder: str,
    issuer: str,
    measure: str,
    instrument: str = "F8",
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
    instrument: str = "F8",
) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key("W0", code, "S1", entry, measure, instrument))
        for code, coeff in sector_terms(sector)
    )


def total_terms(area: str, entry: str, measure: str, instrument: str) -> tuple[Term, ...]:
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
                "custom_breakdown": row.get("CUSTOM_BREAKDOWN"),
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
        or row.get("maturity") != "T"
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
        detail.append({
            "coefficient": term.coefficient,
            "key": term.key,
            "usable": vals is not None,
            "values": vals,
        })
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
                formulas_by_instrument = {
                    instrument: candidate_terms(holder, issuer, measure, instrument)
                    for instrument in ("F8", "F81", "F89")
                }
                plans.append((measure, holder, issuer, formulas_by_instrument))
                for formulas in formulas_by_instrument.values():
                    for terms in formulas.values():
                        required.update(t.key for t in terms)

    controls = []
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for kind, entry in (("holder_total", "A"), ("issuer_total", "L")):
                terms = aggregate_terms(sector, entry, measure, "F8")
                controls.append((measure, kind, sector, terms))
                required.update(t.key for t in terms)

    total_controls = []
    decomposition_controls = []
    for measure in ("LE", "F"):
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                for instrument in ("F8", "F81", "F89"):
                    terms = total_terms(area, entry, measure, instrument)
                    total_controls.append((measure, area, entry, instrument, terms))
                    required.update(t.key for t in terms)
        for sector in RESIDENT:
            for entry in ("A", "L"):
                by_instrument = {}
                for instrument in ("F8", "F81", "F89"):
                    terms = aggregate_terms(sector, entry, measure, instrument)
                    by_instrument[instrument] = terms
                    required.update(t.key for t in terms)
                decomposition_controls.append((measure, sector, entry, by_instrument))

    series_by_key = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, k): k for k in sorted(required)}
        for index, future in enumerate(as_completed(futures), start=1):
            k = futures[future]
            series_by_key[k] = future.result()
            print(f"[{index}/{len(futures)}] {k}", flush=True)

    cells = []
    for measure, holder, issuer, formulas_by_instrument in plans:
        label = "stock" if measure == "LE" else "flow"
        if holder == "X" and issuer == "X":
            cells.append({
                "measure": label,
                "holder": holder,
                "issuer": issuer,
                "status": "OUTSIDE_BOUNDARY_NOT_APPLICABLE",
                "value_million_RON": None,
                "selected_orientation": None,
                "derivation": None,
                "orientation_results": {},
            })
            continue

        orientation_names = sorted(
            set().union(
                *(set(x.keys()) for x in formulas_by_instrument.values())
            )
        )
        orientation_results = {}
        usable = {}
        subinstrument_conflict = False

        for orientation in orientation_names:
            by_instrument = {}
            for instrument in ("F8", "F81", "F89"):
                terms = formulas_by_instrument[instrument].get(orientation)
                if terms is None:
                    by_instrument[instrument] = {
                        "value_million_RON": None,
                        "terms": [],
                    }
                    continue
                value, detail = evaluate(
                    terms, series_by_key, measure, instrument
                )
                by_instrument[instrument] = {
                    "value_million_RON": value,
                    "terms": detail,
                }

            direct = by_instrument["F8"]["value_million_RON"]
            f81 = by_instrument["F81"]["value_million_RON"]
            f89 = by_instrument["F89"]["value_million_RON"]
            component_sum = (
                None if f81 is None or f89 is None
                else float(f81) + float(f89)
            )
            decomposition_residual = (
                None if direct is None or component_sum is None
                else float(direct) - component_sum
            )
            decomposition_status = (
                "CONTROL_INCOMPLETE"
                if decomposition_residual is None
                else "PASS"
                if abs(decomposition_residual) <= TOL
                else "FAIL"
            )
            if decomposition_status == "FAIL":
                subinstrument_conflict = True

            if direct is not None and decomposition_status != "FAIL":
                selected_value = float(direct)
                derivation = "DIRECT_F8"
            elif direct is None and component_sum is not None:
                selected_value = component_sum
                derivation = "EXACT_F81_PLUS_F89"
            else:
                selected_value = None
                derivation = "UNAVAILABLE"

            orientation_results[orientation] = {
                "selected_value_million_RON": selected_value,
                "derivation": derivation,
                "F8_direct_million_RON": direct,
                "F81_million_RON": f81,
                "F89_million_RON": f89,
                "F81_plus_F89_million_RON": component_sum,
                "F8_minus_F81_minus_F89_residual_million_RON":
                    decomposition_residual,
                "subinstrument_control_status": decomposition_status,
                "instrument_results": by_instrument,
            }
            if selected_value is not None:
                usable[orientation] = orientation_results[orientation]

        if subinstrument_conflict:
            status = "SUBINSTRUMENT_CONFLICT"
            value = None
            selected = None
            derivation = None
        elif not usable:
            status = "UNRESOLVED_SOURCE_COVERAGE"
            value = None
            selected = None
            derivation = None
        else:
            vals = [
                float(v["selected_value_million_RON"])
                for v in usable.values()
            ]
            if len(vals) > 1 and max(vals) - min(vals) > TOL:
                status = "ORIENTATION_CONFLICT"
                value = None
                selected = None
                derivation = None
            else:
                status = "OBSERVABLE_OR_EXACT_DERIVATION"
                selected = (
                    "holder_asset_W2"
                    if "holder_asset_W2" in usable
                    else next(iter(usable))
                )
                value = usable[selected]["selected_value_million_RON"]
                derivation = usable[selected]["derivation"]

        cells.append({
            "measure": label,
            "holder": holder,
            "issuer": issuer,
            "status": status,
            "value_million_RON": value,
            "selected_orientation": selected,
            "derivation": derivation,
            "orientation_results": orientation_results,
        })

    reconciliation = []
    for measure, kind, sector, terms in controls:
        label = "stock" if measure == "LE" else "flow"
        official, detail = evaluate(terms, series_by_key, measure, "F8")
        related = [
            c for c in cells
            if c["measure"] == label
            and (
                c["holder"] == sector if kind == "holder_total"
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
        if official is None:
            status = "CONTROL_UNAVAILABLE"
        elif not complete:
            status = "BILATERAL_COVERAGE_INCOMPLETE"
        elif abs(float(residual)) <= TOL:
            status = "PASS"
        else:
            status = "FAIL"
        reconciliation.append({
            "measure": label,
            "kind": kind,
            "sector": sector,
            "bilateral_complete": complete,
            "bilateral_sum_million_RON": bilateral,
            "official_aggregate_million_RON": official,
            "residual_million_RON": residual,
            "status": status,
            "terms": detail,
        })

    totals = []
    total_lookup = {}
    for measure, area, entry, instrument, terms in total_controls:
        value, detail = evaluate(terms, series_by_key, measure, instrument)
        item = {
            "measure": "stock" if measure == "LE" else "flow",
            "area": area,
            "entry": entry,
            "instrument": instrument,
            "value_million_RON": value,
            "status": "AVAILABLE" if value is not None else "UNAVAILABLE",
            "terms": detail,
        }
        totals.append(item)
        total_lookup[(measure, area, entry, instrument)] = value

    decomposition = []
    for measure, sector, entry, by_instrument in decomposition_controls:
        vals = {}
        details = {}
        for instrument, terms in by_instrument.items():
            value, detail = evaluate(terms, series_by_key, measure, instrument)
            vals[instrument] = value
            details[instrument] = detail
        if all(vals[k] is not None for k in ("F8", "F81", "F89")):
            residual = float(vals["F8"]) - float(vals["F81"]) - float(vals["F89"])
            status = "PASS" if abs(residual) <= TOL else "FAIL"
        else:
            residual = None
            status = "CONTROL_INCOMPLETE"
        decomposition.append({
            "measure": "stock" if measure == "LE" else "flow",
            "sector": sector,
            "entry": entry,
            "F8_million_RON": vals["F8"],
            "F81_million_RON": vals["F81"],
            "F89_million_RON": vals["F89"],
            "residual_F8_minus_F81_minus_F89_million_RON": residual,
            "status": status,
            "terms": details,
        })

    total_decomposition = []
    for measure in ("LE", "F"):
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                vals = {
                    instrument: total_lookup[(measure, area, entry, instrument)]
                    for instrument in ("F8", "F81", "F89")
                }
                if all(vals[k] is not None for k in vals):
                    residual = float(vals["F8"]) - float(vals["F81"]) - float(vals["F89"])
                    status = "PASS" if abs(residual) <= TOL else "FAIL"
                else:
                    residual = None
                    status = "CONTROL_INCOMPLETE"
                total_decomposition.append({
                    "measure": "stock" if measure == "LE" else "flow",
                    "area": area,
                    "entry": entry,
                    **{f"{k}_million_RON": v for k, v in vals.items()},
                    "residual_F8_minus_F81_minus_F89_million_RON": residual,
                    "status": status,
                })

    report = {
        "audit_version": "0.1",
        "instrument": "F8",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": dict(Counter(str(x.get("status")) for x in series_by_key.values())),
        "cell_status_counts": dict(Counter(x["status"] for x in cells)),
        "cell_derivation_counts": dict(Counter(
            str(x.get("derivation"))
            for x in cells
            if x["status"] == "OBSERVABLE_OR_EXACT_DERIVATION"
        )),
        "reconciliation_status_counts": dict(Counter(x["status"] for x in reconciliation)),
        "decomposition_status_counts": dict(Counter(x["status"] for x in decomposition)),
        "total_decomposition_status_counts": dict(Counter(x["status"] for x in total_decomposition)),
        "network_errors_present": any(
            x.get("status") == "NETWORK_ERROR" for x in series_by_key.values()
        ),
        "cells": cells,
        "aggregate_reconciliation": reconciliation,
        "total_economy_controls": totals,
        "sector_F8_equals_F81_plus_F89_controls": decomposition,
        "total_F8_equals_F81_plus_F89_controls": total_decomposition,
        "rule": (
            "Coverage only. F8 is the total other-accounts instrument. F81 trade "
            "credits and advances and F89 other receivables/payables are used only "
            "as exact decomposition controls where both are published; neither "
            "subinstrument substitutes for F8."
        ),
    }

    (OUT / "f8_other_accounts_coverage_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "series_requested": report["series_requested"],
        "series_status_counts": report["series_status_counts"],
        "cell_status_counts": report["cell_status_counts"],
        "cell_derivation_counts": report["cell_derivation_counts"],
        "reconciliation_status_counts": report["reconciliation_status_counts"],
        "decomposition_status_counts": report["decomposition_status_counts"],
        "total_decomposition_status_counts": report["total_decomposition_status_counts"],
        "network_errors_present": report["network_errors_present"],
    }, indent=2))


if __name__ == "__main__":
    main()
