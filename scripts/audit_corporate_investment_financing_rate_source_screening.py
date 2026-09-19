from __future__ import annotations

import csv
import io
import json
import math
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("CORPORATE_INVESTMENT_RATE_SCREENING_OUT","corporate_investment_rate_screening_artifacts"))
CONTRACT = ROOT / "model" / "calibration_validation" / "corporate_investment_financing_rate_source_screening_contract.json"
ECB_API = "https://data-api.ecb.europa.eu/service/data"


def month_index(period: str) -> int:
    y,m=map(int,period.split("-"))
    if not 1 <= m <= 12:
        raise ValueError(period)
    return y*12+m-1


def quarter(period: str) -> str:
    y,m=map(int,period.split("-"))
    return f"{y:04d}-Q{(m-1)//3+1}"


def fetch(flow: str,key: str) -> tuple[bytes,dict[str,str],int]:
    prefix=f"{flow}."
    if not key.startswith(prefix):
        raise ValueError(key)
    url=f"{ECB_API}/{flow}/{key[len(prefix):]}?"+urllib.parse.urlencode({"format":"csvdata"})
    req=urllib.request.Request(url,headers={"User-Agent":"romanian-monetary-dynamics/0.1.0","Accept":"text/csv,*/*"})
    with urllib.request.urlopen(req,timeout=90) as resp:
        return resp.read(),dict(resp.headers.items()),int(resp.status)


def finite_periods(body: bytes, expected_key: str) -> list[str]:
    r=csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    periods=[]
    seen=set()
    for row in r:
        key=(row.get("KEY") or "").strip()
        if key and key != expected_key:
            raise ValueError(f"KEY mismatch: {key}")
        p=(row.get("TIME_PERIOD") or "").strip()
        raw=row.get("OBS_VALUE")
        if not p or raw in (None,""):
            continue
        v=float(raw)
        if not math.isfinite(v):
            raise ValueError(f"nonfinite {p}")
        if p in seen:
            raise ValueError(f"duplicate {p}")
        seen.add(p); periods.append(p)
    return sorted(periods,key=month_index)


def metrics(periods: list[str]) -> dict[str,object]:
    if not periods:
        raise ValueError("no finite observations")
    first,last=periods[0],periods[-1]
    expected_months=month_index(last)-month_index(first)+1
    idx={month_index(p) for p in periods}
    longest=0; run=0
    for i in range(month_index(first),month_index(last)+1):
        if i in idx:
            run+=1; longest=max(longest,run)
        else:
            run=0
    grouped=defaultdict(set)
    for p in periods:
        y,m=map(int,p.split("-")); grouped[quarter(p)].add(m)
    complete=[]
    for q,months in grouped.items():
        qn=int(q[-1]); exp=set(range((qn-1)*3+1,(qn-1)*3+4))
        if months==exp: complete.append(q)
    # denominator: all calendar quarters touched between first and last,
    # counting a quarter only if all three months lie inside the bounded span.
    first_full_idx=(month_index(first)+2)//3
    last_full_idx=(month_index(last)-2)//3
    expected_quarters=max(0,last_full_idx-first_full_idx+1)
    return {
      "finite_observations":len(periods),
      "first_period":first,
      "last_period":last,
      "expected_months_between_bounds":expected_months,
      "finite_month_coverage_fraction":len(periods)/expected_months,
      "complete_three_month_quarters":len(complete),
      "expected_quarters_between_first_complete_candidate_and_last_bound":expected_quarters,
      "complete_quarter_coverage_fraction":(len(complete)/expected_quarters if expected_quarters else 0.0),
      "longest_consecutive_month_run":longest,
      "complete_quarters":sorted(complete),
    }


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    results={}
    for candidate in c["candidates"]:
        body,headers,status=fetch(candidate["flow"],candidate["series_key"])
        raw=OUT/f'{candidate["id"]}.csv'
        raw.write_bytes(body)
        if status != 200:
            raise RuntimeError(f"{candidate['id']} HTTP {status}")
        p=finite_periods(body,candidate["series_key"])
        results[candidate["id"]]={
          "series_key":candidate["series_key"],
          "semantic_scope":candidate["semantic_scope"],
          "last_modified":headers.get("Last-Modified"),
          "metrics":metrics(p),
        }
    a=results["total_fixation"]["metrics"]["complete_quarter_coverage_fraction"]
    b=results["up_to_one_year_fixation"]["metrics"]["complete_quarter_coverage_fraction"]
    rule=c["eligibility_rule"]
    eligible=(b >= rule["alternative_min_complete_quarter_coverage_fraction"] and b-a >= rule["alternative_min_advantage_over_total_fixation"])
    audit={
      "audit_version":"0.1",
      "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
      "mechanism_id":c["mechanism_id"],
      "phase":c["phase"],
      "results":results,
      "alternative_measurement_eligibility":eligible,
      "automatic_replacement":False,
      "estimation_authorized":False,
      "hard_rules":c["hard_rules"],
    }
    (OUT/"corporate_investment_financing_rate_source_screening.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2))


if __name__=="__main__":
    main()
