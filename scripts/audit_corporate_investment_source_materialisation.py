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
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "CORPORATE_INVESTMENT_MATERIALISATION_OUT",
        "corporate_investment_materialisation_artifacts",
    )
)
ECB_API = "https://data-api.ecb.europa.eu/service/data"
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "corporate_investment_materialisation_contract.json"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub corporate-investment source materialisation)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,application/vnd.sdmx.data+csv,*/*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return (
                    response.read(),
                    dict(response.headers.items()),
                    int(response.status),
                )
        except urllib.error.HTTPError as exc:
            return exc.read(), dict(exc.headers.items()), int(exc.code)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                raise RuntimeError(
                    f"network failure after {attempt} attempts: {url}: {exc}"
                ) from exc
    raise RuntimeError(f"unreachable fetch state: {last_error}")


def ecb_url(flow: str, series_key: str) -> str:
    prefix = f"{flow}."
    if not series_key.startswith(prefix):
        raise ValueError(
            f"series key {series_key!r} does not match flow {flow!r}"
        )
    key = series_key[len(prefix):]
    query = urllib.parse.urlencode({"format": "csvdata"})
    return f"{ECB_API}/{flow}/{key}?{query}"


def parse_ecb_csv(
    body: bytes,
    *,
    expected_key: str,
) -> tuple[list[tuple[str, float]], dict[str, object]]:
    text = body.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])
    required = {"TIME_PERIOD", "OBS_VALUE"}
    if not required.issubset(fields):
        raise ValueError(
            f"ECB CSV missing required columns: {sorted(required-fields)}"
        )

    observations: list[tuple[str, float]] = []
    seen_periods: set[str] = set()
    keys: set[str] = set()
    units: set[str] = set()
    titles: set[str] = set()
    for row in reader:
        period = (row.get("TIME_PERIOD") or "").strip()
        raw = row.get("OBS_VALUE")
        if not period or raw in (None, ""):
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite observation at {period}")
        if period in seen_periods:
            raise ValueError(f"duplicate observation period: {period}")
        seen_periods.add(period)
        observations.append((period, value))
        key = (row.get("KEY") or "").strip()
        if key:
            keys.add(key)
        unit = (row.get("UNIT") or row.get("UNIT_NAME") or "").strip()
        if unit:
            units.add(unit)
        title = (row.get("TITLE") or "").strip()
        if title:
            titles.add(title)

    if not observations:
        raise ValueError("ECB CSV contained no finite observations")
    if keys and keys != {expected_key}:
        raise ValueError(
            f"provider KEY mismatch: {sorted(keys)} != {[expected_key]}"
        )
    observations.sort(key=lambda item: item[0])
    return observations, {
        "series_keys": sorted(keys),
        "units": sorted(units),
        "titles": sorted(titles),
        "observation_count": len(observations),
        "first_period": observations[0][0],
        "last_period": observations[-1][0],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    script_path = Path(__file__).resolve()
    script_hash = sha256(script_path.read_bytes())
    fetched_at = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    output_files = contract["output_files"]
    source_results = []
    normalized_outputs = []

    for source in contract["sources"]:
        url = ecb_url(source["flow"], source["series_key"])
        body, headers, status = fetch(url)
        raw_path = OUT / "raw" / f'{source["id"]}.csv'
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)
        raw_hash = sha256(body)

        if status != 200:
            raise RuntimeError(
                f'{source["id"]} returned HTTP {status}; raw evidence retained'
            )

        observations, metadata = parse_ecb_csv(
            body,
            expected_key=source["series_key"],
        )
        normalized_path = OUT / output_files[source["id"]]
        with normalized_path.open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["period", "value", "source_status"],
            )
            writer.writeheader()
            for period, value in observations:
                writer.writerow(
                    {
                        "period": period,
                        "value": f"{value:.12g}",
                        "source_status": "FINITE_PROVIDER_OBSERVATION",
                    }
                )

        normalized_body = normalized_path.read_bytes()
        source_results.append(
            {
                "id": source["id"],
                "series_key": source["series_key"],
                "url": url,
                "http_status": status,
                "content_type": headers.get("Content-Type"),
                "last_modified": headers.get("Last-Modified"),
                "raw_path": str(raw_path.relative_to(OUT)),
                "raw_sha256": raw_hash,
                "raw_bytes": len(body),
                "metadata": metadata,
                "role": source["role"],
            }
        )
        normalized_outputs.append(
            {
                "source_id": source["id"],
                "path": str(normalized_path.relative_to(OUT)),
                "sha256": sha256(normalized_body),
                "rows": len(observations),
                "first_period": observations[0][0],
                "last_period": observations[-1][0],
                "derived_from_raw_sha256": [raw_hash],
                "transformations": [],
            }
        )

    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "mechanism_id": contract["mechanism_id"],
        "generated_at_utc": fetched_at,
        "materializer_script": (
            "scripts/audit_corporate_investment_source_materialisation.py"
        ),
        "materializer_script_sha256": script_hash,
        "status": (
            "SOURCE_FAMILY_EVIDENCE_READY_FOR_REPOSITORY_REVIEW"
        ),
        "estimation_authorized": False,
        "source_results": source_results,
        "normalized_outputs": normalized_outputs,
        "hard_rules": contract["hard_rules"],
        "target_selected": False,
        "cross_frequency_join_performed": False,
        "rate_aggregation_performed": False,
        "growth_or_deflation_transform_performed": False,
        "calibration_cycle_open": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    audit_path = OUT / "corporate_investment_materialisation_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "corporate-investment-source-family-vintage-2026-09-19",
        "fetched_at_utc": fetched_at,
        "source_vintage_contract": (
            "data/provenance/source_vintage_contract.json"
        ),
        "materializer_script": (
            "scripts/audit_corporate_investment_source_materialisation.py"
        ),
        "materializer_script_sha256": script_hash,
        "workflow_context": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "raw_sources": source_results,
        "normalized_outputs": normalized_outputs,
        "audit_report": {
            "path": str(audit_path.relative_to(OUT)),
            "sha256": sha256(audit_path.read_bytes()),
        },
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
                "status": audit["status"],
                "coverage": {
                    item["source_id"]: {
                        "rows": item["rows"],
                        "first_period": item["first_period"],
                        "last_period": item["last_period"],
                    }
                    for item in normalized_outputs
                },
                "target_selected": False,
                "estimation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
