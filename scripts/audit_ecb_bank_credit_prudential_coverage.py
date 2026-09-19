from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "BANK_CREDIT_PRUDENTIAL_OUT",
        "bank_credit_prudential_artifacts",
    )
)
API = "https://data-api.ecb.europa.eu/service/data/CBD2/"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub bank-credit prudential source coverage)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_flow(full_key: str) -> str:
    prefix = "CBD2."
    if not full_key.startswith(prefix):
        raise ValueError(full_key)
    return full_key[len(prefix):]


def parse_csv(body: bytes) -> dict[str, float]:
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    fields = set(reader.fieldnames or [])
    if not {"TIME_PERIOD", "OBS_VALUE"}.issubset(fields):
        raise ValueError("CBD2 CSV missing TIME_PERIOD/OBS_VALUE")
    out: dict[str, float] = {}
    for row in reader:
        period = str(row.get("TIME_PERIOD") or "").strip()
        raw = str(row.get("OBS_VALUE") or "").strip()
        if not period or raw in {"", "NaN", "nan"}:
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite value {raw!r} at {period}")
        if period in out:
            raise ValueError(f"duplicate period {period}")
        out[period] = value
    return out


def fetch(full_key: str, start_period: str) -> dict[str, object]:
    key = strip_flow(full_key)
    query = urllib.parse.urlencode(
        {"startPeriod": start_period, "format": "csvdata"}
    )
    url = f"{API}{key}?{query}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
    )
    body = b""
    status = 0
    network_error: str | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
                status = int(response.status)
            break
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
            if status in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(2 * attempt)
                continue
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            network_error = str(exc)
            if attempt < 3:
                time.sleep(2 * attempt)
                continue
            break

    raw_name = sha256(full_key.encode("utf-8"))[:20] + ".csv"
    raw_path = OUT / "raw" / raw_name
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "series_key": full_key,
        "url": url,
        "http_status": status,
        "network_error": network_error,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "observations": {},
    }
    if network_error:
        result["status"] = "NETWORK_ERROR"
        return result
    if status != 200:
        result["status"] = "HTTP_ERROR"
        return result
    try:
        observations = parse_csv(body)
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result
    result["observations"] = observations
    result["status"] = "AVAILABLE" if observations else "EMPTY"
    result["first_period"] = min(observations) if observations else None
    result["last_period"] = max(observations) if observations else None
    result["observation_count"] = len(observations)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(
        (
            ROOT
            / "model"
            / "calibration_validation"
            / "bank_credit_prudential_coverage_contract.json"
        ).read_text(encoding="utf-8")
    )
    candidates = contract["source"]["candidate_series"]
    start = contract["source"]["start_period"]
    results = {
        name: fetch(spec["full_series_key"], start)
        for name, spec in candidates.items()
    }

    anchors = contract["bnr_semantic_anchor"]["diagnostic_values"]
    comparisons: dict[str, dict[str, object]] = {}
    mapping = {
        "npl_ratio": "npl_ratio_pct",
        "solvency_ratio": "total_capital_ratio_pct",
        "cet1_ratio": "cet1_ratio_pct",
    }
    for series_name, anchor_field in mapping.items():
        observations = results[series_name].get("observations") or {}
        rows: dict[str, object] = {}
        for period, anchor in anchors.items():
            if period in observations:
                value = float(observations[period])
                rows[period] = {
                    "cbd2_pct": value,
                    "bnr_anchor_pct": float(anchor[anchor_field]),
                    "cbd2_minus_bnr_pp": value - float(anchor[anchor_field]),
                }
            else:
                rows[period] = {"cbd2_available": False}
        comparisons[series_name] = rows

    npl_available = results["npl_ratio"].get("status") == "AVAILABLE"
    solvency_available = (
        results["solvency_ratio"].get("status") == "AVAILABLE"
    )
    cet1_available = results["cet1_ratio"].get("status") == "AVAILABLE"

    if not npl_available:
        disposition = "NPL_EXPECTED_SOURCE_NOT_AVAILABLE_NO_CALIBRATION"
    elif solvency_available:
        disposition = (
            "QUARTERLY_SOLVENCY_SOURCE_AVAILABLE_BOUNDARY_BRIDGE_PENDING"
        )
    else:
        disposition = (
            "SOLVENCY_SOURCE_UNRESOLVED_CET1_SUBSTITUTION_NOT_AUTHORIZED"
        )

    report = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "formal_calibration_gate": False,
        "results": results,
        "bnr_diagnostic_comparisons": comparisons,
        "availability": {
            "npl_ratio": npl_available,
            "solvency_ratio": solvency_available,
            "cet1_ratio": cet1_available,
        },
        "disposition": disposition,
        "calibration_cycle_open": False,
        "validated_reference_behavioural_mechanisms_change": 0,
        "central_feedback_activation": False,
        "hard_rules": contract["hard_rules"],
    }
    (OUT / "bank_credit_prudential_coverage_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "availability": report["availability"],
                "disposition": disposition,
                "calibration_cycle_open": False,
            },
            indent=2,
        )
    )
    if any(
        item.get("status") == "NETWORK_ERROR"
        for item in results.values()
    ):
        raise SystemExit("live-provider network error; retained evidence only")


if __name__ == "__main__":
    main()
