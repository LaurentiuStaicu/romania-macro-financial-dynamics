from __future__ import annotations

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
        "FISCAL_REACTION_AMECO_PROBE_OUT",
        "fiscal_reaction_ameco_probe_artifacts",
    )
)
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "fiscal_reaction_ameco_source_probe_contract.json"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub AMECO fiscal-reaction source-structure probe)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_text(data: bytes) -> str | None:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def fetch(url: str) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/zip,*/*"},
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read(), dict(response.headers.items()), int(response.status)
        except urllib.error.HTTPError as exc:
            return exc.read(), dict(exc.headers.items()), int(exc.code)
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                raise RuntimeError(
                    f"network failure after {attempt} attempts: {url}: {exc}"
                ) from exc
    raise RuntimeError(f"unreachable fetch state: {last_error}")


def safe_member_path(source_id: str, member: str) -> Path:
    name = Path(member).name
    return OUT / "matching_members" / source_id / name


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    script_sha = sha256(Path(__file__).resolve().read_bytes())
    fetched_at = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    source_reports: list[dict[str, object]] = []
    for source in contract["chapter_sources"]:
        source_id = source["id"]
        required = source["required_variable"]
        body, headers, status = fetch(source["url"])

        raw_path = OUT / "raw" / f"{source_id}.zip"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)

        report: dict[str, object] = {
            "id": source_id,
            "url": source["url"],
            "required_variable": required,
            "http_status": status,
            "content_type": headers.get("Content-Type"),
            "last_modified": headers.get("Last-Modified"),
            "zip_path": str(raw_path.relative_to(OUT)),
            "zip_bytes": len(body),
            "zip_sha256": sha256(body),
            "member_inventory": [],
            "variable_matching_members": [],
            "romania_matching_members": [],
            "variable_line_excerpts": [],
            "romania_line_excerpts": [],
        }
        if status != 200:
            report["status"] = "HTTP_ERROR"
            source_reports.append(report)
            continue

        try:
            archive = zipfile.ZipFile(BytesIO(body))
        except zipfile.BadZipFile as exc:
            report["status"] = "BAD_ZIP"
            report["error"] = str(exc)
            source_reports.append(report)
            continue

        variable_members: set[str] = set()
        romania_members: set[str] = set()
        with archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                report["member_inventory"].append(
                    {
                        "name": info.filename,
                        "bytes": info.file_size,
                        "compressed_bytes": info.compress_size,
                        "crc32": f"{info.CRC:08x}",
                    }
                )
                data = archive.read(info)
                text = decode_text(data)
                name_has_variable = required.casefold() in info.filename.casefold()
                content_has_variable = (
                    text is not None and required.casefold() in text.casefold()
                )
                content_has_romania = (
                    text is not None and "romania" in text.casefold()
                )

                if name_has_variable or content_has_variable:
                    variable_members.add(info.filename)
                    out_path = safe_member_path(source_id, info.filename)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    if not out_path.exists():
                        out_path.write_bytes(data)
                    if text is not None:
                        for line in text.splitlines():
                            if required.casefold() in line.casefold():
                                report["variable_line_excerpts"].append(line[:2000])
                                if len(report["variable_line_excerpts"]) >= 20:
                                    break

                if content_has_romania:
                    romania_members.add(info.filename)
                    if text is not None:
                        for line in text.splitlines():
                            if "romania" in line.casefold():
                                report["romania_line_excerpts"].append(line[:2000])
                                if len(report["romania_line_excerpts"]) >= 20:
                                    break

        report["variable_matching_members"] = sorted(variable_members)
        report["romania_matching_members"] = sorted(romania_members)
        report["status"] = (
            "STRUCTURE_FOUND"
            if variable_members and romania_members
            else "STRUCTURE_INCOMPLETE"
        )
        source_reports.append(report)

    overall = all(item["status"] == "STRUCTURE_FOUND" for item in source_reports)
    audit = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "generated_at_utc": fetched_at,
        "probe_script": "scripts/audit_ameco_fiscal_reaction_source_structure.py",
        "probe_script_sha256": script_sha,
        "estimation_authorized": False,
        "source_reports": source_reports,
        "overall_status": (
            "AMECO_SOURCE_STRUCTURE_FOUND"
            if overall
            else "AMECO_SOURCE_STRUCTURE_INCOMPLETE"
        ),
        "next_gate": contract["next_gate"],
        "hard_rules": contract["hard_rules"],
    }
    path = OUT / "ameco_fiscal_reaction_source_structure_audit.json"
    path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "overall_status": audit["overall_status"],
                "sources": [
                    {
                        "id": item["id"],
                        "status": item["status"],
                        "variable_matching_members": item[
                            "variable_matching_members"
                        ],
                        "romania_matching_members_count": len(
                            item["romania_matching_members"]
                        ),
                        "zip_sha256": item["zip_sha256"],
                    }
                    for item in source_reports
                ],
                "estimation_authorized": False,
            },
            indent=2,
        )
    )
    if not overall:
        raise SystemExit("AMECO source structure probe incomplete")


if __name__ == "__main__":
    main()
