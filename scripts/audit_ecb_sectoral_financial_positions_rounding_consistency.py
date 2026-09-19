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
        "SECTORAL_POSITIONS_PHASE_C_AUDIT_OUT",
        "sectoral_positions_phase_c_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub sectoral-financial-positions Phase C precision audit)"
)
SECTORS = ("H", "C", "F", "G", "X", "BNR")
REQUIRED_2025 = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
DIRECT_CODES = {"H": "S1M", "C": "S11", "G": "S13", "BNR": "S121"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def series_key(
    area: str,
    reference_sector: str,
    entry: str,
    measure: str,
    instrument: str,
) -> str:
    return ".".join(
        (
            "Q", "N", "RO", area, reference_sector, "S1", "N",
            entry, measure, instrument, "_Z", "_Z", "XDC", "_T",
            "S", "V", "N", "_T",
        )
    )


def request_url(key: str, phase_b_contract: dict) -> str:
    query = urllib.parse.urlencode(
        {
            "startPeriod": phase_b_contract["source"]["requested_start"],
            "endPeriod": phase_b_contract["source"]["requested_end"],
            "format": "csvdata",
        }
    )
    return f"{API}{key}?{query}"


def fetch(key: str, phase_b_contract: dict) -> dict[str, object]:
    url = request_url(key, phase_b_contract)
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
                "decimals": None,
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
        "decimals": None,
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
    decimal_values: set[int] = set()
    invalid_decimals: list[str] = []

    for row in rows:
        raw_decimals = str(row.get("DECIMALS", "")).strip()
        if raw_decimals:
            try:
                parsed_decimals = int(raw_decimals)
            except ValueError:
                invalid_decimals.append(raw_decimals)
            else:
                if parsed_decimals < 0:
                    invalid_decimals.append(raw_decimals)
                else:
                    decimal_values.add(parsed_decimals)

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

    decimals = next(iter(decimal_values)) if len(decimal_values) == 1 else None
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
            "decimals_values": sorted(decimal_values),
            "invalid_decimals": invalid_decimals,
            "decimals": decimals,
            "observations": observations,
        }
    )
    return result


def obs(result: dict[str, object]) -> dict[str, float] | None:
    if result.get("status") != "AVAILABLE":
        return None
    return {
        str(period): float(value)
        for period, value in result["observations"].items()
    }


