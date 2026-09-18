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

OUT = Path(os.environ.get("F5_EQUITY_OUT", "f5_equity_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F5 equity bridge)"
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
DIRECT = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}
COMPOSITE = {"F": (("S12", 1.0), ("S121", -1.0))}
NONFUND_RESIDENT_ISSUERS = ("H", "C", "G", "BNR")
EQUITY_COMPONENTS = ("F511", "F512", "F519")
TOL = 0.1


@dataclass(frozen=True)
class Term:
    coefficient: float
    key: str


def sector_terms(sector: str) -> tuple[tuple[str, float], ...]:
    if sector in DIRECT:
        return ((DIRECT[sector], 1.0),)
    if sector == "F":
        return COMPOSITE["F"]
    raise ValueError(sector)


def f52_issuer_terms(sector: str) -> tuple[tuple[str, float], ...]:
    if sector in NONFUND_RESIDENT_ISSUERS:
        return ()
    if sector == "F":
        return (("S12", 1.0),)
    raise ValueError(sector)


def key(area: str, ref: str, cp: str, entry: str, measure: str, instrument: str) -> str:
    return ".".join((
        "Q", "N", "RO", area, ref, cp, "N", entry, measure,
        instrument, "_Z", "_Z", "XDC", "_T", "S", "V", "N", "_T",
    ))


def generic_candidate_terms(
    holder: str, issuer: str, measure: str, instrument: str
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
    assets = []
    liabilities = []
    for h_code, h_coeff in sector_terms(holder):
        for i_code, i_coeff in sector_terms(issuer):
            coeff = h_coeff * i_coeff
            assets.append(Term(coeff, key("W2", h_code, i_code, "A", measure, instrument)))
            liabilities.append(Term(coeff, key("W2", i_code, h_code, "L", measure, instrument)))
    return {"holder_asset_W2": tuple(assets), "issuer_liability_W2": tuple(liabilities)}


def f52_candidate_terms(holder: str, issuer: str, measure: str) -> dict[str, tuple[Term, ...]]:
    if holder == "X" and issuer == "X":
        return {}
    if issuer in NONFUND_RESIDENT_ISSUERS:
        return {"structural_zero": ()}
    if holder == "X":
        issuer_terms = f52_issuer_terms(issuer)
        return {
            "issuer_liability_W1": tuple(
                Term(coeff, key("W1", code, "S1", "L", measure, "F52"))
                for code, coeff in issuer_terms
            )
        }
    if issuer == "X":
        return {
            "holder_asset_W1": tuple(
                Term(coeff, key("W1", code, "S1", "A", measure, "F52"))
                for code, coeff in sector_terms(holder)
            )
        }
    assets = []
    liabilities = []
    for h_code, h_coeff in sector_terms(holder):
        for i_code, i_coeff in f52_issuer_terms(issuer):
            coeff = h_coeff * i_coeff
            assets.append(Term(coeff, key("W2", h_code, i_code, "A", measure, "F52")))
            liabilities.append(Term(coeff, key("W2", i_code, h_code, "L", measure, "F52")))
    return {"holder_asset_W2": tuple(assets), "issuer_liability_W2": tuple(liabilities)}


def aggregate_terms(sector: str, entry: str, measure: str, instrument: str) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key("W0", code, "S1", entry, measure, instrument))
        for code, coeff in sector_terms(sector)
    )


