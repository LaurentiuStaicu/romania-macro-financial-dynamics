from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC,datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("BNR_BLS_XLSX_PROBE_OUT","bnr_bls_xlsx_probe_artifacts"))
CONTRACT=ROOT/"model"/"calibration_validation"/"bnr_bls_may2025_xlsx_probe_contract.json"
UA="romanian-monetary-dynamics/0.1.0 (+GitHub BNR BLS XLSX identity probe)"


def sha256(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()


def fetch(url:str):
    req=urllib.request.Request(url,headers={
        "User-Agent":UA,
        "Accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/zip,application/octet-stream,*/*"
    })
    try:
        with urllib.request.urlopen(req,timeout=60) as resp:
            return resp.read(),dict(resp.headers.items()),int(resp.status),None
    except urllib.error.HTTPError as exc:
        return exc.read(),dict(exc.headers.items()),int(exc.code),f"HTTPError:{exc.code}"
    except Exception as exc:
        return b"",{},None,f"{type(exc).__name__}:{exc}"


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    results=[]
    for item in c["candidates"]:
        body,headers,status,error=fetch(item["url"])
        path=OUT/f'{item["id"]}.xlsx'
        if body:
            path.write_bytes(body)
        sig="ZIP_PK_0304" if body.startswith(b"PK\x03\x04") else "OTHER"
        results.append({
            "id":item["id"],
            "url":item["url"],
            "http_status":status,
            "error":error,
            "bytes":len(body),
            "sha256":sha256(body) if body else None,
            "signature":sig,
            "xlsx_accessible":status==200 and sig=="ZIP_PK_0304",
            "retained_path":str(path.relative_to(OUT)) if body else None,
            "content_type":headers.get("Content-Type"),
            "content_disposition":headers.get("Content-Disposition"),
            "last_modified":headers.get("Last-Modified"),
        })
    accessible=[x for x in results if x["xlsx_accessible"]]
    aliases=(len(accessible)==2 and accessible[0]["sha256"]==accessible[1]["sha256"])
    report={
        "audit_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "phase":c["phase"],
        "mechanism_id":c["mechanism_id"],
        "results":results,
        "accessible_xlsx_count":len(accessible),
        "candidate_count":len(results),
        "byte_identical_aliases":aliases,
        "workbook_parsing_performed":False,
        "value_extraction_performed":False,
        "estimation_authorized":False,
        "hard_rules":c["hard_rules"],
        "status":"PASS_XLSX_BYTES_READY_FOR_REVIEW" if accessible else "NO_ACCESSIBLE_XLSX"
    }
    (OUT/"bnr_bls_may2025_xlsx_probe.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
