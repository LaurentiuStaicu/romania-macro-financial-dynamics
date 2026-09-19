from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "FISCAL_REACTION_CAPB_VINTAGE_OUT",
        "fiscal_reaction_capb_vintage_artifacts",
    )
)
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fiscal_reaction_capb_realtime_vintage_contract.json"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub AMECO fiscal CAPB real-time vintage materialisation)"
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


def decode_line(data: bytes) -> str | None:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def iter_zip_members_recursive(
    archive_bytes: bytes,
    *,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = 3,
):
    if depth > max_depth:
        raise ValueError("nested ZIP depth exceeds frozen maximum")
    try:
        archive = zipfile.ZipFile(BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("provider payload is not a valid ZIP archive") from exc

    with archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            body = archive.read(info)
            path = f"{prefix}{info.filename}"
            looks_like_zip = (
                info.filename.casefold().endswith(".zip")
                or body.startswith(b"PK\x03\x04")
            )
            if looks_like_zip:
                if depth >= max_depth:
                    raise ValueError(
                        f"{path}: nested ZIP exceeds frozen maximum depth"
                    )
                yield from iter_zip_members_recursive(
                    body,
                    prefix=f"{path}::",
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            else:
                yield path, body


def extract_distinct_target_row(
    archive_bytes: bytes,
    target_code: str,
    *,
    max_depth: int = 3,
) -> dict[str, object]:
    matches: list[dict[str, object]] = []
    for member_path, body in iter_zip_members_recursive(
        archive_bytes,
        max_depth=max_depth,
    ):
        for raw_line in body.splitlines(keepends=True):
            text = decode_line(raw_line)
            if text is None:
                continue
            stripped = text.rstrip("\r\n")
            try:
                fields = next(csv.reader([stripped], delimiter=";"))
            except (csv.Error, StopIteration):
                continue
            if not fields:
                continue
            code = fields[0].lstrip("\ufeff").strip()
            if code != target_code:
                continue
            matches.append(
                {
                    "member_path": member_path,
                    "row_bytes": raw_line,
                    "row_sha256": sha256(raw_line),
                }
            )

    if not matches:
        raise ValueError(f"{target_code}: no exact row found in release archive")

    distinct = {str(item["row_sha256"]) for item in matches}
    if len(distinct) != 1:
        locations = sorted(str(item["member_path"]) for item in matches)
        raise ValueError(
            f"{target_code}: multiple distinct matched rows found: {locations}"
        )

    matches.sort(key=lambda item: str(item["member_path"]))
    selected = matches[0]
    return {
        "selected_member_path": selected["member_path"],
        "matching_member_paths": [
            str(item["member_path"]) for item in matches
        ],
        "matching_member_count": len(matches),
        "row_bytes": selected["row_bytes"],
        "row_sha256": selected["row_sha256"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    target_code = contract["target_series"]["code"]
    max_depth = int(
        contract["extraction_rules"]["maximum_nested_zip_depth"]
    )
    script_path = Path(__file__).resolve()
    script_hash = sha256(script_path.read_bytes())
    fetched_at = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    inventory: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []

    for release in contract["releases"]:
        release_id = release["id"]
        body, headers, status = fetch(release["source_url"])
        raw_path = OUT / "raw" / f"{release_id}.zip"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)

        if status != 200:
            raise SystemExit(
                f"{release_id}: provider returned HTTP {status}"
            )

        matched = extract_distinct_target_row(
            body,
            target_code,
            max_depth=max_depth,
        )
        row_bytes = matched["row_bytes"]
        assert isinstance(row_bytes, bytes)

        row_path = OUT / "selected_rows" / f"{release_id}.txt"
        row_path.parent.mkdir(parents=True, exist_ok=True)
        row_path.write_bytes(row_bytes)

        record = {
            "release_id": release_id,
            "release_label": release["label"],
            "release_date": release["release_date"],
            "source_url": release["source_url"],
            "archive_sha256": sha256(body),
            "archive_bytes": len(body),
            "selected_member_path": matched["selected_member_path"],
            "matching_member_count": matched["matching_member_count"],
            "target_code": target_code,
            "matched_row_sha256": matched["row_sha256"],
            "matched_row_bytes": len(row_bytes),
            "status": "EXACT_TARGET_ROW_RETAINED",
        }
        inventory.append(record)
        evidence.append(
            {
                **record,
                "http_status": status,
                "content_type": headers.get("Content-Type"),
                "last_modified": headers.get("Last-Modified"),
                "raw_path": str(raw_path.relative_to(OUT)),
                "selected_row_path": str(row_path.relative_to(OUT)),
                "matching_member_paths": matched["matching_member_paths"],
            }
        )

    inventory_path = OUT / "fiscal_capb_release_inventory.csv"
    with inventory_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=contract["output_schema"],
        )
        writer.writeheader()
        writer.writerows(inventory)

    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "generated_at_utc": fetched_at,
        "materializer_script": (
            "scripts/materialise_fiscal_reaction_capb_realtime_vintages.py"
        ),
        "materializer_script_sha256": script_hash,
        "status": "CAPB_VINTAGE_SOURCE_EVIDENCE_READY_FOR_REPOSITORY_REVIEW",
        "target_code": target_code,
        "release_count": len(inventory),
        "releases": evidence,
        "inventory": {
            "path": str(inventory_path.relative_to(OUT)),
            "sha256": sha256(inventory_path.read_bytes()),
            "rows": len(inventory),
        },
        "estimation_authorized": False,
        "model_selection_authorized": False,
        "prior_final_evaluation_opening_authorized": False,
        "hard_rules": contract["hard_rules"],
        "next_gate": contract["next_gate"],
    }
    audit_path = OUT / "fiscal_capb_vintage_materialisation_audit.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "fiscal-reaction-capb-realtime-vintages-2026-09-19",
        "fetched_at_utc": fetched_at,
        "materializer_script": (
            "scripts/materialise_fiscal_reaction_capb_realtime_vintages.py"
        ),
        "materializer_script_sha256": script_hash,
        "workflow_context": {
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_event_name": os.environ.get("GITHUB_EVENT_NAME"),
        },
        "target_series": contract["target_series"],
        "raw_and_selected_evidence": evidence,
        "normalized_outputs": [
            {
                "path": str(inventory_path.relative_to(OUT)),
                "sha256": sha256(inventory_path.read_bytes()),
                "rows": len(inventory),
                "role": "release-by-release source inventory only",
            }
        ],
        "audit_report": {
            "path": str(audit_path.relative_to(OUT)),
            "sha256": sha256(audit_path.read_bytes()),
        },
        "hard_boundaries": contract["hard_rules"],
        "canonical_promotion": "REQUIRES_EXPLICIT_REPOSITORY_REVIEW_AND_COMMIT",
    }
    (OUT / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": audit["status"],
                "target_code": target_code,
                "release_count": len(inventory),
                "inventory_sha256": audit["inventory"]["sha256"],
                "estimation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
