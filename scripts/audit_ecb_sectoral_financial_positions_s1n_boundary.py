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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "SECTORAL_POSITIONS_S1N_AUDIT_OUT",
        "sectoral_positions_s1n_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub S1N sectoral-position boundary diagnostic)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def s1n_key(entry: str, measure: str, instrument: str) -> str:
    if entry not in {"A", "L"}:
        raise ValueError(entry)
    if measure not in {"LE", "F"}:
        raise ValueError(measure)
    if instrument not in {"F", "F1"}:
        raise ValueError(instrument)
    return ".".join(
        (
            "Q", "N", "RO", "W0", "S1N", "S1", "N",
            entry, measure, instrument, "_Z", "_Z",
            "XDC", "_T", "S", "V", "N", "_T",
        )
    )


def corrected_residual(
    historical_residual: float,
    s1n_net_position: float,
) -> float:
    return float(historical_residual) + float(s1n_net_position)


def explanation_passes(
    historical_residuals: dict[str, float],
    s1n_net_positions: dict[str, float],
    envelope: float,
    epsilon: float,
) -> tuple[bool, dict[str, dict[str, float | bool]]]:
    details: dict[str, dict[str, float | bool]] = {}
    passed = True
    for period, old in historical_residuals.items():
        if period not in s1n_net_positions:
            passed = False
            details[period] = {
                "historical_residual_million_RON": old,
                "s1n_available": False,
            }
            continue
        s1n = s1n_net_positions[period]
        corrected = corrected_residual(old, s1n)
        within = abs(corrected) <= envelope + epsilon
        passed = passed and within
        details[period] = {
            "historical_residual_million_RON": old,
            "s1n_net_position_million_RON": s1n,
            "corrected_residual_million_RON": corrected,
            "within_frozen_phase_C_envelope": within,
            "s1n_available": True,
        }
    return passed, details


def fetch(series_key: str, start: str, end: str) -> dict[str, object]:
    query = urllib.parse.urlencode(
        {"startPeriod": start, "endPeriod": end, "format": "csvdata"}
    )
    url = f"{API}{series_key}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,application/vnd.sdmx.data+csv;version=1.0.0",
        },
    )
    body = b""
    status = 0
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
                time.sleep(float(attempt * 2))
                continue
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 3:
                time.sleep(float(attempt * 2))
                continue
            return {
                "key": series_key,
                "url": url,
                "status": "NETWORK_ERROR",
                "error": str(exc),
                "observations": {},
            }

    raw_path = OUT / "raw" / f"{sha256(series_key.encode())[:20]}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": series_key,
        "url": url,
        "http_status": status,
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "observations": {},
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        return result

    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    observations: dict[str, float] = {}
    duplicates: list[str] = []
    for row in reader:
        period = str(row.get("TIME_PERIOD", "")).strip()
        raw_value = str(row.get("OBS_VALUE", "")).strip()
        if not period or raw_value in {"", "NaN", "nan"}:
            continue
        value = float(raw_value)
        if not math.isfinite(value):
            result["status"] = "NON_FINITE"
            result["period"] = period
            return result
        if period in observations:
            duplicates.append(period)
        observations[period] = value

    result["status"] = (
        "AVAILABLE" if observations and not duplicates else "SERIES_INCOMPLETE"
    )
    result["duplicate_periods"] = duplicates
    result["observations"] = observations
    return result


def obs(result: dict[str, object]) -> dict[str, float] | None:
    if result.get("status") != "AVAILABLE":
        return None
    return {str(k): float(v) for k, v in result["observations"].items()}


def represented_net(
    results: dict[str, dict[str, object]],
    measure: str,
) -> tuple[dict[str, float] | None, dict[str, str]]:
    sides: dict[str, dict[str, float]] = {}
    statuses: dict[str, str] = {}
    for entry in ("A", "L"):
        total_key = s1n_key(entry, measure, "F")
        f1_key = s1n_key(entry, measure, "F1")
        total = obs(results[total_key])
        f1 = obs(results[f1_key])
        if total is None:
            statuses[entry] = f"missing:{total_key}"
            continue
        if f1 is None:
            statuses[entry] = f"missing:{f1_key}"
            continue
        common = sorted(set(total) & set(f1))
        sides[entry] = {p: total[p] - f1[p] for p in common}
        statuses[entry] = "F_MINUS_F1"

    if set(sides) != {"A", "L"}:
        return None, statuses
    common = sorted(set(sides["A"]) & set(sides["L"]))
    return (
        {p: sides["A"][p] - sides["L"][p] for p in common},
        statuses,
    )


