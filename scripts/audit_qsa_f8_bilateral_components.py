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

OUT = Path(os.environ.get("F8_COMPONENT_OUT", "f8_component_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F8 component bridge)"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
COMPONENTS = ("F81", "F89")
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
    instrument: str,
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


def resolve_component(
    formulas: dict[str, tuple[Term, ...]],
    series_by_key: dict[str, dict[str, object]],
    measure: str,
    instrument: str,
) -> dict[str, object]:
    orientation_results = {}
    for orientation, terms in formulas.items():
        value, detail = evaluate(terms, series_by_key, measure, instrument)
        orientation_results[orientation] = {
            "value_million_RON": value,
            "terms": detail,
        }
    usable = {
        k: v for k, v in orientation_results.items()
        if v["value_million_RON"] is not None
    }
    if not usable:
        return {
            "status": "UNRESOLVED_SOURCE_COVERAGE",
            "value_million_RON": None,
            "selected_orientation": None,
            "orientation_results": orientation_results,
        }
    vals = [float(v["value_million_RON"]) for v in usable.values()]
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


def main() -> None:
    plans = []
    required: set[str] = set()

    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                by_component = {}
                for component in COMPONENTS:
                    formulas = candidate_terms(holder, issuer, measure, component)
                    by_component[component] = formulas
                    for terms in formulas.values():
                        required.update(t.key for t in terms)
                plans.append((measure, holder, issuer, by_component))

    controls = []
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for kind, entry in (("holder_total", "A"), ("issuer_total", "L")):
                terms = aggregate_terms(sector, entry, measure, "F8")
                controls.append((measure, kind, sector, terms))
                required.update(t.key for t in terms)

    total_controls = []
    for measure in ("LE", "F"):
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                terms = total_terms(area, entry, measure, "F8")
                total_controls.append((measure, area, entry, terms))
                required.update(t.key for t in terms)

    series_by_key = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch, k): k for k in sorted(required)}
        for index, future in enumerate(as_completed(futures), start=1):
            k = futures[future]
            series_by_key[k] = future.result()
            print(f"[{index}/{len(futures)}] {k}", flush=True)

    cells = []
    component_counts = {component: Counter() for component in COMPONENTS}
    component_conflicts = {component: 0 for component in COMPONENTS}
    for measure, holder, issuer, by_component in plans:
        label = "stock" if measure == "LE" else "flow"
        if holder == "X" and issuer == "X":
            cells.append({
                "measure": label,
                "holder": holder,
                "issuer": issuer,
                "status": "OUTSIDE_BOUNDARY_NOT_APPLICABLE",
                "value_million_RON": None,
                "components": {},
            })
            continue

        resolved = {}
        for component in COMPONENTS:
            result = resolve_component(
                by_component[component],
                series_by_key,
                measure,
                component,
            )
            resolved[component] = result
            component_counts[component][result["status"]] += 1
            if result["status"] == "ORIENTATION_CONFLICT":
                component_conflicts[component] += 1

        if any(
            resolved[c]["status"] == "ORIENTATION_CONFLICT"
            for c in COMPONENTS
        ):
            status = "COMPONENT_ORIENTATION_CONFLICT"
            value = None
        elif all(
            resolved[c]["status"] == "OBSERVABLE_OR_EXACT_DERIVATION"
            for c in COMPONENTS
        ):
            status = "EXACT_F81_PLUS_F89_DERIVATION"
            value = sum(float(resolved[c]["value_million_RON"]) for c in COMPONENTS)
        else:
            status = "UNRESOLVED_COMPONENT_COVERAGE"
            value = None

        cells.append({
            "measure": label,
            "holder": holder,
            "issuer": issuer,
            "status": status,
            "value_million_RON": value,
            "components": resolved,
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
        complete = all(c["status"] == "EXACT_F81_PLUS_F89_DERIVATION" for c in related)
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
            "official_F8_aggregate_million_RON": official,
            "residual_million_RON": residual,
            "status": status,
            "terms": detail,
        })

    total_lookup = {}
    totals = []
    for measure, area, entry, terms in total_controls:
        value, detail = evaluate(terms, series_by_key, measure, "F8")
        item = {
            "measure": "stock" if measure == "LE" else "flow",
            "area": area,
            "entry": entry,
            "value_million_RON": value,
            "status": "AVAILABLE" if value is not None else "UNAVAILABLE",
            "terms": detail,
        }
        totals.append(item)
        total_lookup[(item["measure"], area, entry)] = value

    external_controls = []
    for label in ("stock", "flow"):
        holder_to_x = [
            c for c in cells
            if c["measure"] == label and c["issuer"] == "X" and c["holder"] in RESIDENT
        ]
        x_to_issuer = [
            c for c in cells
            if c["measure"] == label and c["holder"] == "X" and c["issuer"] in RESIDENT
        ]
        for kind, related, entry in (
            ("resident_holder_to_X", holder_to_x, "A"),
            ("X_holder_to_resident_issuer", x_to_issuer, "L"),
        ):
            complete = all(c["status"] == "EXACT_F81_PLUS_F89_DERIVATION" for c in related)
            bilateral = (
                sum(float(c["value_million_RON"]) for c in related)
                if complete else None
            )
            official = total_lookup[(label, "W1", entry)]
            residual = (
                None if bilateral is None or official is None
                else bilateral - float(official)
            )
            status = (
                "CONTROL_UNAVAILABLE"
                if official is None
                else "BILATERAL_COVERAGE_INCOMPLETE"
                if not complete
                else "PASS"
                if abs(float(residual)) <= TOL
                else "FAIL"
            )
            external_controls.append({
                "measure": label,
                "kind": kind,
                "bilateral_complete": complete,
                "bilateral_sum_million_RON": bilateral,
                "published_W1_F8_million_RON": official,
                "residual_million_RON": residual,
                "status": status,
            })

    report = {
        "audit_version": "0.1",
        "instrument": "F8",
        "phase": "bilateral F81 plus F89 component bridge",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": dict(Counter(str(x.get("status")) for x in series_by_key.values())),
        "component_cell_status_counts": {
            component: dict(component_counts[component])
            for component in COMPONENTS
        },
        "component_orientation_conflict_counts": component_conflicts,
        "derived_F8_cell_status_counts": dict(Counter(x["status"] for x in cells)),
        "reconciliation_status_counts": dict(Counter(x["status"] for x in reconciliation)),
        "external_control_status_counts": dict(Counter(x["status"] for x in external_controls)),
        "network_errors_present": any(
            x.get("status") == "NETWORK_ERROR" for x in series_by_key.values()
        ),
        "cells": cells,
        "aggregate_reconciliation": reconciliation,
        "total_economy_F8_controls": totals,
        "external_F8_controls": external_controls,
        "rule": (
            "A bilateral total-F8 cell is derived only as exact F81+F89 after "
            "both component values are separately resolved and neither component "
            "has an orientation conflict. Missing components are never inferred "
            "from aggregate totals."
        ),
    }

    (OUT / "f8_bilateral_component_bridge_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "series_requested": report["series_requested"],
        "series_status_counts": report["series_status_counts"],
        "component_cell_status_counts": report["component_cell_status_counts"],
        "component_orientation_conflict_counts": component_conflicts,
        "derived_F8_cell_status_counts": report["derived_F8_cell_status_counts"],
        "reconciliation_status_counts": report["reconciliation_status_counts"],
        "external_control_status_counts": report["external_control_status_counts"],
        "network_errors_present": report["network_errors_present"],
    }, indent=2))


if __name__ == "__main__":
    main()