def total_terms(area: str, entry: str, measure: str, instrument: str) -> tuple[Term, ...]:
    return (Term(1.0, key(area, "S1", "S1", entry, measure, instrument)),)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(series_key: str) -> dict[str, object]:
    query = urllib.parse.urlencode({
        "startPeriod": "2025-Q1", "endPeriod": "2025-Q4", "format": "csvdata"
    })
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
                    "key": series_key, "url": url, "status": "NETWORK_ERROR",
                    "error": str(last_error), "rows": [],
                }
    else:
        raise AssertionError("unreachable")

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
        if not row.get("TIME_PERIOD") or row.get("OBS_VALUE") in (None, ""):
            continue
        try:
            value = float(row["OBS_VALUE"])
        except ValueError:
            continue
        parsed.append({
            "period": row["TIME_PERIOD"],
            "value": value,
            "unit": row.get("UNIT_MEASURE") or row.get("UNIT"),
            "unit_mult": row.get("UNIT_MULT"),
            "instrument": row.get("INSTR_ASSET"),
            "entry": row.get("ACCOUNTING_ENTRY"),
            "measure": row.get("STO"),
            "maturity": row.get("MATURITY"),
            "expenditure": row.get("EXPENDITURE"),
        })
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def values(series: dict[str, object], measure: str, instrument: str) -> list[float] | None:
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
    needed = ("2025-Q4",) if measure == "LE" else (
        "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"
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


def resolve(
    formulas: dict[str, tuple[Term, ...]],
    series_by_key: dict[str, dict[str, object]],
    measure: str,
    instrument: str,
    structural_zero: bool = False,
) -> dict[str, object]:
    if structural_zero:
        return {
            "status": "STRUCTURAL_NOT_APPLICABLE_RESIDENT_NONFUND_ISSUER",
            "value_million_RON": 0.0,
            "selected_orientation": "ESA_F52_issuer_scope",
            "orientation_results": {},
        }
    orientation_results = {}
    for orientation, terms in formulas.items():
        if orientation == "structural_zero":
            continue
        value, detail = evaluate(terms, series_by_key, measure, instrument)
        orientation_results[orientation] = {
            "value_million_RON": value,
            "terms": detail,
        }
    usable = {
        name: item for name, item in orientation_results.items()
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
    selected = "holder_asset_W2" if "holder_asset_W2" in usable else next(iter(usable))
    return {
        "status": "OBSERVABLE_OR_EXACT_DERIVATION",
        "value_million_RON": usable[selected]["value_million_RON"],
        "selected_orientation": selected,
        "orientation_results": orientation_results,
    }


def main() -> None:
    required: set[str] = set()
    plans = []
    for measure in ("LE", "F"):
        for holder in SECTORS:
            for issuer in SECTORS:
                equity_formulas = {}
                for component in EQUITY_COMPONENTS:
                    formulas = generic_candidate_terms(holder, issuer, measure, component)
                    equity_formulas[component] = formulas
                    for terms in formulas.values():
                        required.update(t.key for t in terms)
                f52_formulas = f52_candidate_terms(holder, issuer, measure)
                for orientation, terms in f52_formulas.items():
                    if orientation != "structural_zero":
                        required.update(t.key for t in terms)
                plans.append((measure, holder, issuer, equity_formulas, f52_formulas))

    sector_controls = []
    total_controls = []
    for measure in ("LE", "F"):
        for sector in RESIDENT:
            for entry in ("A", "L"):
                by_instrument = {}
                for instrument in ("F51", "F511", "F512", "F519"):
                    terms = aggregate_terms(sector, entry, measure, instrument)
                    by_instrument[instrument] = terms
                    required.update(t.key for t in terms)
                sector_controls.append((measure, sector, entry, by_instrument))
        for area in ("W0", "W1"):
            for entry in ("A", "L"):
                by_instrument = {}
                for instrument in ("F51", "F511", "F512", "F519", "F5"):
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
    equity_component_counts = {c: Counter() for c in EQUITY_COMPONENTS}
    f51_counts = Counter()
    f52_counts = Counter()
    total_f5_counts = Counter()

    for measure, holder, issuer, equity_formulas, f52_formulas in plans:
        label = "stock" if measure == "LE" else "flow"
        if holder == "X" and issuer == "X":
            cells.append({
                "measure": label, "holder": holder, "issuer": issuer,
                "status": "OUTSIDE_BOUNDARY_NOT_APPLICABLE",
                "value_million_RON": None, "equity_components": {}, "F52": {},
            })
            continue

        components = {}
        for component in EQUITY_COMPONENTS:
            item = resolve(
                equity_formulas[component], series_by_key, measure, component
            )
            components[component] = item
            equity_component_counts[component][item["status"]] += 1

        if any(item["status"] == "ORIENTATION_CONFLICT" for item in components.values()):
            f51_status = "COMPONENT_ORIENTATION_CONFLICT"
            f51_value = None
        elif all(
            item["status"] == "OBSERVABLE_OR_EXACT_DERIVATION"
            for item in components.values()
        ):
            f51_status = "EXACT_F511_PLUS_F512_PLUS_F519_DERIVATION"
            f51_value = sum(float(item["value_million_RON"]) for item in components.values())
        else:
            f51_status = "UNRESOLVED_SUBCOMPONENT_COVERAGE"
            f51_value = None
        f51_counts[f51_status] += 1

        f52_structural = issuer in NONFUND_RESIDENT_ISSUERS
        f52 = resolve(
            f52_formulas, series_by_key, measure, "F52",
            structural_zero=f52_structural,
        )
        f52_counts[f52["status"]] += 1

        if f51_status != "EXACT_F511_PLUS_F512_PLUS_F519_DERIVATION":
            total_status = "UNRESOLVED_F51_COVERAGE"
            total_value = None
        elif f52["status"] in {
            "OBSERVABLE_OR_EXACT_DERIVATION",
            "STRUCTURAL_NOT_APPLICABLE_RESIDENT_NONFUND_ISSUER",
        }:
            total_status = "EXACT_F51_PLUS_F52_DERIVATION"
            total_value = float(f51_value) + float(f52["value_million_RON"])
        elif f52["status"] == "ORIENTATION_CONFLICT":
            total_status = "F52_ORIENTATION_CONFLICT"
            total_value = None
        else:
            total_status = "UNRESOLVED_F52_COVERAGE"
            total_value = None
        total_f5_counts[total_status] += 1

        cells.append({
            "measure": label,
            "holder": holder,
            "issuer": issuer,
            "status": total_status,
            "value_million_RON": total_value,
            "F51": {
                "status": f51_status,
                "value_million_RON": f51_value,
                "components": components,
            },
            "F52": f52,
        })

    sector_decomposition = []
    for measure, sector, entry, by_instrument in sector_controls:
        vals = {}
        details = {}
        for instrument, terms in by_instrument.items():
            value, detail = evaluate(terms, series_by_key, measure, instrument)
            vals[instrument] = value
            details[instrument] = detail
        if all(vals[k] is not None for k in ("F51", "F511", "F512", "F519")):
            residual = (
                float(vals["F51"]) - float(vals["F511"])
                - float(vals["F512"]) - float(vals["F519"])
            )
            status = "PASS" if abs(residual) <= TOL else "FAIL"
        else:
            residual = None
            status = "CONTROL_INCOMPLETE"
        sector_decomposition.append({
            "measure": "stock" if measure == "LE" else "flow",
            "sector": sector,
            "entry": entry,
            **{f"{k}_million_RON": v for k, v in vals.items()},
            "residual_F51_minus_components_million_RON": residual,
            "status": status,
            "terms": details,
        })

    total_decomposition = []
    total_f5_lookup = {}
    for measure, area, entry, by_instrument in total_controls:
        vals = {}
        details = {}
        for instrument, terms in by_instrument.items():
            value, detail = evaluate(terms, series_by_key, measure, instrument)
            vals[instrument] = value
            details[instrument] = detail
        if all(vals[k] is not None for k in ("F51", "F511", "F512", "F519")):
            residual = (
                float(vals["F51"]) - float(vals["F511"])
                - float(vals["F512"]) - float(vals["F519"])
            )
            status = "PASS" if abs(residual) <= TOL else "FAIL"
        else:
            residual = None
            status = "CONTROL_INCOMPLETE"
        label = "stock" if measure == "LE" else "flow"
        total_decomposition.append({
            "measure": label,
            "area": area,
            "entry": entry,
            **{f"{k}_million_RON": v for k, v in vals.items()},
            "residual_F51_minus_components_million_RON": residual,
            "status": status,
            "terms": details,
        })
        total_f5_lookup[(label, area, entry)] = vals["F5"]

    reconciliation = []
    for label in ("stock", "flow"):
        for sector in RESIDENT:
            for kind, entry in (("holder_total", "A"), ("issuer_total", "L")):
                related = [
                    c for c in cells
                    if c["measure"] == label
                    and (
                        c["holder"] == sector if kind == "holder_total"
                        else c["issuer"] == sector
                    )
                    and c["status"] != "OUTSIDE_BOUNDARY_NOT_APPLICABLE"
                ]
                complete = all(c["status"] == "EXACT_F51_PLUS_F52_DERIVATION" for c in related)
                bilateral = (
                    sum(float(c["value_million_RON"]) for c in related)
                    if complete else None
                )
                measure_code = "LE" if label == "stock" else "F"
                official, detail = evaluate(
                    aggregate_terms(sector, entry, measure_code, "F5"),
                    series_by_key, measure_code, "F5"
                )
                residual = None if bilateral is None or official is None else bilateral - float(official)
                status = (
                    "CONTROL_UNAVAILABLE" if official is None
                    else "BILATERAL_COVERAGE_INCOMPLETE" if not complete
                    else "PASS" if abs(float(residual)) <= TOL
                    else "FAIL"
                )
                reconciliation.append({
                    "measure": label, "kind": kind, "sector": sector,
                    "bilateral_complete": complete,
                    "bilateral_sum_million_RON": bilateral,
                    "official_F5_aggregate_million_RON": official,
                    "residual_million_RON": residual,
                    "status": status,
                    "terms": detail,
                })

    external_controls = []
    for label in ("stock", "flow"):
        for kind, related, entry in (
            ("resident_holder_to_X",
             [c for c in cells if c["measure"] == label and c["issuer"] == "X" and c["holder"] in RESIDENT],
             "A"),
            ("X_holder_to_resident_issuer",
             [c for c in cells if c["measure"] == label and c["holder"] == "X" and c["issuer"] in RESIDENT],
             "L"),
        ):
            complete = all(c["status"] == "EXACT_F51_PLUS_F52_DERIVATION" for c in related)
            bilateral = (
                sum(float(c["value_million_RON"]) for c in related)
                if complete else None
            )
            official = total_f5_lookup[(label, "W1", entry)]
            residual = None if bilateral is None or official is None else bilateral - float(official)
            status = (
                "CONTROL_UNAVAILABLE" if official is None
                else "BILATERAL_COVERAGE_INCOMPLETE" if not complete
                else "PASS" if abs(float(residual)) <= TOL
                else "FAIL"
            )
            external_controls.append({
                "measure": label, "kind": kind,
                "bilateral_complete": complete,
                "bilateral_sum_million_RON": bilateral,
                "published_W1_F5_million_RON": official,
                "residual_million_RON": residual,
                "status": status,
            })

    report = {
        "audit_version": "0.1",
        "instrument": "F5",
        "phase": "bilateral F51 subcomponent bridge",
        "benchmark_changed": False,
        "materialization_allowed_by_this_phase": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": dict(Counter(str(x.get("status")) for x in series_by_key.values())),
        "equity_component_cell_status_counts": {
            c: dict(equity_component_counts[c]) for c in EQUITY_COMPONENTS
        },
        "derived_F51_cell_status_counts": dict(f51_counts),
        "F52_cell_status_counts": dict(f52_counts),
        "derived_F5_cell_status_counts": dict(total_f5_counts),
        "sector_F51_decomposition_status_counts": dict(Counter(x["status"] for x in sector_decomposition)),
        "total_F51_decomposition_status_counts": dict(Counter(x["status"] for x in total_decomposition)),
        "reconciliation_status_counts": dict(Counter(x["status"] for x in reconciliation)),
        "external_control_status_counts": dict(Counter(x["status"] for x in external_controls)),
        "network_errors_present": any(
            x.get("status") == "NETWORK_ERROR" for x in series_by_key.values()
        ),
        "cells": cells,
        "sector_F51_equals_components_controls": sector_decomposition,
        "total_F51_equals_components_controls": total_decomposition,
        "aggregate_F5_reconciliation": reconciliation,
        "external_F5_controls": external_controls,
        "rule": (
            "F51 is derived only as exact F511+F512+F519 when all three bilateral "
            "subcomponents are separately resolved without orientation conflict. "
            "No new issuer-zero rule is introduced for F511/F512/F519. F52 uses "
            "only the already established Phase B investment-fund issuer scope."
        ),
    }

    (OUT / "f5_equity_subcomponent_bridge_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "series_requested": report["series_requested"],
        "series_status_counts": report["series_status_counts"],
        "equity_component_cell_status_counts": report["equity_component_cell_status_counts"],
        "derived_F51_cell_status_counts": report["derived_F51_cell_status_counts"],
        "F52_cell_status_counts": report["F52_cell_status_counts"],
        "derived_F5_cell_status_counts": report["derived_F5_cell_status_counts"],
        "sector_F51_decomposition_status_counts": report["sector_F51_decomposition_status_counts"],
        "total_F51_decomposition_status_counts": report["total_F51_decomposition_status_counts"],
        "network_errors_present": report["network_errors_present"],
    }, indent=2))


if __name__ == "__main__":
    main()
