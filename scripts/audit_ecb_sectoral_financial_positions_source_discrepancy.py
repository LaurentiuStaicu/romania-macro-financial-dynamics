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
        "SECTORAL_POSITIONS_PHASE_D_AUDIT_OUT",
        "sectoral_positions_phase_d_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub sectoral-financial-positions Phase D diagnostic)"
)
REQUIRED_2025 = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
COMPUTATIONAL_EPSILON = 1e-9


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def key(area: str, ref: str, entry: str, measure: str, instrument: str) -> str:
    return ".".join(
        (
            "Q", "N", "RO", area, ref, "S1", "N", entry, measure,
            instrument, "_Z", "_Z", "XDC", "_T", "S", "V", "N", "_T",
        )
    )


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


def represented(
    results: dict[str, dict[str, object]],
    area: str,
    code: str,
    entry: str,
    measure: str,
    f1_optional_structural: bool,
) -> tuple[dict[str, float] | None, str]:
    total_key = key(area, code, entry, measure, "F")
    f1_key = key(area, code, entry, measure, "F1")
    total = obs(results[total_key])
    f1 = obs(results[f1_key])
    if total is None:
        return None, f"missing:{total_key}"
    if f1 is None:
        if f1_optional_structural:
            return total, "F1_STRUCTURAL_NOT_APPLICABLE"
        return None, f"missing:{f1_key}"
    common = sorted(set(total) & set(f1))
    return {p: total[p] - f1[p] for p in common}, "F_MINUS_F1"


def net_series(
    results: dict[str, dict[str, object]],
    area: str,
    code: str,
    measure: str,
    f1_optional_structural: bool,
) -> tuple[dict[str, float] | None, dict[str, str]]:
    assets, a_status = represented(
        results, area, code, "A", measure, f1_optional_structural
    )
    liabilities, l_status = represented(
        results, area, code, "L", measure, f1_optional_structural
    )
    if assets is None or liabilities is None:
        return None, {"assets": a_status, "liabilities": l_status}
    common = sorted(set(assets) & set(liabilities))
    return (
        {p: assets[p] - liabilities[p] for p in common},
        {"assets": a_status, "liabilities": l_status},
    )


def combine(terms: list[tuple[float, dict[str, float]]]) -> dict[str, float]:
    common = set(terms[0][1])
    for _, values in terms[1:]:
        common &= set(values)
    return {
        p: sum(coeff * values[p] for coeff, values in terms)
        for p in sorted(common)
    }


