from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "FISCAL_PRIMARY_BALANCE_OUT",
        "fiscal_primary_balance_artifacts",
    )
)
API = (
    "https://ec.europa.eu/eurostat/api/dissemination/"
    "statistics/1.0/data/gov_10q_ggnfa"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub fiscal-primary-balance source materialisation)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ordered_codes(index: object) -> list[str]:
    if isinstance(index, list):
        return [str(item) for item in index]
    if isinstance(index, dict):
        return [
            str(code)
            for code, _ in sorted(
                index.items(), key=lambda item: int(item[1])
            )
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


def normalise_quarter(period: str) -> str:
    value = period.strip()
    if len(value) == 6 and value[4] == "Q" and value[5] in "1234":
        return f"{value[:4]}-Q{value[5]}"
    if len(value) == 7 and value[4:6] == "-Q" and value[6] in "1234":
        return value
    raise ValueError(f"invalid quarterly period: {period!r}")


def parse_eurostat(body: bytes) -> tuple[dict[str, float], dict]:
    payload = json.loads(body.decode("utf-8-sig"))
    if payload.get("class") != "dataset":
        raise ValueError("Eurostat payload is not a dataset")

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if len(ids) != len(sizes):
        raise ValueError("Eurostat id/size mismatch")
    for dim, size in zip(ids, sizes):
        if dim != "time" and int(size) != 1:
            raise ValueError(
                f"query returned more than one value for {dim}: {size}"
            )

    time_cat = (
        payload.get("dimension", {})
        .get("time", {})
        .get("category", {})
    )
    periods = ordered_codes(time_cat.get("index", {}))
    values = payload.get("value", {})

    observations: dict[str, float] = {}
    for position, period in enumerate(periods):
        raw = value_at(values, position)
        if raw is None:
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite value at {period}: {raw!r}")
        quarter = normalise_quarter(period)
        if quarter in observations:
            raise ValueError(f"duplicate period: {quarter}")
        observations[quarter] = value

    if not observations:
        raise ValueError("no finite Eurostat observations")
    metadata = {
        "updated": payload.get("updated"),
        "label": payload.get("label"),
        "id": ids,
        "size": sizes,
    }
    return observations, metadata


def primary_balance(overall_balance: float, interest: float) -> float:
    overall = float(overall_balance)
    interest_value = float(interest)
    if not math.isfinite(overall) or not math.isfinite(interest_value):
        raise ValueError("primary-balance components must be finite")
    return overall + interest_value


def fetch_item(contract: dict, na_item: str) -> dict[str, object]:
    source = contract["source"]
    query = urllib.parse.urlencode(
        {
            "lang": "en",
            "freq": source["frequency"],
            "unit": source["unit"],
            "s_adj": source["seasonal_adjustment"],
            "sector": source["sector"],
            "na_item": na_item,
            "geo": source["geo"],
            "sinceTimePeriod": source["start_period"],
        }
    )
    url = f"{API}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    body = b""
    status = 0
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
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
                    "na_item": na_item,
                    "url": url,
                    "status": "NETWORK_ERROR",
                    "error": str(last_error),
                    "observations": {},
                }
    else:
        raise AssertionError("unreachable retry state")

    raw_path = OUT / "raw" / f"gov_10q_ggnfa_RO_{na_item}_NSA_PC_GDP.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    result: dict[str, object] = {
        "na_item": na_item,
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
        return result

    try:
        observations, metadata = parse_eurostat(body)
    except Exception as exc:
        result["status"] = "PARSE_ERROR"
        result["error"] = str(exc)
        return result

    result.update(
        {
            "status": "AVAILABLE",
            "metadata": metadata,
            "observations": observations,
            "observation_count": len(observations),
            "first_period": min(observations),
            "last_period": max(observations),
        }
    )
    return result


def load_contract() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "calibration_validation"
            / "fiscal_primary_balance_materialisation_contract.json"
        ).read_text(encoding="utf-8")
    )


