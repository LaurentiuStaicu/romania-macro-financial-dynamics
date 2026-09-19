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
        "FX_INFLATION_MATERIALISATION_OUT",
        "fx_inflation_materialisation_artifacts",
    )
)
ECB_API = "https://data-api.ecb.europa.eu/service/data"
EUROSTAT_API = (
    "https://ec.europa.eu/eurostat/api/dissemination/"
    "statistics/1.0/data"
)
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fx_inflation_monthly_materialisation_contract.json"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub FX-inflation raw source materialisation)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finite_float(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite value: {value!r}")
    return result


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


def fetch(url: str, accept: str) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
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


def ecb_url(flow: str, key_without_flow: str, start_period: str) -> str:
    query = urllib.parse.urlencode(
        {
            "format": "csvdata",
            "startPeriod": start_period,
        }
    )
    return f"{ECB_API}/{flow}/{key_without_flow}?{query}"


def eurostat_url(dataset: str, dims: dict[str, str]) -> str:
    query = urllib.parse.urlencode(dims)
    return f"{EUROSTAT_API}/{dataset}?{query}"


def parse_ecb_monthly_csv(body: bytes) -> tuple[dict[str, float], dict]:
    text = body.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])
    required = {"TIME_PERIOD", "OBS_VALUE"}
    if not required.issubset(fields):
        raise ValueError(
            f"ECB CSV missing required columns: {sorted(required - fields)}"
        )

    observations: dict[str, float] = {}
    series_keys: set[str] = set()
    for row in reader:
        period = (row.get("TIME_PERIOD") or "").strip()[:7]
        raw = row.get("OBS_VALUE")
        if not period or raw in (None, ""):
            continue
        value = finite_float(raw)
        if period in observations:
            raise ValueError(f"duplicate ECB monthly period: {period}")
        observations[period] = value
        key = (row.get("KEY") or "").strip()
        if key:
            series_keys.add(key)

    if not observations:
        raise ValueError("ECB source contained no finite monthly observations")
    return observations, {
        "series_keys": sorted(series_keys),
        "observation_count": len(observations),
        "first_period": min(observations),
        "last_period": max(observations),
    }


def parse_eurostat_monthly_json(
    body: bytes,
    expected_dims: dict[str, str],
) -> tuple[dict[str, float], dict]:
    payload = json.loads(body.decode("utf-8-sig"))
    if payload.get("class") != "dataset":
        raise ValueError("Eurostat payload is not a dataset")

    ids = [str(item) for item in payload.get("id") or []]
    sizes = [int(item) for item in payload.get("size") or []]
    if len(ids) != len(sizes):
        raise ValueError("Eurostat id/size mismatch")

    dimension = payload.get("dimension", {})
    for dim, expected in expected_dims.items():
        if dim == "lang":
            continue
        if dim not in ids:
            raise ValueError(f"Eurostat dimension missing: {dim}")
        index = (
            dimension.get(dim, {})
            .get("category", {})
            .get("index", {})
        )
        codes = ordered_codes(index)
        if codes != [expected]:
            raise ValueError(
                f"Eurostat dimension {dim} returned {codes}, "
                f"expected exactly {[expected]}"
            )

    for dim, size in zip(ids, sizes):
        if dim != "time" and int(size) != 1:
            raise ValueError(
                f"Eurostat query returned multiple values for {dim}: {size}"
            )

    time_codes = ordered_codes(
        dimension.get("time", {})
        .get("category", {})
        .get("index", {})
    )
    values = payload.get("value", {})
    observations: dict[str, float] = {}
    for position, period in enumerate(time_codes):
        raw = value_at(values, position)
        if raw is None:
            continue
        month = str(period)[:7]
        if month in observations:
            raise ValueError(f"duplicate Eurostat month: {month}")
        observations[month] = finite_float(raw)

    if not observations:
        raise ValueError("Eurostat source contained no finite monthly observations")

    meta = {
        "updated": payload.get("updated"),
        "label": payload.get("label"),
        "id": ids,
        "size": sizes,
        "observation_count": len(observations),
        "first_period": min(observations),
        "last_period": max(observations),
    }
    return observations, meta


