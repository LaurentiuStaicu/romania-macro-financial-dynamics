from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from io import BytesIO, StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "FISCAL_REACTION_AMECO_MATERIALISATION_OUT",
        "fiscal_reaction_ameco_materialisation_artifacts",
    )
)
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fiscal_reaction_ameco_materialisation_contract.json"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub AMECO fiscal-reaction annual source materialisation)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/zip,*/*"},
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


def decode_member(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("AMECO member is not decodable text")


def selected_row(
    member_bytes: bytes,
    expected_code: str,
    expected_country: str,
    expected_concept: str,
    expected_unit: str,
) -> tuple[list[str], list[str], bytes]:
    text = decode_member(member_bytes)
    reader = csv.reader(StringIO(text), delimiter=";")
    rows = list(reader)
    if not rows:
        raise ValueError("empty AMECO member")
    header = [item.strip() for item in rows[0]]
    matches = [
        row for row in rows[1:]
        if row and row[0].strip() == expected_code
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{expected_code}: expected one row, found {len(matches)}"
        )
    row = [item.strip() for item in matches[0]]
    if row[1] != expected_country:
        raise ValueError(f"{expected_code}: country mismatch {row[1]!r}")
    if expected_concept.casefold() not in row[3].casefold():
        raise ValueError(f"{expected_code}: concept mismatch {row[3]!r}")
    if row[4] != expected_unit:
        raise ValueError(f"{expected_code}: unit mismatch {row[4]!r}")
    raw_line = (";".join(matches[0]) + "\n").encode("utf-8")
    return header, row, raw_line


def annual_values(
    header: list[str],
    row: list[str],
    last_actual_year: int,
) -> dict[int, float]:
    values: dict[int, float] = {}
    for label, raw in zip(header[5:], row[5:]):
        label = label.strip()
        raw = raw.strip()
        if not label.isdigit():
            continue
        year = int(label)
        if year > last_actual_year or raw in {"", "NA"}:
            continue
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite value for {year}: {raw!r}")
        values[year] = value
    return values


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    fetched_at = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    script_path = Path(__file__).resolve()
    script_hash = sha256(script_path.read_bytes())
    last_actual_year = int(
        contract["source_release"]["actual_only_last_year"]
    )

    series: dict[str, dict[int, float]] = {}
    source_records: list[dict[str, object]] = []

    for source in contract["sources"]:
        body, headers, status = fetch(source["url"])
        raw_path = OUT / "raw" / f'{source["id"]}.zip'
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)
        if status != 200:
            raise SystemExit(
                f'{source["id"]}: provider returned HTTP {status}'
            )

        try:
            archive = zipfile.ZipFile(BytesIO(body))
        except zipfile.BadZipFile as exc:
            raise SystemExit(f'{source["id"]}: invalid ZIP: {exc}') from exc

        with archive:
            if source["member"] not in archive.namelist():
                raise SystemExit(
                    f'{source["id"]}: member {source["member"]!r} missing'
                )
            member_bytes = archive.read(source["member"])
            info = archive.getinfo(source["member"])

        header, row, row_bytes = selected_row(
            member_bytes,
            source["code"],
            source["country"],
            source["concept"],
            source["unit"],
        )
        row_path = OUT / "selected_rows" / f'{source["id"]}.txt'
        row_path.parent.mkdir(parents=True, exist_ok=True)
        row_path.write_bytes(row_bytes)

        observations = annual_values(header, row, last_actual_year)
        series[source["id"]] = observations
        source_records.append(
            {
                "id": source["id"],
                "url": source["url"],
                "http_status": status,
                "content_type": headers.get("Content-Type"),
                "last_modified": headers.get("Last-Modified"),
                "zip_path": str(raw_path.relative_to(OUT)),
                "zip_bytes": len(body),
                "zip_sha256": sha256(body),
                "member": source["member"],
                "member_bytes": len(member_bytes),
                "member_sha256": sha256(member_bytes),
                "member_crc32": f"{info.CRC:08x}",
                "selected_code": source["code"],
                "selected_row_path": str(row_path.relative_to(OUT)),
                "selected_row_sha256": sha256(row_bytes),
                "selected_row_bytes": len(row_bytes),
                "first_actual_year": min(observations),
                "last_actual_year": max(observations),
                "actual_observations": len(observations),
            }
        )

    common = sorted(
        set(series["output_gap"])
        & set(series["primary_balance"])
        & set(series["debt"])
    )
    gate = contract["coverage_gate"]
    if (
        not common
        or common[0] != int(gate["first_expected_common_actual_year"])
        or common[-1] != int(gate["last_expected_common_actual_year"])
        or len(common) != int(gate["expected_common_actual_observations"])
    ):
        raise SystemExit(
            "AMECO common actual-only coverage differs from frozen gate: "
            f"{common[0] if common else None}.."
            f"{common[-1] if common else None}, n={len(common)}"
        )

    csv_path = OUT / "fiscal_reaction_annual_actual_source.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=contract["output_schema"],
        )
        writer.writeheader()
        for year in common:
            writer.writerow(
                {
                    "year": year,
                    "primary_balance_pct_gdp": (
                        f'{series["primary_balance"][year]:.12g}'
                    ),
                    "output_gap_pct_potential_gdp": (
                        f'{series["output_gap"][year]:.12g}'
                    ),
                    "debt_pct_gdp": f'{series["debt"][year]:.12g}',
                    "source_status": "ACTUAL_ONLY_COMPLETE",
                }
            )

    csv_body = csv_path.read_bytes()
    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "generated_at_utc": fetched_at,
        "materializer_script": (
            "scripts/audit_ameco_fiscal_reaction_materialisation.py"
        ),
        "materializer_script_sha256": script_hash,
        "status": (
            "SOURCE_MATERIALISATION_EVIDENCE_READY_FOR_REPOSITORY_REVIEW"
        ),
        "estimation_authorized": False,
        "coverage": {
            "rows": len(common),
            "first_year": common[0],
            "last_year": common[-1],
            "forecast_years_present": False,
        },
        "source_records": source_records,
        "output": {
            "path": str(csv_path.relative_to(OUT)),
            "sha256": sha256(csv_body),
            "rows": len(common),
        },
        "hard_rules": contract["hard_rules"],
        "calibration_cycle_open": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
    }
    audit_path = OUT / "fiscal_reaction_ameco_materialisation_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "fiscal-reaction-ameco-actual-vintage-2026-09-19",
        "fetched_at_utc": fetched_at,
        "source_vintage_contract": (
            "data/provenance/source_vintage_contract.json"
        ),
        "materializer_script": (
            "scripts/audit_ameco_fiscal_reaction_materialisation.py"
        ),
        "materializer_script_sha256": script_hash,
        "workflow_context": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "raw_sources": source_records,
        "normalized_outputs": [
            {
                "path": str(csv_path.relative_to(OUT)),
                "sha256": sha256(csv_body),
                "derived_from_raw_sha256": [
                    item["zip_sha256"] for item in source_records
                ],
                "normalizer": (
                    "scripts/audit_ameco_fiscal_reaction_materialisation.py"
                ),
                "normalizer_sha256": script_hash,
                "rows": len(common),
            }
        ],
        "audit_report": {
            "path": str(audit_path.relative_to(OUT)),
            "sha256": sha256(audit_path.read_bytes()),
        },
        "actual_only_last_year": last_actual_year,
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
                "estimation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
