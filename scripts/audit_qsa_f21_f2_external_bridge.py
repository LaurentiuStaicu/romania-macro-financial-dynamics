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

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("F21_BRIDGE_OUT", "f21_bridge_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F21 F2 bridge audit)"
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
    return COMPOSITE[sector]


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
            "Q", "N", "RO", area, ref, cp, "N", entry, measure, instrument,
            "T", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def holder_terms(
    sector: str, area: str, measure: str, instrument: str
) -> tuple[Term, ...]:
    return tuple(
        Term(coeff, key(area, code, "S1", "A", measure, instrument))
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
                    "attempts": attempt,
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
        if not row.get("TIME_PERIOD") or row.get("OBS_VALUE") in (None, ""):
            continue
        try:
            numeric = float(row["OBS_VALUE"])
        except ValueError:
            continue
        parsed.append(
            {
                "period": row["TIME_PERIOD"],
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


def period_values(
    series: dict[str, object], measure: str, instrument: str
) -> list[float] | None:
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != instrument
        or row.get("entry") != "A"
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
        vals = period_values(series_by_key[term.key], measure, instrument)
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


def component_external_f2m() -> dict[tuple[str, str], float]:
    component = json.loads(
        (ROOT / "model" / "accounting" / "f2m_component_2025.json").read_text(
            encoding="utf-8"
        )
    )
    if component["instrument"] != "F2M":
        raise RuntimeError("Unexpected component input")
    out = {}
    for measure in ("stock", "flow"):
        for cell in component["matrices"][measure]:
            if cell["issuer"] == "X" and cell["holder"] in RESIDENT:
                if cell["status"] != "DERIVED" or cell["value"] is None:
                    raise RuntimeError(f"F2M external input not materialized: {cell}")
                out[(measure, cell["holder"])] = float(cell["value"])
    if len(out) != 10:
        raise RuntimeError("Expected ten materialized holder-specific external F2M cells")
    return out


def main() -> None:
    f2m_external = component_external_f2m()
    required: set[str] = set()
    plans = []

    for measure in ("LE", "F"):
        for holder in RESIDENT:
            f2_terms = holder_terms(holder, "W1", measure, "F2")
            f21_w0_terms = holder_terms(holder, "W0", measure, "F21")
            plans.append((measure, holder, f2_terms, f21_w0_terms))
            required.update(t.key for t in f2_terms)
            required.update(t.key for t in f21_w0_terms)

        for series_key in (
            key("W1", "S1", "S1", "A", measure, "F2"),
            key("W1", "S1", "S1", "A", measure, "F21"),
            key("W0", "S1", "S1", "A", measure, "F21"),
            key("W0", "S1", "S1", "L", measure, "F21"),
            key("W0", "S121", "S1", "L", measure, "F21"),
        ):
            required.add(series_key)

    series_by_key = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch, k): k for k in sorted(required)}
        for index, future in enumerate(as_completed(futures), start=1):
            k = futures[future]
            series_by_key[k] = future.result()
            print(f"[{index}/{len(futures)}] {k}", flush=True)

    holder_results = []
    bridge_complete = True
    any_network_error = any(
        s.get("status") == "NETWORK_ERROR" for s in series_by_key.values()
    )

    for measure, holder, f2_terms, f21_w0_terms in plans:
        label = "stock" if measure == "LE" else "flow"
        f2_w1, f2_detail = evaluate(f2_terms, series_by_key, measure, "F2")
        f21_w0, f21_detail = evaluate(f21_w0_terms, series_by_key, measure, "F21")
        f2m_w1 = f2m_external[(label, holder)]
        if f2_w1 is None or f21_w0 is None:
            bridge_complete = False
            external_f21 = None
            domestic_f21 = None
            status = "SOURCE_COVERAGE_BLOCKED"
        else:
            external_f21 = f2_w1 - f2m_w1
            domestic_f21 = f21_w0 - external_f21
            status = "EXACT_IDENTITY_DERIVATION_CANDIDATE"
        holder_results.append(
            {
                "measure": label,
                "holder": holder,
                "status": status,
                "W1_F2_million_RON": f2_w1,
                "W1_F2_terms": f2_detail,
                "materialized_W1_F2M_million_RON": f2m_w1,
                "derived_W1_F21_million_RON": external_f21,
                "W0_F21_holder_assets_million_RON": f21_w0,
                "W0_F21_terms": f21_detail,
                "implied_domestic_F21_million_RON": domestic_f21,
            }
        )

    controls = []
    all_controls_pass = bridge_complete and not any_network_error
    for measure in ("LE", "F"):
        label = "stock" if measure == "LE" else "flow"
        rows = [x for x in holder_results if x["measure"] == label]

        def direct(area: str, entry: str, instrument: str, ref: str = "S1"):
            k = key(area, ref, "S1", entry, measure, instrument)
            vals = period_values(series_by_key[k], measure, instrument)
            if vals is None:
                return None
            return vals[0] if measure == "LE" else sum(vals)

        total_w1_f2 = direct("W1", "A", "F2")
        total_w1_f21 = direct("W1", "A", "F21")
        total_w0_f21_assets = direct("W0", "A", "F21")
        total_w0_f21_liabilities = direct("W0", "L", "F21")
        bnr_w0_f21_liabilities = direct("W0", "L", "F21", ref="S121")

        if bridge_complete:
            sum_w1_f2 = sum(float(x["W1_F2_million_RON"]) for x in rows)
            sum_w1_f21 = sum(float(x["derived_W1_F21_million_RON"]) for x in rows)
            sum_domestic_f21 = sum(float(x["implied_domestic_F21_million_RON"]) for x in rows)
            sum_w0_f21 = sum(float(x["W0_F21_holder_assets_million_RON"]) for x in rows)
        else:
            sum_w1_f2 = sum_w1_f21 = sum_domestic_f21 = sum_w0_f21 = None

        checks = [
            ("holder_W1_F2_vs_total_W1_F2", sum_w1_f2, total_w1_f2),
            ("derived_W1_F21_vs_total_W1_F21", sum_w1_f21, total_w1_f21),
            ("holder_W0_F21_vs_total_W0_F21_assets", sum_w0_f21, total_w0_f21_assets),
            ("implied_domestic_F21_vs_total_W0_F21_liabilities", sum_domestic_f21, total_w0_f21_liabilities),
            ("implied_domestic_F21_vs_BNR_W0_F21_liabilities", sum_domestic_f21, bnr_w0_f21_liabilities),
        ]
        for name, lhs, rhs in checks:
            residual = None if lhs is None or rhs is None else lhs - rhs
            status = (
                "CONTROL_UNAVAILABLE"
                if residual is None
                else "PASS"
                if abs(residual) <= TOL
                else "FAIL"
            )
            if status != "PASS":
                all_controls_pass = False
            controls.append(
                {
                    "measure": label,
                    "check": name,
                    "left_million_RON": lhs,
                    "right_million_RON": rhs,
                    "residual_million_RON": residual,
                    "status": status,
                }
            )

    report = {
        "audit_version": "0.1",
        "phase": "F21 external instrument bridge",
        "benchmark_changed": False,
        "total_F2_materialization_allowed": False,
        "behavioural_closure_changed": False,
        "series_requested": len(required),
        "series_status_counts": {},
        "network_errors_present": any_network_error,
        "holder_results": holder_results,
        "controls": controls,
        "all_holder_bridges_available": bridge_complete,
        "all_required_controls_pass": all_controls_pass,
        "promotion_status": (
            "HOLDER_SPECIFIC_EXTERNAL_F21_ELIGIBLE_FOR_LATER_MATERIALIZATION"
            if all_controls_pass
            else "F21_EXTERNAL_BRIDGE_REMAINS_BLOCKED"
        ),
        "rule": "No value is written to the benchmark. F21 is derived only by the exact F2-F2M instrument identity when all source dimensions and aggregate controls pass.",
    }
    for series in series_by_key.values():
        status = str(series.get("status"))
        report["series_status_counts"][status] = (
            report["series_status_counts"].get(status, 0) + 1
        )

    (OUT / "f21_f2_external_bridge_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_requested": report["series_requested"],
                "series_status_counts": report["series_status_counts"],
                "all_holder_bridges_available": bridge_complete,
                "all_required_controls_pass": all_controls_pass,
                "promotion_status": report["promotion_status"],
                "controls": controls,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
