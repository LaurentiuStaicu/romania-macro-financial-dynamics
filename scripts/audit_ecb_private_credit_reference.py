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

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "PRIVATE_CREDIT_REFERENCE_AUDIT_OUT",
        "private_credit_reference_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = "https://data-api.ecb.europa.eu/service/data/BSI"
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub private-credit reference-mode audit)"
)
REQUIRED_MONTHS = tuple(f"2025-{month:02d}" for month in range(1, 13))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract() -> dict:
    return json.loads(
        (
            ROOT / "model" / "dynamics" / "private_credit_reference_contract.json"
        ).read_text(encoding="utf-8")
    )


def request_url(full_series_key: str, contract: dict) -> str:
    if not full_series_key.startswith("BSI."):
        raise ValueError(f"Unexpected BSI series key: {full_series_key}")
    key = full_series_key.removeprefix("BSI.")
    query = urllib.parse.urlencode(
        {
            "startPeriod": contract["source"]["requested_start"],
            "endPeriod": contract["source"]["requested_end"],
            "format": "csvdata",
        }
    )
    return f"{API}/{key}?{query}"


def fetch_component(name: str, spec: dict, contract: dict) -> dict[str, object]:
    full_key = str(spec["series_key"])
    url = request_url(full_key, contract)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,application/vnd.sdmx.data+csv;version=1.0.0",
        },
    )

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
            break
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                return {
                    "component": name,
                    "series_key": full_key,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "attempts": attempt,
                    "observation_count": 0,
                    "observations": [],
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_path = OUT / "raw" / f"{name}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "component": name,
        "series_key": full_key,
        "url": url,
        "http_status": status,
        "content_type": headers.get("Content-Type"),
        "raw_path": str(raw_path.relative_to(OUT)),
        "raw_sha256": sha256(body),
        "raw_bytes": len(body),
        "observation_count": 0,
        "observations": [],
    }
    if status != 200:
        result["status"] = "HTTP_ERROR"
        result["response_preview"] = body[:500].decode(
            "utf-8", errors="replace"
        )
        return result

    try:
        text = body.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV response has no header")
        rows = list(reader)
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    required_columns = {"TIME_PERIOD", "OBS_VALUE"}
    if not required_columns.issubset(set(reader.fieldnames)):
        result["status"] = "UNEXPECTED_COLUMNS"
        result["columns"] = list(reader.fieldnames)
        return result

    observations: list[dict[str, object]] = []
    seen_periods: set[str] = set()
    non_finite_periods: list[str] = []
    duplicate_periods: list[str] = []
    reported_keys: set[str] = set()

    for row in rows:
        if row.get("KEY"):
            reported_keys.add(str(row["KEY"]))
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
            non_finite_periods.append(period)
            continue
        if period in seen_periods:
            duplicate_periods.append(period)
            continue
        seen_periods.add(period)
        observations.append({"period": period, "value": value})

    observations.sort(key=lambda item: str(item["period"]))
    observed_periods = {str(item["period"]) for item in observations}
    missing_required = [
        period for period in REQUIRED_MONTHS if period not in observed_periods
    ]

    result.update(
        {
            "status": (
                "AVAILABLE_SERIES"
                if observations
                and not non_finite_periods
                and not duplicate_periods
                else "SERIES_INCOMPLETE"
            ),
            "reported_keys": sorted(reported_keys),
            "observation_count": len(observations),
            "first_observation": (
                observations[0]["period"] if observations else None
            ),
            "last_observation": (
                observations[-1]["period"] if observations else None
            ),
            "missing_required_periods": missing_required,
            "non_finite_periods": non_finite_periods,
            "duplicate_periods": duplicate_periods,
            "observations": observations,
        }
    )
    return result


def observation_map(result: dict[str, object]) -> dict[str, float]:
    return {
        str(item["period"]): float(item["value"])
        for item in result.get("observations", [])
    }


def aggregate_pair(
    left: dict[str, object],
    right: dict[str, object],
) -> list[dict[str, object]]:
    left_map = observation_map(left)
    right_map = observation_map(right)
    periods = sorted(set(left_map) & set(right_map))
    return [
        {
            "period": period,
            "value": left_map[period] + right_map[period],
        }
        for period in periods
    ]


