from __future__ import annotations

import hashlib
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
        "GOV_DEBT_REFERENCE_AUDIT_OUT",
        "government_debt_reference_audit_artifacts",
    )
)
OUT.mkdir(parents=True, exist_ok=True)

API = (
    "https://ec.europa.eu/eurostat/api/dissemination/"
    "statistics/1.0/data/gov_10q_ggdebt"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub government-debt reference-mode audit)"
)
UNITS = ("MIO_NAC", "PC_GDP")
REQUIRED_PERIODS = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_contract() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "dynamics"
            / "government_debt_stock_reference_contract.json"
        ).read_text(encoding="utf-8")
    )


def request_url(unit: str, contract: dict) -> str:
    source = contract["source"]
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": source["frequency"],
            "unit": unit,
            "sector": source["sector"],
            "na_item": source["na_item"],
            "geo": source["geo"],
            "sinceTimePeriod": source["requested_start"],
            "untilTimePeriod": source["requested_end"],
        }
    )
    return f"{API}?{query}"


def ordered_codes(index: object) -> list[str]:
    if isinstance(index, list):
        return [str(item) for item in index]
    if isinstance(index, dict):
        return [
            str(code)
            for code, _ in sorted(index.items(), key=lambda item: int(item[1]))
        ]
    return []


def value_at(values: object, position: int) -> object:
    if isinstance(values, list):
        return values[position] if position < len(values) else None
    if isinstance(values, dict):
        value = values.get(str(position))
        if value is None:
            value = values.get(position)
        return value
    return None


def fetch_unit(unit: str, contract: dict) -> dict[str, object]:
    url = request_url(unit, contract)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
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
                    "unit": unit,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "attempts": attempt,
                    "observation_count": 0,
                    "observations": [],
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_path = OUT / "raw" / f"gov_10q_ggdebt_GD_RO_{unit}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "unit": unit,
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
        payload = json.loads(body.decode("utf-8-sig"))
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    if payload.get("class") != "dataset":
        result["status"] = "UNEXPECTED_PAYLOAD"
        result["payload_keys"] = sorted(payload.keys())
        return result

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if len(ids) != len(sizes):
        result["status"] = "UNEXPECTED_DIMENSIONS"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    non_time_sizes = [
        int(size)
        for dim, size in zip(ids, sizes)
        if dim != "time"
    ]
    if any(size != 1 for size in non_time_sizes):
        result["status"] = "UNEXPECTED_MULTI_SERIES_RESPONSE"
        result["ids"] = ids
        result["sizes"] = sizes
        return result

    time_dimension = (
        payload.get("dimension", {})
        .get("time", {})
        .get("category", {})
    )
    time_codes = ordered_codes(time_dimension.get("index", {}))
    values = payload.get("value", {})

    observations: list[dict[str, object]] = []
    non_finite_periods: list[str] = []
    for position, period in enumerate(time_codes):
        raw_value = value_at(values, position)
        if raw_value is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            result["status"] = "NON_NUMERIC_OBSERVATION"
            result["period"] = period
            result["raw_value"] = raw_value
            return result
        if not math.isfinite(value):
            non_finite_periods.append(period)
            continue
        observations.append({"period": period, "value": value})

    observed_periods = {str(item["period"]) for item in observations}
    missing_required = [
        period for period in REQUIRED_PERIODS if period not in observed_periods
    ]

    result.update(
        {
            "status": (
                "AVAILABLE_SERIES"
                if observations and not non_finite_periods
                else "SERIES_INCOMPLETE"
            ),
            "dataset_updated": payload.get("updated"),
            "dataset_label": payload.get("label"),
            "observation_count": len(observations),
            "first_observation": (
                observations[0]["period"] if observations else None
            ),
            "last_observation": (
                observations[-1]["period"] if observations else None
            ),
            "missing_required_periods": missing_required,
            "non_finite_periods": non_finite_periods,
            "observations": observations,
        }
    )
    return result


def main() -> None:
    contract = load_contract()
    minimum_count = int(
        contract["reference_mode"]["minimum_observation_count_per_unit"]
    )

    results = {
        unit: fetch_unit(unit, contract)
        for unit in contract["source"]["units_to_probe"]
    }

    unit_assessments: dict[str, dict[str, object]] = {}
    for unit, result in results.items():
        missing_required = list(result.get("missing_required_periods", []))
        network_or_parse_failure = result.get("status") in {
            "NETWORK_ERROR",
            "HTTP_ERROR",
            "PARSE_ERROR",
            "UNEXPECTED_PAYLOAD",
            "UNEXPECTED_DIMENSIONS",
            "UNEXPECTED_MULTI_SERIES_RESPONSE",
            "NON_NUMERIC_OBSERVATION",
        }
        enough_observations = int(result.get("observation_count", 0)) >= minimum_count
        all_required = not missing_required
        finite = not result.get("non_finite_periods", [])
        passed = (
            result.get("status") == "AVAILABLE_SERIES"
            and not network_or_parse_failure
            and enough_observations
            and all_required
            and finite
        )
        unit_assessments[unit] = {
            "passed": passed,
            "status": result.get("status"),
            "observation_count": result.get("observation_count", 0),
            "minimum_required_observation_count": minimum_count,
            "first_observation": result.get("first_observation"),
            "last_observation": result.get("last_observation"),
            "missing_required_periods": missing_required,
            "non_finite_periods": result.get("non_finite_periods", []),
            "dataset_updated": result.get("dataset_updated"),
        }

    all_units_present = set(results) == set(UNITS)
    promotion_eligible = (
        all_units_present
        and all(item["passed"] for item in unit_assessments.values())
    )

    report = {
        "audit_version": "0.1",
        "phase": "Reference Mode Recovery — Government Debt Stock",
        "reference_mode": "government_debt_stock",
        "dataset": "gov_10q_ggdebt",
        "geo": "RO",
        "sector": "S13",
        "na_item": "GD",
        "requested_start": contract["source"]["requested_start"],
        "requested_end": contract["source"]["requested_end"],
        "required_periods": list(REQUIRED_PERIODS),
        "unit_assessments": unit_assessments,
        "source_results": results,
        "promotion_eligible": promotion_eligible,
        "accounting_spine_changed": False,
        "behavioural_closure_changed": False,
        "promotion_status": (
            "OBSERVED_SERIES_EVIDENCE_READY_FOR_REPOSITORY_ASSESSMENT"
            if promotion_eligible
            else "REFERENCE_MODE_REMAINS_PARTIAL_SERIES_AVAILABLE"
        ),
        "interpretation": (
            "GD is retained only as quarterly general-government consolidated "
            "gross Maastricht debt at nominal/face value. It is an observed "
            "behaviour-over-time reference mode, not a replacement for "
            "market-valued financial-accounts liabilities or holder-by-issuer "
            "Accounting Spine cells."
        ),
    }

    report_path = OUT / "government_debt_stock_reference_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "unit_assessments": unit_assessments,
                "promotion_eligible": promotion_eligible,
                "promotion_status": report["promotion_status"],
            },
            indent=2,
        )
    )

    if not promotion_eligible:
        raise SystemExit(
            "Government-debt reference-mode source gate did not pass; "
            "see retained audit artifact."
        )


if __name__ == "__main__":
    main()