def main() -> None:
    contract = load_json(
        "model/dynamics/sectoral_financial_positions_source_discrepancy_contract.json"
    )
    phase_c = load_json(
        "model/dynamics/sectoral_financial_positions_rounding_consistency_assessment.json"
    )
    if phase_c["verdict"] != contract["prerequisites"]["required_phase_C_verdict"]:
        raise RuntimeError("Phase C verdict does not satisfy Phase D prerequisite")

    start = contract["source"]["requested_start"]
    end = contract["source"]["requested_end"]
    resident_codes = ("S1M", "S11", "S12", "S13", "S1")
    required: set[str] = set()
    for code in resident_codes:
        for measure in ("LE", "F"):
            for entry in ("A", "L"):
                required.add(key("W0", code, entry, measure, "F"))
                required.add(key("W0", code, entry, measure, "F1"))
    for measure in ("LE", "F"):
        for entry in ("A", "L"):
            required.add(key("W1", "S1", entry, measure, "F"))
            required.add(key("W1", "S1", entry, measure, "F1"))

    results: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch, k, start, end): k for k in sorted(required)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            k = futures[future]
            results[k] = future.result()
            print(
                f"[{index}/{len(futures)}] {results[k].get('status')} {k}",
                flush=True,
            )

    status_counts = dict(Counter(str(x.get("status")) for x in results.values()))
    network_errors = [
        k for k, value in results.items()
        if value.get("status") == "NETWORK_ERROR"
    ]

    diagnostics: dict[str, dict[str, object]] = {}
    mandatory_missing: list[str] = []

    for label, measure in (("stock", "LE"), ("flow", "F")):
        nets: dict[str, dict[str, float]] = {}
        statuses = {}
        for code in ("S1M", "S11", "S12", "S13", "S1"):
            values, status = net_series(
                results,
                "W0",
                code,
                measure,
                code in {"S1M", "S11"},
            )
            statuses[code] = status
            if values is None:
                for side_status in status.values():
                    if side_status.startswith("missing:"):
                        mandatory_missing.append(side_status.split(":", 1)[1])
            else:
                nets[code] = values

        w1_assets, w1a_status = represented(
            results, "W1", "S1", "A", measure, False
        )
        w1_liabilities, w1l_status = represented(
            results, "W1", "S1", "L", measure, False
        )
        statuses["W1"] = {
            "assets": w1a_status,
            "liabilities": w1l_status,
        }
        for side_status in (w1a_status, w1l_status):
            if side_status.startswith("missing:"):
                mandatory_missing.append(side_status.split(":", 1)[1])

        if (
            set(nets) != {"S1M", "S11", "S12", "S13", "S1"}
            or w1_assets is None
            or w1_liabilities is None
        ):
            diagnostics[label] = {
                "source_complete": False,
                "statuses": statuses,
            }
            continue

        domestic_sector_sum = combine(
            [(1.0, nets[x]) for x in ("S1M", "S11", "S12", "S13")]
        )
        direct_s1 = nets["S1"]
        x_net = combine([(1.0, w1_liabilities), (-1.0, w1_assets)])

        common = sorted(
            set(domestic_sector_sum) & set(direct_s1) & set(x_net)
        )
        resident_additivity = {
            p: domestic_sector_sum[p] - direct_s1[p] for p in common
        }
        total_economy_external = {
            p: direct_s1[p] + x_net[p] for p in common
        }
        reconstructed = {
            p: resident_additivity[p] + total_economy_external[p]
            for p in common
        }
        direct_six_sector = {
            p: domestic_sector_sum[p] + x_net[p] for p in common
        }
        decomposition_error = {
            p: reconstructed[p] - direct_six_sector[p] for p in common
        }

        failing_phase_c = (
            set(phase_c["precision_gate"]["stock"]["failing_periods"])
            if label == "stock" else set()
        )
        dominant = {}
        for p in sorted(failing_phase_c & set(common)):
            a = resident_additivity[p]
            b = total_economy_external[p]
            dominant[p] = {
                "resident_additivity_residual_million_RON": a,
                "total_economy_external_residual_million_RON": b,
                "reconstructed_six_sector_residual_million_RON": reconstructed[p],
                "dominant_component": (
                    "RESIDENT_SECTOR_ADDITIVITY"
                    if abs(a) > abs(b)
                    else "TOTAL_ECONOMY_EXTERNAL"
                    if abs(b) > abs(a)
                    else "EQUAL"
                ),
            }

        diagnostics[label] = {
            "source_complete": True,
            "statuses": statuses,
            "common_observation_count": len(common),
            "first_common_period": common[0] if common else None,
            "last_common_period": common[-1] if common else None,
            "missing_required_2025_periods": [
                p for p in REQUIRED_2025 if p not in common
            ],
            "resident_additivity_residual_million_RON": resident_additivity,
            "total_economy_external_residual_million_RON": total_economy_external,
            "reconstructed_six_sector_residual_million_RON": reconstructed,
            "decomposition_error_million_RON": decomposition_error,
            "max_absolute_resident_additivity_residual_million_RON": (
                max(abs(x) for x in resident_additivity.values())
                if resident_additivity else None
            ),
            "max_absolute_total_economy_external_residual_million_RON": (
                max(abs(x) for x in total_economy_external.values())
                if total_economy_external else None
            ),
            "max_absolute_decomposition_error_million_RON": (
                max(abs(x) for x in decomposition_error.values())
                if decomposition_error else None
            ),
            "phase_c_failing_stock_period_localization": dominant,
        }

    decomposition_exact = all(
        item.get("source_complete")
        and item.get("max_absolute_decomposition_error_million_RON", math.inf)
        <= COMPUTATIONAL_EPSILON
        for item in diagnostics.values()
    )

    report = {
        "audit_version": "0.1",
        "phase": "Sectoral Financial Positions Phase D — source discrepancy localization",
        "reference_mode": "sectoral_financial_positions",
        "contract": "model/dynamics/sectoral_financial_positions_source_discrepancy_contract.json",
        "source": {
            "series_requested": len(required),
            "series_status_counts": status_counts,
            "network_errors": network_errors,
        },
        "mandatory_missing_series": sorted(set(mandatory_missing)),
        "diagnostics": diagnostics,
        "decomposition_exact_within_computational_epsilon": decomposition_exact,
        "promotion_eligible": False,
        "readiness_count_change": 0,
        "accounting_readiness_changed": False,
        "behavioural_closure_changed": False,
        "interpretation": (
            "Diagnostic only. The decomposition localizes the observed six-sector "
            "residual; it does not authorize replacement of sector histories by "
            "S1 totals or any residual allocation."
        ),
    }
    path = OUT / "sectoral_financial_positions_phase_d_diagnostic.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "series_requested": len(required),
        "series_status_counts": status_counts,
        "mandatory_missing_series_count": len(set(mandatory_missing)),
        "decomposition_exact": decomposition_exact,
        "diagnostics": {
            label: {
                k: v for k, v in item.items()
                if k.startswith("max_absolute_")
                or k in {
                    "source_complete",
                    "common_observation_count",
                    "first_common_period",
                    "last_common_period",
                    "missing_required_2025_periods",
                    "phase_c_failing_stock_period_localization",
                }
            }
            for label, item in diagnostics.items()
        },
        "promotion_eligible": False,
    }, indent=2))

    if network_errors or mandatory_missing or not decomposition_exact:
        raise SystemExit("Phase D diagnostic source/decomposition gate failed")


if __name__ == "__main__":
    main()
