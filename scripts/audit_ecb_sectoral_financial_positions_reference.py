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
        "SECTORAL_POSITIONS_REFERENCE_AUDIT_OUT",
        "sectoral_positions_reference_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub sectoral-financial-positions reference audit)"
)
TOL = 0.1
SECTORS = ("H", "C", "F", "G", "X", "BNR")
RESIDENT = ("H", "C", "F", "G", "BNR")
REQUIRED_2025 = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "dynamics"
            / "sectoral_financial_positions_reference_contract.json"
        ).read_text(encoding="utf-8")
    )


def key(
    area: str,
    reference_sector: str,
    counterpart_sector: str,
    entry: str,
    measure: str,
    instrument: str,
    maturity: str,
    expenditure: str,
) -> str:
    return ".".join(
        (
            "Q",
            "N",
            "RO",
            area,
            reference_sector,
            counterpart_sector,
            "N",
            entry,
            measure,
            instrument,
            maturity,
            expenditure,
            "XDC",
            "_T",
            "S",
            "V",
            "N",
            "_T",
        )
    )


def request_url(series_key: str, contract: dict) -> str:
    query = urllib.parse.urlencode(
        {
            "startPeriod": contract["source"]["requested_start"],
            "endPeriod": contract["source"]["requested_end"],
            "format": "csvdata",
        }
    )
    return f"{API}{series_key}?{query}"


def fetch(series_key: str, contract: dict) -> dict[str, object]:
    url = request_url(series_key, contract)
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
    last_error: Exception | None = None

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
            last_error = exc
            if attempt < 3:
                time.sleep(float(attempt * 2))
                continue
            return {
                "key": series_key,
                "url": url,
                "status": "NETWORK_ERROR",
                "error": str(last_error),
                "attempts": attempt,
                "observations": {},
            }

    raw_path = OUT / "raw" / f"{sha256(series_key.encode())[:20]}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "key": series_key,
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
        result["response_preview"] = body[:300].decode("utf-8", errors="replace")
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
    returned_keys: set[str] = set()
    dimension_values = {
        "FREQ": set(),
        "REF_AREA": set(),
        "COUNTERPART_AREA": set(),
        "REF_SECTOR": set(),
        "COUNTERPART_SECTOR": set(),
        "ACCOUNTING_ENTRY": set(),
        "STO": set(),
        "INSTR_ASSET": set(),
        "MATURITY": set(),
        "EXPENDITURE": set(),
        "UNIT_MEASURE": set(),
        "UNIT_MULT": set(),
    }

    for row in rows:
        if row.get("KEY"):
            returned_keys.add(str(row["KEY"]))
        for field in dimension_values:
            value = row.get(field)
            if value not in (None, ""):
                dimension_values[field].add(str(value))

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
            "returned_keys": sorted(returned_keys),
            "dimension_values": {
                field: sorted(values)
                for field, values in dimension_values.items()
            },
            "observations": observations,
        }
    )
    return result


def same_period_sum(
    maps: list[tuple[float, dict[str, float]]],
) -> dict[str, float]:
    if not maps:
        return {}
    common = set(maps[0][1])
    for _, values in maps[1:]:
        common &= set(values)
    return {
        period: sum(coefficient * values[period] for coefficient, values in maps)
        for period in sorted(common)
    }


def instrument_sum(
    series_by_key: dict[str, dict[str, object]],
    keys: list[str],
) -> tuple[dict[str, float] | None, list[str]]:
    missing = [
        series_key
        for series_key in keys
        if series_by_key[series_key].get("status") != "AVAILABLE"
    ]
    if missing:
        return None, missing
    maps = [
        (
            1.0,
            {
                str(period): float(value)
                for period, value in series_by_key[series_key][
                    "observations"
                ].items()
            },
        )
        for series_key in keys
    ]
    return same_period_sum(maps), []


