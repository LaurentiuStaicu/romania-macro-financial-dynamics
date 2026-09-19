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
        "SECTORAL_POSITIONS_PHASE_B_AUDIT_OUT",
        "sectoral_positions_phase_b_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub sectoral-financial-positions Phase B audit)"
)
SECTORS = ("H", "C", "F", "G", "X", "BNR")
REQUIRED_2025 = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
DIRECT_CODES = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "dynamics"
            / "sectoral_financial_positions_aggregate_identity_contract.json"
        ).read_text(encoding="utf-8")
    )


def series_key(
    area: str,
    reference_sector: str,
    entry: str,
    measure: str,
    instrument: str,
) -> str:
    return ".".join(
        (
            "Q",
            "N",
            "RO",
            area,
            reference_sector,
            "S1",
            "N",
            entry,
            measure,
            instrument,
            "_Z",
            "_Z",
            "XDC",
            "_T",
            "S",
            "V",
            "N",
            "_T",
        )
    )


def request_url(key: str, contract: dict) -> str:
    query = urllib.parse.urlencode(
        {
            "startPeriod": contract["source"]["requested_start"],
            "endPeriod": contract["source"]["requested_end"],
            "format": "csvdata",
        }
    )
    return f"{API}{key}?{query}"


def fetch(key: str, contract: dict) -> dict[str, object]:
    url = request_url(key, contract)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,application/vnd.sdmx.data+csv;version=1.0.0",
        },
    )
    body = b""
    status = 0
    headers: dict[str, str] = {}

    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read()
                status = int(response.status)
                headers = dict(response.headers.items())
            break
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = int(exc.code)
            headers = dict(exc.headers.items())
            if status in {429, 500, 502, 503, 504} and attempt < 3:
                time.sleep(float(attempt * 2))
                continue
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < 3:
                time.sleep(float(attempt * 2))
                continue
            return {
                "key": key,
                "url": url,
                "status": "NETWORK_ERROR",
                "error": str(exc),
                "observations": {},
            }

    raw_path = OUT / "raw" / f"{sha256(key.encode())[:20]}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": key,
        "url": url,
        "http_status": status,
        "content_type": headers.get("Content-Type"),
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "observations": {},
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        result["response_preview"] = body[:300].decode(
            "utf-8", errors="replace"
        )
        return result

    try:
        reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
        if not reader.fieldnames:
            raise ValueError("CSV response has no header")
        rows = list(reader)
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    observations: dict[str, float] = {}
    duplicates: list[str] = []
    non_finite: list[str] = []
    dims: dict[str, set[str]] = {
        "ACCOUNTING_ENTRY": set(),
        "STO": set(),
        "INSTR_ASSET": set(),
        "UNIT_MEASURE": set(),
        "UNIT_MULT": set(),
        "REF_SECTOR": set(),
        "COUNTERPART_AREA": set(),
    }

    for row in rows:
        for field in dims:
            value = row.get(field)
            if value not in (None, ""):
                dims[field].add(str(value))

        period = str(row.get("TIME_PERIOD", "")).strip()
        raw_value = str(row.get("OBS_VALUE", "")).strip()
        if not period or raw_value in {"", "NaN", "nan"}:
            continue
        try:
            value = float(raw_value)
        except ValueError:
            result["status"] = "NON_NUMERIC_OBSERVATION"
            result["period"] = period
            result["raw_value"] = raw_value
            return result
        if not math.isfinite(value):
            non_finite.append(period)
            continue
        if period in observations:
            duplicates.append(period)
            continue
        observations[period] = value

    result.update(
        {
            "status": (
                "AVAILABLE"
                if observations and not duplicates and not non_finite
                else "SERIES_INCOMPLETE"
            ),
            "observation_count": len(observations),
            "first_observation": min(observations) if observations else None,
            "last_observation": max(observations) if observations else None,
            "duplicate_periods": duplicates,
            "non_finite_periods": non_finite,
            "dimension_values": {
                field: sorted(values) for field, values in dims.items()
            },
            "observations": observations,
        }
    )
    return result


def observations(result: dict[str, object]) -> dict[str, float] | None:
    if result.get("status") != "AVAILABLE":
        return None
    return {
        str(period): float(value)
        for period, value in result["observations"].items()
    }


def subtract(
    left: dict[str, float],
    right: dict[str, float],
) -> dict[str, float]:
    common = sorted(set(left) & set(right))
    return {period: left[period] - right[period] for period in common}


def combine(
    terms: list[tuple[float, dict[str, float]]],
) -> dict[str, float]:
    if not terms:
        return {}
    common = set(terms[0][1])
    for _, values in terms[1:]:
        common &= set(values)
    return {
        period: sum(coefficient * values[period] for coefficient, values in terms)
        for period in sorted(common)
    }


def key_for(
    area: str,
    code: str,
    entry: str,
    measure: str,
    instrument: str,
) -> str:
    return series_key(area, code, entry, measure, instrument)


