from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("BNR_DSTI_WORKBOOK_PROBE_OUT","bnr_dsti_workbook_probe_artifacts"))
CONTRACT=ROOT/"model"/"calibration_validation"/"bnr_household_dsti_workbook_probe_contract.json"
USER_AGENT="romanian-monetary-dynamics/0.1.0 (+GitHub BNR DSTI workbook probe)"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signature(data: bytes) -> str:
    if data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return "OLE2_CFBF_D0CF11E0A1B11AE1"
    if data.startswith(b"PK\x03\x04"):
        return "ZIP_PK_0304"
    return "OTHER"


def fetch(url: str, timeout: int, attempts: int):
    req=urllib.request.Request(
        url,
        headers={
            "User-Agent":USER_AGENT,
            "Accept":"application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*",
        },
    )
    last=None
    for attempt in range(1,attempts+1):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                return resp.read(),dict(resp.headers.items()),int(resp.status),None
        except urllib.error.HTTPError as exc:
            return exc.read(),dict(exc.headers.items()),int(exc.code),f"HTTPError:{exc.code}"
        except Exception as exc:
            last=f"{type(exc).__name__}:{exc}"
            if attempt<attempts:
                time.sleep(1)
    return b"",{},None,last


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    rules=c["probe_rules"]
    results=[]
    for item in c["candidate_workbooks"]:
        body,headers,status,error=fetch(
            item["url"],
            timeout=int(rules["timeout_seconds"]),
            attempts=int(rules["max_attempts_per_url"]),
        )
        sig=signature(body)
        accessible=status==200 and sig in rules["allowed_binary_signatures"]
        suffix=".xls" if sig=="OLE2_CFBF_D0CF11E0A1B11AE1" else ".xlsx" if sig=="ZIP_PK_0304" else ".response"
        path=OUT/f'{item["id"]}{suffix}'
        if rules["retain_all_response_bytes"] and body:
            path.write_bytes(body)
        results.append({
            "id":item["id"],
            "url":item["url"],
            "http_status":status,
            "error":error,
            "bytes":len(body),
            "sha256":sha256(body) if body else None,
            "signature":sig,
            "spreadsheet_accessible":accessible,
            "retained_path":str(path.relative_to(OUT)) if body else None,
            "content_type":headers.get("Content-Type"),
            "content_disposition":headers.get("Content-Disposition"),
            "last_modified":headers.get("Last-Modified"),
        })
    accessible=[x for x in results if x["spreadsheet_accessible"]]
    audit={
        "audit_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "phase":c["phase"],
        "mechanism_id":c["mechanism_id"],
        "results":results,
        "accessible_workbook_count":len(accessible),
        "candidate_count":len(results),
        "status":"ACCESSIBLE_WORKBOOK_BYTES_READY_FOR_EXPLICIT_REPOSITORY_REVIEW_ONLY" if accessible else "PROVIDER_ACCESS_BLOCKED_OR_NON_SPREADSHEET_RESPONSE",
        "value_extraction_performed":False,
        "chart_digitisation_performed":False,
        "estimation_authorized":False,
        "hard_rules":c["hard_rules"],
    }
    (OUT/"bnr_household_dsti_workbook_probe.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
