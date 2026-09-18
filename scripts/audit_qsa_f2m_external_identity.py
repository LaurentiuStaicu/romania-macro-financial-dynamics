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
from pathlib import Path

IN_DIR = Path(os.environ.get("F2M_AUDIT_IN", "f2m_audit_artifacts"))
OUT = Path(os.environ.get("F2M_EXTERNAL_AUDIT_OUT", "f2m_external_audit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub F2M external identity audit)"
TOL = 0.1
RESIDENT_HOLDERS = ("H", "C", "F", "G", "BNR")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def key(area: str, measure: str) -> str:
    return ".".join(
        (
            "Q", "N", "RO", area, "S1", "S1", "N", "A", measure, "F2M",
            "T", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


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
                "counterpart_area": row.get("COUNTERPART_AREA"),
                "reference_sector": row.get("REF_SECTOR"),
                "counterpart_sector": row.get("COUNTERPART_SECTOR")
            }
        )
    result["rows"] = parsed
    result["status"] = "AVAILABLE" if parsed else "NO_OBSERVATIONS"
    return result


def period_value(series: dict[str, object], measure: str) -> float | None:
    if series.get("status") != "AVAILABLE":
        return None
    rows = series.get("rows", [])
    if any(
        row.get("unit") != "XDC"
        or str(row.get("unit_mult")) != "6"
        or row.get("instrument") != "F2M"
        or row.get("entry") != "A"
        for row in rows
    ):
        return None
    mapping = {str(row["period"]): float(row["value"]) for row in rows}
    if measure == "LE":
        value = mapping.get("2025-Q4")
        return value if value is not None and math.isfinite(value) else None
    periods = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
    if not all(p in mapping and math.isfinite(mapping[p]) for p in periods):
        return None
    return sum(mapping[p] for p in periods)


def main() -> None:
    phase_a1_path = IN_DIR / "f2m_deposit_coverage_audit.json"
    phase_a1 = json.loads(phase_a1_path.read_text(encoding="utf-8"))

    aggregates = {}
    for measure in ("LE", "F"):
        for area in ("W0", "W2", "W1"):
            series_key = key(area, measure)
            print(f"{measure} {area}: {series_key}", flush=True)
            aggregates[(measure, area)] = fetch(series_key)

    measure_results = []
    complement_candidates = []

    for measure, label in (("LE", "stock"), ("F", "flow")):
        values = {
            area: period_value(aggregates[(measure, area)], measure)
            for area in ("W0", "W2", "W1")
        }
        direct_area_residual = (
            None
            if any(values[area] is None for area in ("W0", "W2", "W1"))
            else values["W0"] - values["W2"] - values["W1"]
        )
        direct_area_status = (
            "CONTROL_UNAVAILABLE"
            if direct_area_residual is None
            else "PASS"
            if abs(direct_area_residual) <= TOL
            else "FAIL"
        )

        domestic_cells = [
            cell
            for cell in phase_a1["cells"]
            if cell["measure"] == label
            and cell["holder"] in RESIDENT_HOLDERS
            and cell["issuer"] in RESIDENT_HOLDERS
            and cell["value_million_RON"] is not None
        ]
        domestic_bilateral_sum = sum(
            float(cell["value_million_RON"]) for cell in domestic_cells
        )
        implied_domestic_control = (
            None
            if values["W0"] is None or values["W1"] is None
            else float(values["W0"]) - float(values["W1"])
        )
        implied_domestic_residual = (
            None
            if implied_domestic_control is None
            else domestic_bilateral_sum - implied_domestic_control
        )
        implied_domestic_status = (
            "CONTROL_UNAVAILABLE"
            if implied_domestic_residual is None
            else "PASS"
            if abs(implied_domestic_residual) <= TOL
            else "FAIL"
        )

        holder_controls = [
            item for item in phase_a1["aggregate_reconciliation"]
            if item["measure"] == label and item["kind"] == "holder_total"
        ]

        for holder in RESIDENT_HOLDERS:
            item = next(x for x in holder_controls if x["sector"] == holder)
            official = item["official_aggregate_million_RON"]
            bilateral = item["bilateral_sum_million_RON"]
            candidate = (
                None
                if official is None
                else float(official) - float(bilateral)
            )
            complement_candidates.append(
                {
                    "measure": label,
                    "holder": holder,
                    "issuer": "X",
                    "candidate_value_million_RON": candidate,
                    "status": "DERIVATION_CANDIDATE_ONLY" if candidate is not None else "UNRESOLVED",
                    "source_identity": "holder_W0_F2M_assets - complete_resident_issuer_F2M_submatrix"
                }
            )

        candidates = [
            x["candidate_value_million_RON"]
            for x in complement_candidates
            if x["measure"] == label and x["candidate_value_million_RON"] is not None
        ]
        candidate_sum = sum(float(x) for x in candidates) if len(candidates) == len(RESIDENT_HOLDERS) else None
        external_control = values["W1"]
        external_residual = (
            None
            if candidate_sum is None or external_control is None
            else candidate_sum - external_control
        )
        external_status = (
            "CONTROL_UNAVAILABLE"
            if external_residual is None
            else "PASS"
            if abs(external_residual) <= TOL
            else "FAIL"
        )

        measure_results.append(
            {
                "measure": label,
                "qsa_total_economy": values,
                "direct_W2_published": values["W2"] is not None,
                "direct_area_partition_residual_million_RON": direct_area_residual,
                "direct_area_partition_status": direct_area_status,
                "independent_domestic_bilateral_sum_million_RON": domestic_bilateral_sum,
                "implied_domestic_W0_minus_W1_million_RON": implied_domestic_control,
                "independent_domestic_partition_residual_million_RON": implied_domestic_residual,
                "independent_domestic_partition_status": implied_domestic_status,
                "sum_holder_complement_candidates_million_RON": candidate_sum,
                "published_W1_total_economy_million_RON": external_control,
                "holder_complements_vs_W1_residual_million_RON": external_residual,
                "holder_complements_vs_W1_status": external_status,
            }
        )

    all_gates_pass = all(
        item["independent_domestic_partition_status"] == "PASS"
        and item["holder_complements_vs_W1_status"] == "PASS"
        and (
            item["direct_area_partition_status"] in {"PASS", "CONTROL_UNAVAILABLE"}
        )
        for item in measure_results
    )

    report = {
        "audit_version": "0.2",
        "purpose": "Test whether F2M resident-holder→X values are uniquely derivable from QSA accounting partitions rather than synthetically allocated.",
        "benchmark_changed": False,
        "tolerance_million_RON": TOL,
        "phase_a1_cell_status_counts": phase_a1["cell_status_counts"],
        "aggregate_series": [
            aggregates[(measure, area)]
            for measure in ("LE", "F")
            for area in ("W0", "W2", "W1")
        ],
        "measure_results": measure_results,
        "complement_candidates": complement_candidates,
        "all_required_identity_controls_pass": all_gates_pass,
        "promotion_status": (
            "EXACT_COMPLEMENT_DERIVATION_ELIGIBLE_FOR_LATER_MATERIALIZATION"
            if all_gates_pass
            else "EXTERNAL_F2M_REMAINS_UNRESOLVED"
        ),
        "rule": "No candidate value is written to the benchmark by this audit. When direct W2 total-economy publication is unavailable, the independent domestic control is the observed/derived domestic bilateral sum versus published W0 minus published W1; holder→X candidates are excluded from that control."
    }

    (OUT / "f2m_external_identity_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "measure_results": measure_results,
        "all_required_identity_controls_pass": all_gates_pass,
        "promotion_status": report["promotion_status"],
    }, indent=2))


if __name__ == "__main__":
    main()
