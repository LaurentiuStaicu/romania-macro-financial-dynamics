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
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "SOVEREIGN_YIELD_MATERIALISATION_OUT",
        "sovereign_yield_materialisation_artifacts",
    )
)
ECB_API = "https://data-api.ecb.europa.eu/service/data"
EUROSTAT_API = (
    "https://ec.europa.eu/eurostat/api/dissemination/"
    "statistics/1.0/data/gov_10q_ggnfa"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub sovereign-yield source materialisation)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_quarter(period: str) -> str:
    value = period.strip()
    if len(value) == 7 and value[4:6] == "-Q" and value[6] in "1234":
        return value
    if len(value) == 6 and value[4] == "Q" and value[5] in "1234":
        return f"{value[:4]}-Q{value[5]}"
    raise ValueError(f"invalid quarterly period: {period!r}")


def quarter_from_month(period: str) -> str:
    year_text, month_text = period.split("-", 1)
    month = int(month_text[:2])
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {period}")
    return f"{int(year_text):04d}-Q{((month - 1) // 3) + 1}"


def month_from_date(period: str) -> str:
    parsed = date.fromisoformat(period[:10])
    return f"{parsed.year:04d}-{parsed.month:02d}"


def finite_float(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite value: {value!r}")
    return result


def parse_ecb_csv(body: bytes) -> list[tuple[str, float]]:
    text = body.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])
    required = {"TIME_PERIOD", "OBS_VALUE"}
    if not required.issubset(fields):
        raise ValueError(
            f"ECB CSV missing required columns: {sorted(required - fields)}"
        )

    rows: list[tuple[str, float]] = []
    for row in reader:
        period = (row.get("TIME_PERIOD") or "").strip()
        raw = row.get("OBS_VALUE")
        if not period or raw in (None, ""):
            continue
        rows.append((period, finite_float(raw)))
    if not rows:
        raise ValueError("ECB CSV contained no finite observations")
    return rows


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


def parse_eurostat_json(body: bytes) -> tuple[list[tuple[str, float]], dict]:
    payload = json.loads(body.decode("utf-8-sig"))
    if payload.get("class") != "dataset":
        raise ValueError("Eurostat response is not a JSON-stat dataset")

    ids = payload.get("id") or []
    sizes = payload.get("size") or []
    if len(ids) != len(sizes):
        raise ValueError("Eurostat id/size dimension mismatch")
    for dim, size in zip(ids, sizes):
        if dim != "time" and int(size) != 1:
            raise ValueError(
                f"Eurostat query returned multiple values for {dim}: {size}"
            )

    time_cat = (
        payload.get("dimension", {})
        .get("time", {})
        .get("category", {})
    )
    codes = ordered_codes(time_cat.get("index", {}))
    values = payload.get("value", {})

    rows: list[tuple[str, float]] = []
    for position, period in enumerate(codes):
        raw = value_at(values, position)
        if raw is None:
            continue
        rows.append((normalize_quarter(period), finite_float(raw)))
    if not rows:
        raise ValueError("Eurostat response contained no finite observations")
    meta = {
        "updated": payload.get("updated"),
        "label": payload.get("label"),
        "id": ids,
        "size": sizes,
    }
    return rows, meta


def complete_quarterly_monthly_mean(
    rows: Iterable[tuple[str, float]],
) -> dict[str, float]:
    grouped: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for period, value in rows:
        month = period[:7]
        grouped[quarter_from_month(month)].append((month, value))

    result: dict[str, float] = {}
    for quarter, items in grouped.items():
        unique = {period: value for period, value in items}
        q = int(quarter[-1])
        first_month = 3 * (q - 1) + 1
        year = quarter[:4]
        expected = {
            f"{year}-{first_month:02d}",
            f"{year}-{first_month + 1:02d}",
            f"{year}-{first_month + 2:02d}",
        }
        if set(unique) == expected:
            result[quarter] = sum(unique.values()) / 3.0
    return result


def equal_weight_daily_to_quarter(
    rows: Iterable[tuple[str, float]],
) -> dict[str, float]:
    by_month: dict[str, list[float]] = defaultdict(list)
    for period, value in rows:
        by_month[month_from_date(period)].append(value)

    monthly = {
        month: sum(values) / len(values)
        for month, values in by_month.items()
        if values
    }
    return complete_quarterly_monthly_mean(monthly.items())


def fetch(url: str) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
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