def main() -> None:
    contract = load_contract()
    mandatory_f1_codes = {"S12", "S121", "S13"}
    optional_zero_f1_codes = {"S1M", "S11"}
    source_codes = sorted(mandatory_f1_codes | optional_zero_f1_codes)

    required: set[str] = set()
    for code in source_codes:
        for measure in ("LE", "F"):
            for entry in ("A", "L"):
                required.add(key_for("W0", code, entry, measure, "F"))
                required.add(key_for("W0", code, entry, measure, "F1"))
    for measure in ("LE", "F"):
        for entry in ("A", "L"):
            required.add(key_for("W1", "S1", entry, measure, "F"))
            required.add(key_for("W1", "S1", entry, measure, "F1"))

    results: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch, key, contract): key
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

    mandatory_missing: list[str] = []
    structural_checks: dict[str, dict[str, object]] = {}

    represented_by_code: dict[tuple[str, str, str], dict[str, float] | None] = {}

    for code in source_codes:
        for measure in ("LE", "F"):
            for entry in ("A", "L"):
                total_key = key_for("W0", code, entry, measure, "F")
                f1_key = key_for("W0", code, entry, measure, "F1")
                total = observations(results[total_key])
                f1 = observations(results[f1_key])

                if total is None:
                    mandatory_missing.append(total_key)
                    represented_by_code[(code, measure, entry)] = None
                    continue

                if code in mandatory_f1_codes:
                    if f1 is None:
                        mandatory_missing.append(f1_key)
                        represented_by_code[(code, measure, entry)] = None
                    else:
                        represented_by_code[(code, measure, entry)] = subtract(
                            total, f1
                        )
                    continue

                # H/C: F1 is preregistered as structurally not applicable.
                if f1 is None:
                    structural_checks[
                        f"{code}:{measure}:{entry}"
                    ] = {
                        "F1_source_status": results[f1_key].get("status"),
                        "rule": "STRUCTURAL_NOT_APPLICABLE_SOURCE_ABSENCE_ACCEPTED",
                        "passes": True,
                    }
                    represented_by_code[(code, measure, entry)] = total
                else:
                    tolerance = float(
                        contract["consistency_gates"][
                            "H_C_F1_if_published_must_be_zero_within_million_RON"
                        ]
                    )
                    nonzero = {
                        period: value
                        for period, value in f1.items()
                        if abs(value) > tolerance
                    }
                    passes = not nonzero
                    structural_checks[
                        f"{code}:{measure}:{entry}"
                    ] = {
                        "F1_source_status": "AVAILABLE",
                        "rule": "PUBLISHED_F1_MUST_BE_ZERO_WITHIN_TOLERANCE",
                        "tolerance_million_RON": tolerance,
                        "nonzero_periods": nonzero,
                        "passes": passes,
                    }
                    represented_by_code[(code, measure, entry)] = (
                        subtract(total, f1) if passes else None
                    )

    external: dict[tuple[str, str], dict[str, float] | None] = {}
    for measure in ("LE", "F"):
        for entry in ("A", "L"):
            total_key = key_for("W1", "S1", entry, measure, "F")
            f1_key = key_for("W1", "S1", entry, measure, "F1")
            total = observations(results[total_key])
            f1 = observations(results[f1_key])
            if total is None:
                mandatory_missing.append(total_key)
                external[(measure, entry)] = None
            elif f1 is None:
                mandatory_missing.append(f1_key)
                external[(measure, entry)] = None
            else:
                external[(measure, entry)] = subtract(total, f1)

    structural_checks_pass = all(
        bool(item["passes"]) for item in structural_checks.values()
    )

    sector_series: dict[str, dict[str, dict[str, dict[str, float]]]] = {
        "stock": {},
        "flow": {},
    }
    for label, measure in (("stock", "LE"), ("flow", "F")):
        for sector in ("H", "C", "G", "BNR"):
            code = DIRECT_CODES[sector]
            assets = represented_by_code[(code, measure, "A")]
            liabilities = represented_by_code[(code, measure, "L")]
            if assets is None or liabilities is None:
                sector_series[label][sector] = {
                    "assets": {}, "liabilities": {}, "net": {}
                }
            else:
                common = sorted(set(assets) & set(liabilities))
                sector_series[label][sector] = {
                    "assets": {p: assets[p] for p in common},
                    "liabilities": {p: liabilities[p] for p in common},
                    "net": {
                        p: assets[p] - liabilities[p]
                        for p in common
                    },
                }

        f_assets_s12 = represented_by_code[("S12", measure, "A")]
        f_assets_s121 = represented_by_code[("S121", measure, "A")]
        f_liab_s12 = represented_by_code[("S12", measure, "L")]
        f_liab_s121 = represented_by_code[("S121", measure, "L")]
        if None in (
            f_assets_s12,
            f_assets_s121,
            f_liab_s12,
            f_liab_s121,
        ):
            sector_series[label]["F"] = {
                "assets": {}, "liabilities": {}, "net": {}
            }
        else:
            f_assets = combine(
                [(1.0, f_assets_s12), (-1.0, f_assets_s121)]
            )
            f_liabilities = combine(
                [(1.0, f_liab_s12), (-1.0, f_liab_s121)]
            )
            common = sorted(set(f_assets) & set(f_liabilities))
            sector_series[label]["F"] = {
                "assets": {p: f_assets[p] for p in common},
                "liabilities": {p: f_liabilities[p] for p in common},
                "net": {
                    p: f_assets[p] - f_liabilities[p]
                    for p in common
                },
            }

        resident_ext_assets = external[(measure, "A")]
        resident_ext_liabilities = external[(measure, "L")]
        if resident_ext_assets is None or resident_ext_liabilities is None:
            sector_series[label]["X"] = {
                "assets": {}, "liabilities": {}, "net": {}
            }
        else:
            x_assets = resident_ext_liabilities
            x_liabilities = resident_ext_assets
            common = sorted(set(x_assets) & set(x_liabilities))
            sector_series[label]["X"] = {
                "assets": {p: x_assets[p] for p in common},
                "liabilities": {p: x_liabilities[p] for p in common},
                "net": {
                    p: x_assets[p] - x_liabilities[p]
                    for p in common
                },
            }

    measure_assessments: dict[str, dict[str, object]] = {}
    gates = contract["consistency_gates"]
    for label in ("stock", "flow"):
        common_sets = [
            set(sector_series[label][sector]["net"])
            for sector in SECTORS
        ]
        common = set.intersection(*common_sets) if common_sets else set()
        periods = sorted(common)
        residuals = {
            period: sum(
                sector_series[label][sector]["net"][period]
                for sector in SECTORS
            )
            for period in periods
        }
        tolerance = float(
            gates[
                "system_stock_residual_max_abs_million_RON"
                if label == "stock"
                else "system_flow_residual_max_abs_million_RON"
            ]
        )
        failing = {
            period: value
            for period, value in residuals.items()
            if not math.isfinite(value) or abs(value) > tolerance
        }
        measure_assessments[label] = {
            "common_observation_count": len(periods),
            "first_common_period": periods[0] if periods else None,
            "last_common_period": periods[-1] if periods else None,
            "missing_required_2025_periods": [
                p for p in REQUIRED_2025 if p not in common
            ],
            "tolerance_million_RON": tolerance,
            "max_absolute_system_residual_million_RON": (
                max(abs(value) for value in residuals.values())
                if residuals else None
            ),
            "system_reconciliation_pass": bool(residuals) and not failing,
            "failing_system_residuals": failing,
            "system_residuals_million_RON": residuals,
        }

    minimum = int(gates["minimum_common_observation_count"])
    source_complete = not mandatory_missing and not network_errors
    measures_pass = all(
        item["common_observation_count"] >= minimum
        and not item["missing_required_2025_periods"]
        and item["system_reconciliation_pass"]
        for item in measure_assessments.values()
    )
    promotion_eligible = (
        source_complete
        and structural_checks_pass
        and measures_pass
    )

    report = {
        "audit_version": "0.1",
        "phase": "Sectoral Financial Positions Phase B — exact F-minus-F1 aggregate identity",
        "reference_mode": "sectoral_financial_positions",
        "contract": "model/dynamics/sectoral_financial_positions_aggregate_identity_contract.json",
        "source": {
            "institution": contract["source"]["institution"],
            "dataset": contract["source"]["dataset"],
            "series_requested": len(required),
            "series_status_counts": status_counts,
            "network_errors": network_errors,
        },
        "mandatory_missing_series": sorted(set(mandatory_missing)),
        "H_C_structural_F1_checks": structural_checks,
        "measure_assessments": measure_assessments,
        "sector_series": sector_series,
        "source_results": results,
        "promotion_eligible": promotion_eligible,
        "accounting_spine_changed": False,
        "accounting_readiness_changed": False,
        "bilateral_materialization": False,
        "behavioural_closure_changed": False,
        "promotion_status": (
            "SECTORAL_FINANCIAL_POSITIONS_PHASE_B_READY_FOR_REPOSITORY_ASSESSMENT"
            if promotion_eligible
            else "REFERENCE_MODE_REMAINS_PARTIAL_SERIES_AVAILABLE"
        ),
        "interpretation": (
            "Phase B uses the exact ESA identity F2-F8 = total F - F1. "
            "Only H/C have preregistered F1 structural applicability rules; "
            "all other F1 inputs are mandatory source series."
        ),
    }

    output = OUT / "sectoral_financial_positions_phase_b_audit.json"
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "series_requested": len(required),
                "series_status_counts": status_counts,
                "mandatory_missing_series_count": len(set(mandatory_missing)),
                "structural_checks_pass": structural_checks_pass,
                "measure_assessments": measure_assessments,
                "promotion_eligible": promotion_eligible,
                "promotion_status": report["promotion_status"],
            },
            indent=2,
        )
    )
    if not promotion_eligible:
        raise SystemExit(
            "Sectoral financial positions Phase B did not pass; "
            "see retained audit artifact."
        )


if __name__ == "__main__":
    main()