def write_raw(name: str, body: bytes) -> dict[str, object]:
    path = OUT / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {
        "path": str(path.relative_to(OUT)),
        "sha256": sha256(body),
        "bytes": len(body),
    }


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = load_contract()
    script_path = Path(__file__).resolve()
    script_hash = sha256(script_path.read_bytes())
    fetched_at = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    fx = contract["sources"]["exchange_rate"]
    hicp = contract["sources"]["hicp"]
    ext = contract["sources"]["external_price"]

    requests = {
        "exchange_rate": {
            "url": ecb_url(
                fx["flow"],
                fx["key_without_flow"],
                fx["start_period"],
            ),
            "accept": "text/csv,application/vnd.sdmx.data+csv,*/*",
            "raw_name": "ecb_exr_m_ron_eur_sp00_a.csv",
        },
        "hicp": {
            "url": eurostat_url(
                hicp["dataset"],
                hicp["exact_dimensions"],
            ),
            "accept": "application/json",
            "raw_name": "eurostat_prc_hicp_minr_ro_i25_total.json",
        },
        "external_price": {
            "url": eurostat_url(
                ext["dataset"],
                ext["exact_dimensions"],
            ),
            "accept": "application/json",
            "raw_name": (
                "eurostat_ext_st_27_2020msbec_ro_imp_world_total_ivu.json"
            ),
        },
    }

    fetched: dict[str, dict[str, object]] = {}
    parsed: dict[str, dict[str, float]] = {}
    metadata: dict[str, dict[str, object]] = {}

    for name, spec in requests.items():
        body, headers, status = fetch(spec["url"], spec["accept"])
        raw = write_raw(spec["raw_name"], body)
        fetched[name] = {
            "url": spec["url"],
            "http_status": status,
            "content_type": headers.get("Content-Type"),
            "last_modified": headers.get("Last-Modified"),
            **raw,
        }
        if status != 200:
            raise RuntimeError(
                f"{name} source returned HTTP {status}; raw evidence retained"
            )

        if name == "exchange_rate":
            obs, meta = parse_ecb_monthly_csv(body)
        elif name == "hicp":
            obs, meta = parse_eurostat_monthly_json(
                body,
                hicp["exact_dimensions"],
            )
        else:
            obs, meta = parse_eurostat_monthly_json(
                body,
                ext["exact_dimensions"],
            )
        parsed[name] = obs
        metadata[name] = meta

    common = sorted(
        set(parsed["exchange_rate"])
        & set(parsed["hicp"])
        & set(parsed["external_price"])
    )
    if not common:
        raise RuntimeError("no common finite monthly history across exact sources")

    gate = contract["completeness_gate"]
    if common[0] != gate["expected_first_common_period"]:
        raise RuntimeError(
            f"first common month {common[0]} differs from frozen "
            f"{gate['expected_first_common_period']}"
        )
    if len(common) < int(gate["minimum_common_months"]):
        raise RuntimeError(
            f"only {len(common)} common months; minimum is "
            f"{gate['minimum_common_months']}"
        )

    csv_path = OUT / "fx_inflation_monthly_raw_source.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=contract["output_schema"],
        )
        writer.writeheader()
        for period in common:
            writer.writerow(
                {
                    "period": period,
                    "ron_per_eur_monthly_average": (
                        f"{parsed['exchange_rate'][period]:.12g}"
                    ),
                    "hicp_total_2025_100": (
                        f"{parsed['hicp'][period]:.12g}"
                    ),
                    "import_uvi_total_world_2021_100": (
                        f"{parsed['external_price'][period]:.12g}"
                    ),
                    "source_completeness": "COMPLETE_LEVELS_ONLY",
                }
            )

    csv_body = csv_path.read_bytes()
    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "mechanism_id": contract["mechanism_id"],
        "generated_at_utc": fetched_at,
        "materializer_script": (
            "scripts/audit_fx_inflation_monthly_materialisation.py"
        ),
        "materializer_script_sha256": script_hash,
        "status": (
            "SOURCE_MATERIALISATION_EVIDENCE_READY_FOR_REPOSITORY_REVIEW"
        ),
        "estimation_authorized": False,
        "source_results": {
            name: {
                **fetched[name],
                "metadata": metadata[name],
            }
            for name in fetched
        },
        "coverage": {
            "common_observation_count": len(common),
            "first_common_period": common[0],
            "last_common_period": common[-1],
        },
        "output": {
            "path": str(csv_path.relative_to(OUT)),
            "sha256": sha256(csv_body),
            "rows": len(common),
        },
        "hard_rules": contract["hard_rules"],
        "transformations_performed": [],
        "calibration_cycle_open": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    audit_path = OUT / "fx_inflation_monthly_materialisation_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "fx-inflation-monthly-levels-vintage-2026-09-19",
        "fetched_at_utc": fetched_at,
        "source_vintage_contract": (
            "data/provenance/source_vintage_contract.json"
        ),
        "materializer_script": (
            "scripts/audit_fx_inflation_monthly_materialisation.py"
        ),
        "materializer_script_sha256": script_hash,
        "workflow_context": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "raw_sources": [
            {
                "name": name,
                **fetched[name],
                "provider_metadata": metadata[name],
            }
            for name in ("exchange_rate", "hicp", "external_price")
        ],
        "normalized_outputs": [
            {
                "path": str(csv_path.relative_to(OUT)),
                "sha256": sha256(csv_body),
                "derived_from_raw_sha256": [
                    fetched[name]["sha256"]
                    for name in (
                        "exchange_rate",
                        "hicp",
                        "external_price",
                    )
                ],
                "normalizer": (
                    "scripts/audit_fx_inflation_monthly_materialisation.py"
                ),
                "normalizer_sha256": script_hash,
                "rows": len(common),
                "transformations": [],
            }
        ],
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
                "coverage": audit["coverage"],
                "output": audit["output"],
                "transformations_performed": [],
                "estimation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
