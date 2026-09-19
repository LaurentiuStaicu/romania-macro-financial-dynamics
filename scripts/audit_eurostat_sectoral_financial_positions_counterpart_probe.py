from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "dynamics"
    / "sectoral_financial_positions_eurostat_counterpart_probe_contract.json"
)
OUT = Path(
    os.environ.get(
        "EUROSTAT_COUNTERPART_PROBE_OUT",
        "sectoral_financial_positions_eurostat_counterpart_probe_artifacts",
    )
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+Eurostat sectoral-financial-position counterpart discovery probe)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(
    url: str,
    *,
    timeout: int = 60,
    attempts: int = 2,
) -> tuple[bytes, dict[str, str], int | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,application/json-stat+json,*/*",
        },
    )
    last_error: str | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return (
                    response.read(),
                    dict(response.headers.items()),
                    int(response.status),
                    None,
                )
        except urllib.error.HTTPError as exc:
            return (
                exc.read(),
                dict(exc.headers.items()),
                int(exc.code),
                f"HTTPError:{exc.code}",
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}:{exc}"
            if attempt < attempts:
                time.sleep(1)
    return b"", {}, None, last_error


def category_codes(dimension: dict) -> list[str]:
    category = dimension.get("category", {})
    index = category.get("index", {})
    if isinstance(index, dict):
        return [
            code
            for code, _ in sorted(
                index.items(),
                key=lambda item: item[1],
            )
        ]
    if isinstance(index, list):
        return [str(code) for code in index]
    return []


def non_null_observation_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(item is not None for item in value.values())
    if isinstance(value, list):
        return sum(item is not None for item in value)
    return 0


def inspect_json_stat(payload: dict) -> dict:
    dimension_ids = payload.get("id")
    dimension_sizes = payload.get("size")
    dimensions = payload.get("dimension")
    if not isinstance(dimension_ids, list):
        raise ValueError("JSON-stat payload lacks top-level dimension id list")
    if not isinstance(dimension_sizes, list):
        raise ValueError("JSON-stat payload lacks top-level size list")
    if not isinstance(dimensions, dict):
        raise ValueError("JSON-stat payload lacks dimension object")
    if len(dimension_ids) != len(dimension_sizes):
        raise ValueError("JSON-stat dimension id/size lengths differ")

    codes: dict[str, list[str]] = {}
    for dimension_id in dimension_ids:
        dimension = dimensions.get(dimension_id)
        if not isinstance(dimension, dict):
            raise ValueError(f"Missing dimension metadata for {dimension_id}")
        codes[dimension_id] = category_codes(dimension)

    return {
        "dimension_ids": [str(item) for item in dimension_ids],
        "dimension_sizes": [int(item) for item in dimension_sizes],
        "category_codes_by_dimension": codes,
        "non_null_observation_count": non_null_observation_count(
            payload.get("value")
        ),
        "geo_codes": codes.get("geo", []),
        "time_codes": codes.get("time", []),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    scope = contract["query_scope"]
    query = urllib.parse.urlencode(
        {
            "lang": scope["lang"],
            "geo": scope["geo"],
            "sinceTimePeriod": scope["sinceTimePeriod"],
            "untilTimePeriod": scope["untilTimePeriod"],
        }
    )
    url = f'{contract["provider"]["statistics_api_url"]}?{query}'

    body, headers, status, error = fetch(url)
    raw_path = OUT / "nasq_10_f_cp_ro_recent.json"
    if body:
        raw_path.write_bytes(body)

    parse_error: str | None = None
    summary = {
        "dimension_ids": [],
        "dimension_sizes": [],
        "category_codes_by_dimension": {},
        "non_null_observation_count": 0,
        "geo_codes": [],
        "time_codes": [],
    }
    if status == 200 and body:
        try:
            payload = json.loads(body.decode("utf-8"))
            summary = inspect_json_stat(payload)
        except Exception as exc:
            parse_error = f"{type(exc).__name__}:{exc}"

    rule = contract["discovery_pass_rule"]
    required_dimensions = set(rule["required_dimension_ids"])
    pass_gate = (
        status == rule["required_http_status"]
        and parse_error is None
        and required_dimensions <= set(summary["dimension_ids"])
        and rule["required_geo_identity"] in summary["geo_codes"]
        and summary["non_null_observation_count"]
        >= rule["minimum_non_null_observations"]
    )

    audit = {
        "audit_version": "0.1",
        "generated_at_utc": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "phase": contract["phase"],
        "reference_mode": contract["reference_mode"],
        "formal_reference_mode_gate": False,
        "dataset_code": contract["provider"]["dataset_code"],
        "request_url": url,
        "http_status": status,
        "error": error,
        "content_type": headers.get("Content-Type"),
        "bytes": len(body),
        "sha256": sha256(body) if body else None,
        "parse_error": parse_error,
        **summary,
        "discovery_gate_pass": pass_gate,
        "disposition": (
            rule["effect_if_pass"]
            if pass_gate
            else rule["effect_if_fail"]
        ),
        "semantic_mapping_performed": False,
        "instrument_mapping_performed": False,
        "counterpart_orientation_mapping_performed": False,
        "historical_coverage_claim_performed": False,
        "reconciliation_test_performed": False,
        "historical_phase_A_D_reinterpreted": False,
        "reference_mode_promotion": False,
        "accounting_readiness_change": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
    }
    (
        OUT
        / "sectoral_financial_positions_eurostat_counterpart_probe.json"
    ).write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