def main() -> None:
    contract = load_contract()
    source = contract["source"]
    instruments = tuple(source["instrument_dimensions"])

    required: set[str] = set()
    resident_keys: dict[tuple[str, str, str], list[str]] = {}
    source_codes = sorted(
        {
            code
            for terms in source["resident_sector_mapping"].values()
            for code, _ in terms
        }
    )

    for code in source_codes:
        for measure in ("LE", "F"):
            for entry in ("A", "L"):
                keys = []
                for instrument in instruments:
                    dims = source["instrument_dimensions"][instrument]
                    series_key = key(
                        "W0",
                        code,
                        "S1",
                        entry,
                        measure,
                        instrument,
                        dims["maturity"],
                        dims["expenditure"],
                    )
                    keys.append(series_key)
                    required.add(series_key)
                resident_keys[(code, measure, entry)] = keys

    external_keys: dict[tuple[str, str], list[str]] = {}
    for measure in ("LE", "F"):
        for entry in ("A", "L"):
            keys = []
            for instrument in instruments:
                dims = source["instrument_dimensions"][instrument]
                series_key = key(
                    "W1",
                    "S1",
                    "S1",
                    entry,
                    measure,
                    instrument,
                    dims["maturity"],
                    dims["expenditure"],
                )
                keys.append(series_key)
                required.add(series_key)
            external_keys[(measure, entry)] = keys

    series_by_key: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch, series_key, contract): series_key
            for series_key in sorted(required)
        }
        for index, future in enumerate(as_completed(futures), start=1):
            series_key = futures[future]
            series_by_key[series_key] = future.result()
            print(
                f"[{index}/{len(futures)}] "
                f"{series_by_key[series_key].get('status')} {series_key}",
                flush=True,
            )

    source_status_counts = dict(
        Counter(str(item.get("status")) for item in series_by_key.values())
    )
    network_errors_present = any(
        item.get("status") == "NETWORK_ERROR"
        for item in series_by_key.values()
    )

    code_aggregates: dict[tuple[str, str, str], dict[str, float] | None] = {}
    missing_components: dict[str, list[str]] = {}
    for address, keys in resident_keys.items():
        aggregate, missing = instrument_sum(series_by_key, keys)
        code_aggregates[address] = aggregate
        if missing:
            code, measure, entry = address
            missing_components[f"W0:{code}:{measure}:{entry}"] = missing

    external_aggregates: dict[tuple[str, str], dict[str, float] | None] = {}
    for address, keys in external_keys.items():
        aggregate, missing = instrument_sum(series_by_key, keys)
        external_aggregates[address] = aggregate
        if missing:
            measure, entry = address
            missing_components[f"W1:S1:{measure}:{entry}"] = missing

    sector_series: dict[str, dict[str, dict[str, dict[str, float]]]] = {
        "stock": {},
        "flow": {},
    }

    measure_map = {"stock": "LE", "flow": "F"}
    for label, measure in measure_map.items():
        for sector in RESIDENT:
            terms = source["resident_sector_mapping"][sector]
            assets_terms = []
            liabilities_terms = []
            usable = True
            for code, coefficient in terms:
                assets = code_aggregates[(code, measure, "A")]
                liabilities = code_aggregates[(code, measure, "L")]
                if assets is None or liabilities is None:
                    usable = False
                    break
                assets_terms.append((float(coefficient), assets))
                liabilities_terms.append((float(coefficient), liabilities))
            if not usable:
                sector_series[label][sector] = {
                    "assets": {},
                    "liabilities": {},
                    "net": {},
                }
                continue
            assets = same_period_sum(assets_terms)
            liabilities = same_period_sum(liabilities_terms)
            common = sorted(set(assets) & set(liabilities))
            net = {
                period: assets[period] - liabilities[period]
                for period in common
            }
            sector_series[label][sector] = {
                "assets": {p: assets[p] for p in common},
                "liabilities": {p: liabilities[p] for p in common},
                "net": net,
            }

        resident_external_assets = external_aggregates[(measure, "A")]
        resident_external_liabilities = external_aggregates[(measure, "L")]
        if (
            resident_external_assets is None
            or resident_external_liabilities is None
        ):
            sector_series[label]["X"] = {
                "assets": {},
                "liabilities": {},
                "net": {},
            }
        else:
            x_assets = resident_external_liabilities
            x_liabilities = resident_external_assets
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
    for label in ("stock", "flow"):
        period_sets = [
            set(sector_series[label][sector]["net"])
            for sector in SECTORS
        ]
        common = set.intersection(*period_sets) if period_sets else set()
        common_periods = sorted(common)
        residuals = {
            period: sum(
                sector_series[label][sector]["net"][period]
                for sector in SECTORS
            )
            for period in common_periods
        }
        failing_residuals = {
            period: value
            for period, value in residuals.items()
            if not math.isfinite(value) or abs(value) > TOL
        }
        missing_required = [
            period for period in REQUIRED_2025 if period not in common
        ]
        measure_assessments[label] = {
            "common_observation_count": len(common_periods),
            "first_common_period": common_periods[0] if common_periods else None,
            "last_common_period": common_periods[-1] if common_periods else None,
            "missing_required_2025_periods": missing_required,
            "max_absolute_system_residual_million_RON": (
                max(abs(value) for value in residuals.values())
                if residuals
                else None
            ),
            "system_reconciliation_pass": not failing_residuals and bool(residuals),
            "failing_system_residuals": failing_residuals,
            "system_residuals_million_RON": residuals,
        }

    minimum = int(
        contract["reference_mode"]["minimum_common_observation_count"]
    )
    source_complete = not missing_components and not network_errors_present
    measures_pass = all(
        assessment["common_observation_count"] >= minimum
        and not assessment["missing_required_2025_periods"]
        and assessment["system_reconciliation_pass"]
        for assessment in measure_assessments.values()
    )
    promotion_eligible = source_complete and measures_pass

    report = {
        "audit_version": "0.1",
        "phase": "Reference Mode Recovery — Aggregate Sectoral Financial Positions",
        "reference_mode": "sectoral_financial_positions",
        "boundary_review": contract["boundary_review"],
        "source": {
            "institution": source["institution"],
            "dataset": source["dataset"],
            "requested_start": source["requested_start"],
            "requested_end": source["requested_end"],
            "series_requested": len(required),
            "series_status_counts": source_status_counts,
            "network_errors_present": network_errors_present,
        },
        "construction": {
            "represented_instruments": list(instruments),
            "resident_sector_mapping": source["resident_sector_mapping"],
            "X_orientation": source["rest_of_world"]["orientation"],
            "missing_source_components": missing_components,
        },
        "measure_assessments": measure_assessments,
        "sector_series": sector_series,
        "source_results": series_by_key,
        "promotion_eligible": promotion_eligible,
        "accounting_spine_changed": False,
        "accounting_readiness_changed": False,
        "bilateral_materialization": False,
        "behavioural_closure_changed": False,
        "promotion_status": (
            "AGGREGATE_SECTORAL_REFERENCE_EVIDENCE_READY_FOR_REPOSITORY_ASSESSMENT"
            if promotion_eligible
            else "REFERENCE_MODE_REMAINS_PARTIAL_SERIES_AVAILABLE"
        ),
        "interpretation": (
            "The gate constructs only sector-level behaviour-over-time "
            "positions and financial transactions by explicitly summing QSA "
            "F2-F8. It does not observe holder-by-issuer cells and cannot "
            "change Accounting Spine readiness."
        ),
    }

    report_path = OUT / "sectoral_financial_positions_reference_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "series_requested": len(required),
                "series_status_counts": source_status_counts,
                "missing_component_addresses": len(missing_components),
                "measure_assessments": measure_assessments,
                "promotion_eligible": promotion_eligible,
                "promotion_status": report["promotion_status"],
            },
            indent=2,
        )
    )

    if not promotion_eligible:
        raise SystemExit(
            "Sectoral-financial-positions source gate did not pass; "
            "see retained audit artifact."
        )


if __name__ == "__main__":
    main()
