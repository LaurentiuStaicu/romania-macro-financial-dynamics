from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "model"
    / "calibration_validation"
    / "bnr_bls_missing_round_workbook_recovery_contract.json"
)
OUT = Path(
    os.environ.get(
        "BNR_BLS_MISSING_ROUND_RECOVERY_OUT",
        "bnr_bls_missing_round_recovery_artifacts",
    )
)
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub BLS missing-round recovery)"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signature(data: bytes) -> str:
    if data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return "OLE2_CFBF_D0CF11E0A1B11AE1"
    if data.startswith(b"PK\x03\x04"):
        return "ZIP_PK_0304"
    return "OTHER"


def fetch(url: str, timeout: int, attempts: int):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/vnd.ms-excel,"
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
                "application/octet-stream,*/*"
            ),
        },
    )
    last_error = None
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


def retained_suffix(sig: str) -> str:
    if sig == "OLE2_CFBF_D0CF11E0A1B11AE1":
        return ".xls"
    if sig == "ZIP_PK_0304":
        return ".xlsx"
    return ".response"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rules = contract["probe_rules"]
    results = []

    for round_spec in contract["rounds"]:
        quarter = round_spec["quarter"]
        candidates = round_spec["url_candidates"]
        if not candidates:
            results.append(
                {
                    "quarter": quarter,
                    "status": "NO_EXACT_URL_PREREGISTERED",
                    "discovery_status": round_spec["discovery_status"],
                    "requests_performed": 0,
                    "candidates": [],
                }
            )
            continue

        candidate_results = []
        for index, url in enumerate(candidates, start=1):
            body, headers, status, error = fetch(
                url,
                timeout=int(rules["timeout_seconds"]),
                attempts=int(rules["max_attempts_per_url"]),
            )
            sig = signature(body)
            accessible = (
                status == 200
                and sig in rules["allowed_binary_signatures"]
            )
            retained_path = None
            if rules["retain_all_response_bytes"] and body:
                retained = OUT / (
                    f"{quarter.lower()}-candidate-{index}"
                    f"{retained_suffix(sig)}"
                )
                retained.write_bytes(body)
                retained_path = str(retained.relative_to(OUT))

            candidate_results.append(
                {
                    "url": url,
                    "http_status": status,
                    "error": error,
                    "bytes": len(body),
                    "sha256": sha256(body) if body else None,
                    "signature": sig,
                    "spreadsheet_accessible": accessible,
                    "retained_path": retained_path,
                    "content_type": headers.get("Content-Type"),
                    "content_disposition": headers.get("Content-Disposition"),
                    "last_modified": headers.get("Last-Modified"),
                }
            )

        accessible_count = sum(
            1 for item in candidate_results
            if item["spreadsheet_accessible"]
        )
        results.append(
            {
                "quarter": quarter,
                "status": (
                    "SPREADSHEET_BYTES_RECOVERED"
                    if accessible_count
                    else "NO_VALID_SPREADSHEET_BYTES_RECOVERED"
                ),
                "discovery_status": round_spec["discovery_status"],
                "requests_performed": len(candidate_results),
                "accessible_candidate_count": accessible_count,
                "candidates": candidate_results,
            }
        )

    recovered_quarters = [
        item["quarter"]
        for item in results
        if item["status"] == "SPREADSHEET_BYTES_RECOVERED"
    ]
    audit = {
        "audit_version": "0.1",
        "generated_at_utc": datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "phase": contract["phase"],
        "mechanism_id": contract["mechanism_id"],
        "target_missing_quarters": contract["target_missing_quarters"],
        "results": results,
        "recovered_quarters": recovered_quarters,
        "recovered_quarter_count": len(recovered_quarters),
        "canonical_panel_modified": False,
        "value_extraction_performed": False,
        "parameter_estimation_performed": False,
        "model_selection_performed": False,
        "system_dynamics_activation": False,
        "behavioural_closure_change": False,
        "promotion_boundary": contract["promotion_boundary"],
        "hard_rules": contract["hard_rules"],
        "status": (
            "RECOVERED_WORKBOOK_BYTES_READY_FOR_EXPLICIT_PROMOTION_REVIEW_ONLY"
            if recovered_quarters
            else "NEGATIVE_SOURCE_ACCESS_EVIDENCE_ONLY"
        ),
    }
    (
        OUT / "bnr_bls_missing_round_workbook_recovery.json"
    ).write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