def main() -> None:
    contract = load_json(
        "model/dynamics/"
        "sectoral_financial_positions_s1n_boundary_diagnostic_contract.json"
    )
    phase_c = load_json(
        "model/dynamics/"
        "sectoral_financial_positions_rounding_consistency_assessment.json"
    )
    phase_d = load_json(
        "model/dynamics/"
        "sectoral_financial_positions_source_discrepancy_assessment.json"
    )

    envelope = float(
        phase_c["precision_gate"]["rounding_envelope_million_RON"]
    )
    frozen = float(
        contract["historical_diagnostic_basis"][
            "frozen_source_precision_envelope_million_RON"
        ]
    )
    if envelope != frozen:
        raise RuntimeError(
            "Phase C envelope no longer matches frozen S1N diagnostic contract"
        )

    start = contract["source"]["requested_start"]
    end = contract["source"]["requested_end"]
    required = {
        s1n_key(entry, measure, instrument)
        for entry in ("A", "L")
        for measure in ("LE", "F")
        for instrument in ("F", "F1")
    }
    if len(required) != contract["source"]["required_series_count"]:
        raise RuntimeError("unexpected S1N series count")

    results: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch, key, start, end): key
            for key in sorted(required)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            key = futures[future]
            results[key] = future.result()
            print(
                f"[{index}/{len(futures)}] "
                f"{results[key].get('status')} {key}",
                flush=True,
            )

    status_counts = dict(
        Counter(str(item.get("status")) for item in results.values())
    )
    network_errors = [
        key for key, item in results.items()
        if item.get("status") == "NETWORK_ERROR"
    ]

    nets: dict[str, dict[str, float] | None] = {}
    side_statuses: dict[str, dict[str, str]] = {}
    coverage: dict[str, dict[str, object]] = {}
    required_2025 = set(contract["coverage_gate"]["required_benchmark_periods"])
    minimum_count = int(
        contract["coverage_gate"]["minimum_common_observation_count"]
    )

    for label, measure in (("stock", "LE"), ("flow", "F")):
        net, statuses = represented_net(results, measure)
        nets[label] = net
        side_statuses[label] = statuses
        periods = set(net or {})
        coverage[label] = {
            "available": net is not None,
            "common_observation_count": len(periods),
            "first_period": min(periods) if periods else None,
            "last_period": max(periods) if periods else None,
            "missing_required_2025_periods": sorted(required_2025 - periods),
            "minimum_common_observation_count_pass": len(periods) >= minimum_count,
        }

    coverage_pass = all(
        item["available"]
        and item["minimum_common_observation_count_pass"]
        and not item["missing_required_2025_periods"]
        for item in coverage.values()
    ) and all(
        result.get("status") == "AVAILABLE" for result in results.values()
    )

    historical = {
        period: float(values["resident_additivity"])
        for period, values in phase_d["localization"]["stock"][
            "phase_C_failing_periods"
        ].items()
    }
    expected_periods = set(
        contract["historical_diagnostic_basis"][
            "phase_C_failing_stock_periods"
        ]
    )
    if set(historical) != expected_periods:
        raise RuntimeError(
            "Historical Phase D failing-period residual set differs from frozen contract"
        )

    stock_net = nets["stock"] or {}
    epsilon = float(
        contract["explanatory_gate"]["computational_epsilon_million_RON"]
    )
    explanatory_pass, explanation = explanation_passes(
        historical,
        stock_net,
        envelope,
        epsilon,
    )

    if not coverage_pass:
        disposition = "NO_REOPEN_EVIDENCE_FROM_S1N"
    elif explanatory_pass:
        disposition = "S1N_EXPLANATORY_CANDIDATE_REOPEN_TRIGGER_ONLY"
    else:
        disposition = "S1N_PUBLISHED_BUT_DOES_NOT_EXPLAIN_FROZEN_RESIDUALS"

    report = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "reference_mode": "sectoral_financial_positions",
        "formal_reference_mode_gate": False,
        "source": {
            "series_requested": len(required),
            "series_status_counts": status_counts,
            "network_errors": network_errors,
        },
        "side_statuses": side_statuses,
        "coverage": coverage,
        "coverage_gate_pass": coverage_pass,
        "frozen_phase_C_envelope_million_RON": envelope,
        "historical_phase_D_residuals_million_RON": historical,
        "stock_explanation": explanation,
        "explanatory_gate_pass": explanatory_pass if coverage_pass else False,
        "disposition": disposition,
        "promotion_eligible": False,
        "readiness_count_change": 0,
        "historical_A_D_reinterpreted": False,
        "accounting_readiness_changed": False,
        "behavioural_closure_changed": False,
        "interpretation": (
            "Post-run boundary diagnostic only. Even a positive S1N explanation "
            "is only evidence that a new formal reference-boundary retest may "
            "be preregistered; it cannot promote the mode or rewrite A-D."
        ),
        "source_results": results,
    }

    path = OUT / "sectoral_financial_positions_s1n_boundary_diagnostic.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "coverage": coverage,
        "coverage_gate_pass": coverage_pass,
        "explanatory_gate_pass": report["explanatory_gate_pass"],
        "disposition": disposition,
        "promotion_eligible": False,
    }, indent=2))

    if network_errors:
        raise SystemExit("S1N live-source diagnostic encountered network errors")
    if not coverage_pass:
        raise SystemExit(
            "S1N source coverage gate did not pass; retained diagnostic is negative"
        )


if __name__ == "__main__":
    main()