def load_retained_interest_snapshot() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "dynamics"
            / "government_interest_burden_reference_snapshot.json"
        ).read_text(encoding="utf-8")
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = load_contract()
    fetcher_script_path = Path(__file__).resolve()
    fetcher_script_sha256 = sha256(fetcher_script_path.read_bytes())
    fetched_at_utc = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    items = contract["source"]["items"]

    b9 = fetch_item(contract, items["overall_balance"]["na_item"])
    interest = fetch_item(
        contract,
        items["interest_expenditure"]["na_item"],
    )

    for name, result in (("B9", b9), ("D41PAY", interest)):
        if result.get("status") != "AVAILABLE":
            report = {
                "audit_version": "0.1",
                "phase": contract["phase"],
                "status": "LIVE_SOURCE_GATE_FAILED",
                "failed_component": name,
                "source_results": {"B9": b9, "D41PAY": interest},
                "calibration_cycle_open": False,
            }
            (OUT / "fiscal_primary_balance_materialisation_audit.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            raise SystemExit(f"{name} source not available")

    b9_updated = b9["metadata"].get("updated")
    interest_updated = interest["metadata"].get("updated")
    if b9_updated != interest_updated:
        raise SystemExit(
            "B9 and D41PAY provider payloads have different updated metadata; "
            "matched-vintage primary balance is not materialised"
        )

    b9_obs = {str(k): float(v) for k, v in b9["observations"].items()}
    int_obs = {
        str(k): float(v) for k, v in interest["observations"].items()
    }
    common = sorted(set(b9_obs) & set(int_obs))
    minimum = int(
        contract["completeness_gate"]["minimum_common_observations"]
    )
    if len(common) < minimum:
        raise SystemExit(
            f"only {len(common)} common observations; minimum is {minimum}"
        )

    retained = load_retained_interest_snapshot()
    retained_interest = {
        str(k): float(v)
        for k, v in retained["series"]["PC_GDP"]["observations"].items()
    }
    overlap = sorted(set(retained_interest) & set(int_obs))
    retained_diffs = {
        period: int_obs[period] - retained_interest[period]
        for period in overlap
    }
    max_abs_retained_diff = (
        max(abs(v) for v in retained_diffs.values())
        if retained_diffs
        else None
    )

    csv_path = OUT / "fiscal_primary_balance_quarterly_source.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = contract["output_schema"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for period in common:
            writer.writerow(
                {
                    "period": period,
                    "net_lending_borrowing_pct_gdp": f"{b9_obs[period]:.12g}",
                    "interest_expenditure_pct_gdp": f"{int_obs[period]:.12g}",
                    "primary_balance_pct_gdp": f"{primary_balance(b9_obs[period], int_obs[period]):.12g}",
                    "source_completeness": "COMPLETE",
                }
            )

    csv_body = csv_path.read_bytes()
    report = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "generated_at_utc": fetched_at_utc,
        "fetcher_script": "scripts/audit_fiscal_primary_balance_materialisation.py",
        "fetcher_script_sha256": fetcher_script_sha256,
        "status": "SOURCE_MATERIALISATION_EVIDENCE_READY_FOR_REPOSITORY_REVIEW",
        "estimation_authorized": False,
        "provider_dataset_updated": b9_updated,
        "source_results": {
            "B9": {
                key: value
                for key, value in b9.items()
                if key != "observations"
            },
            "D41PAY": {
                key: value
                for key, value in interest.items()
                if key != "observations"
            },
        },
        "coverage": {
            "common_observation_count": len(common),
            "first_common_period": common[0],
            "last_common_period": common[-1],
        },
        "measurement_identity": contract["measurement_identity"],
        "retained_interest_snapshot_diagnostic": {
            "overlap_count": len(overlap),
            "max_absolute_live_minus_retained_pp": max_abs_retained_diff,
            "hard_equality_gate": False,
            "reason": "The retained snapshot is a prior vintage cross-check only; the matched primary-balance source uses live B9 and D41PAY from the same provider vintage.",
        },
        "output": {
            "path": str(csv_path.relative_to(OUT)),
            "sha256": sha256(csv_body),
            "rows": len(common),
        },
        "hard_rules": contract["hard_rules"],
        "calibration_cycle_open": False,
        "validated_reference_behavioural_mechanisms_change": 0,
        "central_feedback_activation": False,
    }
    report_path = OUT / "fiscal_primary_balance_materialisation_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    raw_sources = []
    for name, result in (("B9", b9), ("D41PAY", interest)):
        raw_sources.append(
            {
                "name": name,
                "institution": contract["source"]["institution"],
                "url": result["url"],
                "accept": "application/json",
                "status": result["http_status"],
                "content_type": result["content_type"],
                "bytes": result["raw_bytes"],
                "sha256": result["raw_sha256"],
                "path": result["raw_path"],
                "dataset_updated": result["metadata"].get("updated"),
            }
        )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "fiscal-primary-balance-quarterly-vintage-2026-09-19",
        "fetched_at_utc": fetched_at_utc,
        "source_vintage_contract": "data/provenance/source_vintage_contract.json",
        "fetcher_script": "scripts/audit_fiscal_primary_balance_materialisation.py",
        "fetcher_script_sha256": fetcher_script_sha256,
        "workflow_context": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "raw_sources": raw_sources,
        "normalized_outputs": [
            {
                "path": str(csv_path.relative_to(OUT)),
                "sha256": sha256(csv_body),
                "derived_from_raw_sha256": [
                    b9["raw_sha256"],
                    interest["raw_sha256"],
                ],
                "normalizer": "scripts/audit_fiscal_primary_balance_materialisation.py",
                "normalizer_sha256": fetcher_script_sha256,
                "rows": len(common),
            }
        ],
        "audit_report": {
            "path": str(report_path.relative_to(OUT)),
            "sha256": sha256(report_path.read_bytes()),
        },
        "matched_dataset_updated": b9_updated,
        "hard_boundaries": contract["hard_rules"],
        "canonical_promotion": (
            "REQUIRES_EXPLICIT_REPOSITORY_REVIEW_AND_COMMIT"
        ),
    }
    (OUT / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "coverage": report["coverage"],
                "output": report["output"],
                "calibration_cycle_open": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