def ecb_url(flow: str, full_key: str, start_period: str) -> str:
    prefix = f"{flow}."
    if not full_key.startswith(prefix):
        raise ValueError(f"key {full_key!r} does not start with {prefix!r}")
    key = full_key[len(prefix):]
    query = urllib.parse.urlencode(
        {
            "format": "csvdata",
            "startPeriod": start_period,
        }
    )
    return f"{ECB_API}/{flow}/{key}?{query}"


def eurostat_b9_url(contract: dict) -> str:
    dims = contract["fiscal_controls"]["net_lending_borrowing_to_gdp"][
        "exact_provider_tuple"
    ]
    query = urllib.parse.urlencode({"lang": "en", **dims})
    return f"{EUROSTAT_API}?{query}"


def load_contract() -> dict:
    return json.loads(
        (
            ROOT
            / "model"
            / "calibration_validation"
            / "sovereign_yield_quarterly_materialisation_contract.json"
        ).read_text(encoding="utf-8")
    )


def load_debt_snapshot() -> tuple[dict[str, float], str]:
    path = (
        ROOT
        / "model"
        / "dynamics"
        / "government_debt_stock_reference_snapshot.json"
    )
    body = path.read_bytes()
    payload = json.loads(body.decode("utf-8"))
    observations = payload["series"]["PC_GDP"]["observations"]
    return (
        {str(period): finite_float(value) for period, value in observations.items()},
        sha256(body),
    )