def subtract(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    common = sorted(set(left) & set(right))
    return {p: left[p] - right[p] for p in common}


def combine(terms: list[tuple[float, dict[str, float]]]) -> dict[str, float]:
    if not terms:
        return {}
    common = set(terms[0][1])
    for _, values in terms[1:]:
        common &= set(values)
    return {
        p: sum(coeff * values[p] for coeff, values in terms)
        for p in sorted(common)
    }


def key_for(area: str, code: str, entry: str, measure: str, instrument: str) -> str:
    return series_key(area, code, entry, measure, instrument)


def half_rounding_width(result: dict[str, object]) -> float | None:
    decimals = result.get("decimals")
    if not isinstance(decimals, int) or decimals < 0:
        return None
    return 0.5 * (10.0 ** (-decimals))


def main() -> None:
    phase_c = load_json(
        "model/dynamics/sectoral_financial_positions_rounding_consistency_contract.json"
    )
    phase_b_contract = load_json(
        "model/dynamics/sectoral_financial_positions_aggregate_identity_contract.json"
    )
    phase_b_assessment = load_json(
        "model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"
    )

    if phase_b_assessment["verdict"] != phase_c["prerequisites"]["required_phase_B_verdict"]:
        raise RuntimeError("Phase B verdict does not satisfy Phase C prerequisite")

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
            executor.submit(fetch, key, phase_b_contract): key
            for key in sorted(required)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            key = futures[future]
            results[key] = future.result()
            print(
                f"[{index}/{len(futures)}] "
                f"{results[key].get('status')} "
                f"DECIMALS={results[key].get('decimals')} {key}",
                flush=True,
            )

    status_counts = dict(Counter(str(v.get("status")) for v in results.values()))
    network_errors = [
        key for key, item in results.items()
        if item.get("status") == "NETWORK_ERROR"
    ]

    mandatory_missing: list[str] = []
    invalid_precision: list[str] = []
    structural_checks: dict[str, dict[str, object]] = {}
    represented_by_code: dict[tuple[str, str, str], dict[str, float] | None] = {}

    for code in source_codes:
        for measure in ("LE", "F"):
            for entry in ("A", "L"):
                total_key = key_for("W0", code, entry, measure, "F")
                f1_key = key_for("W0", code, entry, measure, "F1")
                total = obs(results[total_key])
                f1 = obs(results[f1_key])

                if total is None:
                    mandatory_missing.append(total_key)
                    represented_by_code[(code, measure, entry)] = None
                    continue
                if half_rounding_width(results[total_key]) is None:
                    invalid_precision.append(total_key)

                if code in mandatory_f1_codes:
                    if f1 is None:
                        mandatory_missing.append(f1_key)
                        represented_by_code[(code, measure, entry)] = None
                    else:
                        if half_rounding_width(results[f1_key]) is None:
                            invalid_precision.append(f1_key)
                        represented_by_code[(code, measure, entry)] = subtract(total, f1)
                    continue

                if f1 is None:
                    structural_checks[f"{code}:{measure}:{entry}"] = {
                        "rule": "STRUCTURAL_NOT_APPLICABLE_SOURCE_ABSENCE_ACCEPTED",
                        "passes": True,
                    }
                    represented_by_code[(code, measure, entry)] = total
                else:
                    if half_rounding_width(results[f1_key]) is None:
                        invalid_precision.append(f1_key)
                    tolerance = float(
                        phase_b_contract["consistency_gates"][
                            "H_C_F1_if_published_must_be_zero_within_million_RON"
                        ]
                    )
                    nonzero = {
                        p: value for p, value in f1.items()
                        if abs(value) > tolerance
                    }
                    passes = not nonzero
                    structural_checks[f"{code}:{measure}:{entry}"] = {
                        "rule": "PUBLISHED_F1_MUST_BE_ZERO_WITHIN_PHASE_B_TOLERANCE",
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
            total = obs(results[total_key])
            f1 = obs(results[f1_key])
            if total is None:
                mandatory_missing.append(total_key)
                external[(measure, entry)] = None
            elif f1 is None:
                mandatory_missing.append(f1_key)
                external[(measure, entry)] = None
            else:
                if half_rounding_width(results[total_key]) is None:
                    invalid_precision.append(total_key)
                if half_rounding_width(results[f1_key]) is None:
                    invalid_precision.append(f1_key)
                external[(measure, entry)] = subtract(total, f1)

    structural_pass = all(bool(x["passes"]) for x in structural_checks.values())

    sector_series: dict[str, dict[str, dict[str, dict[str, float]]]] = {
        "stock": {}, "flow": {}
    }
    for label, measure in (("stock", "LE"), ("flow", "F")):
        for sector in ("H", "C", "G", "BNR"):
            code = DIRECT_CODES[sector]
            assets = represented_by_code[(code, measure, "A")]
            liabilities = represented_by_code[(code, measure, "L")]
            if assets is None or liabilities is None:
                sector_series[label][sector] = {"assets": {}, "liabilities": {}, "net": {}}
            else:
                common = sorted(set(assets) & set(liabilities))
                sector_series[label][sector] = {
                    "assets": {p: assets[p] for p in common},
                    "liabilities": {p: liabilities[p] for p in common},
                    "net": {p: assets[p] - liabilities[p] for p in common},
                }

        s12a = represented_by_code[("S12", measure, "A")]
        s121a = represented_by_code[("S121", measure, "A")]
        s12l = represented_by_code[("S12", measure, "L")]
        s121l = represented_by_code[("S121", measure, "L")]
        if None in (s12a, s121a, s12l, s121l):
            sector_series[label]["F"] = {"assets": {}, "liabilities": {}, "net": {}}
        else:
            assets = combine([(1.0, s12a), (-1.0, s121a)])
            liabilities = combine([(1.0, s12l), (-1.0, s121l)])
            common = sorted(set(assets) & set(liabilities))
            sector_series[label]["F"] = {
                "assets": {p: assets[p] for p in common},
                "liabilities": {p: liabilities[p] for p in common},
                "net": {p: assets[p] - liabilities[p] for p in common},
            }

        ext_a = external[(measure, "A")]
        ext_l = external[(measure, "L")]
        if ext_a is None or ext_l is None:
            sector_series[label]["X"] = {"assets": {}, "liabilities": {}, "net": {}}
        else:
            x_assets = ext_l
            x_liabilities = ext_a
            common = sorted(set(x_assets) & set(x_liabilities))
            sector_series[label]["X"] = {
                "assets": {p: x_assets[p] for p in common},
                "liabilities": {p: x_liabilities[p] for p in common},
                "net": {p: x_assets[p] - x_liabilities[p] for p in common},
            }

    # Algebraically reduced system identity after F + BNR cancellation.
    # Each tuple is (series key, coefficient).
    identity_terms: dict[str, list[tuple[str, float]]] = {}
    for measure in ("LE", "F"):
        terms: list[tuple[str, float]] = []
        for code in ("S1M", "S11", "S12", "S13"):
            for entry, sign in (("A", 1.0), ("L", -1.0)):
                total_key = key_for("W0", code, entry, measure, "F")
                terms.append((total_key, sign))
                f1_key = key_for("W0", code, entry, measure, "F1")
                if results[f1_key].get("status") == "AVAILABLE":
                    terms.append((f1_key, -sign))
                elif code not in optional_zero_f1_codes:
                    mandatory_missing.append(f1_key)
        for entry, sign in (("A", -1.0), ("L", 1.0)):
            total_key = key_for("W1", "S1", entry, measure, "F")
            f1_key = key_for("W1", "S1", entry, measure, "F1")
            terms.append((total_key, sign))
            terms.append((f1_key, -sign))
        identity_terms[measure] = terms

    phase_c_assessments: dict[str, dict[str, object]] = {}
    epsilon = float(phase_c["rounding_model"]["computational_epsilon_million_RON"])
    minimum = int(phase_c["source_requirements"]["minimum_common_observation_count"])

    for label, measure in (("stock", "LE"), ("flow", "F")):
        common_sets = [
            set(sector_series[label][sector]["net"])
            for sector in SECTORS
        ]
        common = set.intersection(*common_sets) if common_sets else set()
        periods = sorted(common)
        residuals = {
            p: sum(sector_series[label][s]["net"][p] for s in SECTORS)
            for p in periods
        }

        widths: dict[str, float] = {}
        precision_complete = True
        for key, coefficient in identity_terms[measure]:
            if abs(coefficient) == 0:
                continue
            width = half_rounding_width(results[key])
            if width is None:
                precision_complete = False
                invalid_precision.append(key)
            else:
                widths[key] = abs(coefficient) * width

        envelope = sum(widths.values()) if precision_complete else None
        failures = {}
        if envelope is not None:
            failures = {
                p: {
                    "residual_million_RON": residuals[p],
                    "rounding_envelope_million_RON": envelope,
                    "excess_million_RON": abs(residuals[p]) - envelope,
                }
                for p in periods
                if abs(residuals[p]) > envelope + epsilon
            }

        phase_c_assessments[label] = {
            "common_observation_count": len(periods),
            "first_common_period": periods[0] if periods else None,
            "last_common_period": periods[-1] if periods else None,
            "missing_required_2025_periods": [p for p in REQUIRED_2025 if p not in common],
            "precision_metadata_complete": precision_complete,
            "unique_source_series_in_system_identity": len(widths),
            "rounding_envelope_million_RON": envelope,
            "max_absolute_system_residual_million_RON": (
                max(abs(x) for x in residuals.values()) if residuals else None
            ),
            "precision_consistency_pass": (
                precision_complete and bool(residuals) and not failures
            ),
            "failing_periods": failures,
            "system_residuals_million_RON": residuals,
            "rounding_width_contributions_million_RON": widths,
        }

    source_complete = not mandatory_missing and not network_errors
    precision_complete = not invalid_precision
    measures_pass = all(
        item["common_observation_count"] >= minimum
        and not item["missing_required_2025_periods"]
        and item["precision_consistency_pass"]
        for item in phase_c_assessments.values()
    )
    promotion_eligible = (
        source_complete and precision_complete and structural_pass and measures_pass
    )

    report = {
        "audit_version": "0.1",
        "phase": "Sectoral Financial Positions Phase C — source-precision reconciliation",
        "reference_mode": "sectoral_financial_positions",
        "contract": "model/dynamics/sectoral_financial_positions_rounding_consistency_contract.json",
        "source": {
            "series_requested": len(required),
            "series_status_counts": status_counts,
            "network_errors": sorted(set(network_errors)),
        },
        "mandatory_missing_series": sorted(set(mandatory_missing)),
        "invalid_precision_series": sorted(set(invalid_precision)),
        "H_C_structural_F1_checks": structural_checks,
        "measure_assessments": phase_c_assessments,
        "source_results": results,
        "promotion_eligible": promotion_eligible,
        "accounting_spine_changed": False,
        "accounting_readiness_changed": False,
        "bilateral_materialization": False,
        "behavioural_closure_changed": False,
        "promotion_status": (
            "SECTORAL_FINANCIAL_POSITIONS_PHASE_C_READY_FOR_REPOSITORY_ASSESSMENT"
            if promotion_eligible
            else "REFERENCE_MODE_REMAINS_PARTIAL_SERIES_AVAILABLE"
        ),
        "interpretation": (
            "The Phase B fixed tolerance is not modified. Phase C asks only "
            "whether the exact system residual is contained in the rounding "
            "interval implied by ECB DECIMALS metadata after algebraic "
            "cancellation of repeated source terms."
        ),
    }

    output = OUT / "sectoral_financial_positions_phase_c_audit.json"
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "series_requested": len(required),
        "series_status_counts": status_counts,
        "mandatory_missing_series_count": len(set(mandatory_missing)),
        "invalid_precision_series_count": len(set(invalid_precision)),
        "structural_checks_pass": structural_pass,
        "measure_assessments": phase_c_assessments,
        "promotion_eligible": promotion_eligible,
        "promotion_status": report["promotion_status"],
    }, indent=2))

    if not promotion_eligible:
        raise SystemExit(
            "Sectoral financial positions Phase C did not pass; "
            "see retained audit artifact."
        )


if __name__ == "__main__":
    main()