def main() -> None:
    contract = load_contract()
    minimum_count = int(
        contract["reference_modes"]["minimum_component_observation_count"]
    )
    components = contract["source"]["components"]
    results = {
        name: fetch_component(name, spec, contract)
        for name, spec in components.items()
    }

    component_assessments: dict[str, dict[str, object]] = {}
    for name, result in results.items():
        expected_key = str(components[name]["series_key"])
        reported_keys = set(result.get("reported_keys", []))
        key_consistent = (
            not reported_keys
            or reported_keys == {expected_key}
        )
        passed = (
            result.get("status") == "AVAILABLE_SERIES"
            and int(result.get("observation_count", 0)) >= minimum_count
            and not result.get("missing_required_periods", [])
            and not result.get("non_finite_periods", [])
            and not result.get("duplicate_periods", [])
            and key_consistent
        )
        component_assessments[name] = {
            "passed": passed,
            "status": result.get("status"),
            "series_key": expected_key,
            "reported_keys": sorted(reported_keys),
            "key_consistent": key_consistent,
            "observation_count": result.get("observation_count", 0),
            "minimum_required_observation_count": minimum_count,
            "first_observation": result.get("first_observation"),
            "last_observation": result.get("last_observation"),
            "missing_required_periods": result.get(
                "missing_required_periods", []
            ),
            "non_finite_periods": result.get("non_finite_periods", []),
            "duplicate_periods": result.get("duplicate_periods", []),
        }

    stock = aggregate_pair(
        results["nfc_stock"],
        results["households_npish_stock"],
    )
    flow = aggregate_pair(
        results["nfc_flow"],
        results["households_npish_flow"],
    )
    stock_map = {str(item["period"]): float(item["value"]) for item in stock}
    flow_map = {str(item["period"]): float(item["value"]) for item in flow}

    aggregate_assessment = {
        "credit_stock": {
            "observation_count": len(stock),
            "first_observation": stock[0]["period"] if stock else None,
            "last_observation": stock[-1]["period"] if stock else None,
            "missing_required_periods": [
                p for p in REQUIRED_MONTHS if p not in stock_map
            ],
            "observations": stock,
        },
        "credit_flow": {
            "observation_count": len(flow),
            "first_observation": flow[0]["period"] if flow else None,
            "last_observation": flow[-1]["period"] if flow else None,
            "missing_required_periods": [
                p for p in REQUIRED_MONTHS if p not in flow_map
            ],
            "observations": flow,
        },
    }

    promotion_eligible = (
        all(item["passed"] for item in component_assessments.values())
        and not aggregate_assessment["credit_stock"][
            "missing_required_periods"
        ]
        and not aggregate_assessment["credit_flow"][
            "missing_required_periods"
        ]
    )

    report = {
        "audit_version": "0.1",
        "phase": "Reference Mode Recovery — Private Non-Financial Credit",
        "reference_modes": ["credit_stock", "credit_flow"],
        "source": "ECB BSI",
        "scope": "Romania domestic S11 plus S14/S15 loans from MFIs excluding NCB, all currencies combined",
        "unit": "Millions of Euro",
        "frequency": "Monthly",
        "component_assessments": component_assessments,
        "source_results": results,
        "aggregate_series": aggregate_assessment,
        "promotion_eligible": promotion_eligible,
        "accounting_spine_changed": False,
        "behavioural_closure_changed": False,
        "credit_stock_difference_used_as_flow": False,
        "promotion_status": (
            "CREDIT_STOCK_AND_FLOW_EVIDENCE_READY_FOR_REPOSITORY_ASSESSMENT"
            if promotion_eligible
            else "REFERENCE_MODES_REMAIN_BLOCKED"
        ),
        "interpretation": (
            "credit_stock is the same-month sum of directly published S11 and "
            "S14/S15 A20 end-of-period loan stocks. credit_flow is the "
            "same-month sum of directly published ECB financial transactions "
            "for the same two sectors. The flow is not a first difference of "
            "the stock and is not gross new-lending originations."
        ),
    }

    path = OUT / "private_credit_reference_audit.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "component_assessments": component_assessments,
                "aggregate_summary": {
                    key: {
                        "observation_count": value["observation_count"],
                        "first_observation": value["first_observation"],
                        "last_observation": value["last_observation"],
                        "missing_required_periods": value[
                            "missing_required_periods"
                        ],
                    }
                    for key, value in aggregate_assessment.items()
                },
                "promotion_eligible": promotion_eligible,
                "promotion_status": report["promotion_status"],
            },
            indent=2,
        )
    )

    if not promotion_eligible:
        raise SystemExit(
            "Private-credit stock/flow source gate did not pass; "
            "see retained audit artifact."
        )


if __name__ == "__main__":
    main()