def write_raw(name: str, body: bytes) -> dict[str, object]:
    path = OUT / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {
        "path": str(path.relative_to(OUT)),
        "sha256": sha256(body),
        "bytes": len(body),
    }


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

    target_key = contract["target"]["series_key"]
    benchmark_key = contract["common_long_rate_control"]["series_key"]
    ciss_key = contract["financial_stress_control"]["series_key"]

    requests = {
        "romania_yield": ecb_url("IRS", target_key, "2005-04"),
        "germany_yield": ecb_url("IRS", benchmark_key, "2005-04"),
        "new_ciss": ecb_url("CISS", ciss_key, "2005-04-01"),
        "b9": eurostat_b9_url(contract),
    }

    fetched: dict[str, dict[str, object]] = {}
    parsed: dict[str, object] = {}
    for name, url in requests.items():
        body, headers, status = fetch(url)
        raw = write_raw(
            {
                "romania_yield": "ecb_irs_ro_10y.csv",
                "germany_yield": "ecb_irs_de_10y.csv",
                "new_ciss": "ecb_new_ciss_u2.csv",
                "b9": "eurostat_gov_10q_ggnfa_ro_b9_sca_pc_gdp.json",
            }[name],
            body,
        )
        fetched[name] = {
            "url": url,
            "http_status": status,
            "content_type": headers.get("Content-Type"),
            "last_modified": headers.get("Last-Modified"),
            **raw,
        }
        if status != 200:
            raise RuntimeError(
                f"{name} source returned HTTP {status}; evidence retained in {raw['path']}"
            )

        if name == "b9":
            rows, meta = parse_eurostat_json(body)
            parsed[name] = {"rows": rows, "metadata": meta}
        else:
            parsed[name] = {"rows": parse_ecb_csv(body)}

    ro_q = complete_quarterly_monthly_mean(parsed["romania_yield"]["rows"])
    de_q = complete_quarterly_monthly_mean(parsed["germany_yield"]["rows"])
    ciss_q = equal_weight_daily_to_quarter(parsed["new_ciss"]["rows"])
    b9_q = dict(parsed["b9"]["rows"])
    debt_q, debt_snapshot_sha = load_debt_snapshot()

    common = sorted(
        set(ro_q)
        & set(de_q)
        & set(ciss_q)
        & set(b9_q)
        & set(debt_q)
    )
    common = [period for period in common if period >= "2005-Q2"]
    if not common:
        raise RuntimeError("no complete common quarterly history across mandatory sources")

    csv_path = OUT / "sovereign_yield_quarterly_source.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = contract["output_schema"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for period in common:
            writer.writerow(
                {
                    "period": period,
                    "romania_10y_yield_pct": f"{ro_q[period]:.12g}",
                    "germany_10y_yield_pct": f"{de_q[period]:.12g}",
                    "euro_area_new_ciss": f"{ciss_q[period]:.12g}",
                    "government_debt_pct_gdp": f"{debt_q[period]:.12g}",
                    "government_net_lending_borrowing_pct_gdp": f"{b9_q[period]:.12g}",
                    "source_completeness": "COMPLETE",
                }
            )

    csv_body = csv_path.read_bytes()
    report = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "mechanism_id": contract["mechanism_id"],
        "estimation_authorized": False,
        "generated_at_utc": fetched_at_utc,
        "fetcher_script": "scripts/audit_sovereign_yield_quarterly_materialisation.py",
        "fetcher_script_sha256": fetcher_script_sha256,
        "source_requests": fetched,
        "source_metadata": {
            "eurostat_b9": parsed["b9"]["metadata"],
            "retained_debt_snapshot_sha256": debt_snapshot_sha,
        },
        "transformations": {
            "romania_yield": contract["target"]["quarterly_rule"],
            "germany_yield": contract["common_long_rate_control"]["quarterly_rule"],
            "new_ciss": contract["financial_stress_control"]["aggregation_rule"],
            "debt": contract["fiscal_controls"]["debt_to_gdp"]["aggregation"],
            "b9": contract["fiscal_controls"]["net_lending_borrowing_to_gdp"]["aggregation"],
        },
        "quarterly_coverage": {
            "romania_yield_complete_quarters": len(ro_q),
            "germany_yield_complete_quarters": len(de_q),
            "new_ciss_complete_quarters": len(ciss_q),
            "b9_quarters": len(b9_q),
            "debt_quarters": len(debt_q),
            "common_complete_quarters": len(common),
            "first_common_quarter": common[0],
            "last_common_quarter": common[-1],
        },
        "output": {
            "path": str(csv_path.relative_to(OUT)),
            "sha256": sha256(csv_body),
            "rows": len(common),
        },
        "hard_boundaries": contract["hard_rules"],
        "disposition": (
            "SOURCE_MATERIALISATION_EVIDENCE_READY_FOR_REPOSITORY_REVIEW"
        ),
        "interpretation": (
            "This run materializes source evidence only. It does not estimate "
            "a sovereign-yield equation, identify causal fiscal coefficients, "
            "validate a behavioural mechanism, or activate a feedback loop."
        ),
    }

    report_path = OUT / "sovereign_yield_quarterly_materialisation_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    raw_institutions = {
        "romania_yield": "European Central Bank / ESCB",
        "germany_yield": "European Central Bank / ESCB",
        "new_ciss": "European Central Bank / ESCB",
        "b9": "Eurostat",
    }
    raw_sources = []
    for name, meta in fetched.items():
        raw_sources.append(
            {
                "name": name,
                "institution": raw_institutions[name],
                "url": meta["url"],
                "accept": "*/*",
                "status": meta["http_status"],
                "content_type": meta["content_type"],
                "last_modified": meta["last_modified"],
                "bytes": meta["bytes"],
                "sha256": meta["sha256"],
                "path": meta["path"],
            }
        )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "sovereign-yield-quarterly-vintage-2026-09-19",
        "fetched_at_utc": fetched_at_utc,
        "source_vintage_contract": "data/provenance/source_vintage_contract.json",
        "fetcher_script": (
            "scripts/audit_sovereign_yield_quarterly_materialisation.py"
        ),
        "fetcher_script_sha256": fetcher_script_sha256,
        "workflow_context": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "raw_sources": raw_sources,
        "repository_inputs": [
            {
                "path": (
                    "model/dynamics/"
                    "government_debt_stock_reference_snapshot.json"
                ),
                "sha256": debt_snapshot_sha,
                "role": "quarterly Maastricht debt-to-GDP control",
            }
        ],
        "normalized_outputs": [
            {
                "path": str(csv_path.relative_to(OUT)),
                "sha256": sha256(csv_body),
                "derived_from_raw_sha256": [
                    fetched[name]["sha256"]
                    for name in (
                        "romania_yield",
                        "germany_yield",
                        "new_ciss",
                        "b9",
                    )
                ],
                "repository_input_sha256": [debt_snapshot_sha],
                "normalizer": (
                    "scripts/audit_sovereign_yield_quarterly_materialisation.py"
                ),
                "normalizer_sha256": fetcher_script_sha256,
                "rows": len(common),
            }
        ],
        "audit_report": {
            "path": str(report_path.relative_to(OUT)),
            "sha256": sha256(report_path.read_bytes()),
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
                "coverage": report["quarterly_coverage"],
                "output": report["output"],
                "disposition": report["disposition"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
