from __future__ import annotations

import csv, hashlib, io, json, math, os, time
import urllib.error, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("SECTORAL_POSITIONS_PHASE_C_AUDIT_OUT","sectoral_positions_phase_c_audit_artifacts"))
OUT.mkdir(parents=True,exist_ok=True)
API="https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT="romanian-monetary-dynamics/0.1.0 (+GitHub sectoral-financial-positions Phase C diagnostic)"
BREAK_PERIODS=("2021-Q2","2021-Q3","2021-Q4")

def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def load_contract()->dict:
    return json.loads((ROOT/"model/dynamics/sectoral_financial_positions_phase_c_diagnostic_contract.json").read_text(encoding="utf-8"))

def key(area,ref,cp,entry,measure,instrument):
    return ".".join(("Q","N","RO",area,ref,cp,"N",entry,measure,instrument,"_Z","_Z","XDC","_T","S","V","N","_T"))

def fetch(k:str,contract:dict)->dict:
    q=urllib.parse.urlencode({"startPeriod":contract["source"]["requested_start"],"endPeriod":contract["source"]["requested_end"],"format":"csvdata"})
    url=f"{API}{k}?{q}"
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/csv,application/vnd.sdmx.data+csv;version=1.0.0"})
    body=b""; status=0; headers={}; last=None
    for attempt in range(1,4):
        try:
            with urllib.request.urlopen(req,timeout=45) as response:
                body=response.read(); status=int(response.status); headers=dict(response.headers.items())
            break
        except urllib.error.HTTPError as exc:
            body=exc.read(); status=int(exc.code); headers=dict(exc.headers.items())
            if status in {429,500,502,503,504} and attempt<3:
                time.sleep(attempt*2); continue
            break
        except (urllib.error.URLError,TimeoutError) as exc:
            last=exc
            if attempt<3:
                time.sleep(attempt*2); continue
            return {"key":k,"url":url,"status":"NETWORK_ERROR","error":str(last),"observations":{}}
    raw=OUT/"raw"/f"{sha256(k.encode())[:20]}.csv"; raw.parent.mkdir(parents=True,exist_ok=True); raw.write_bytes(body)
    result={"key":k,"url":url,"http_status":status,"content_type":headers.get("Content-Type"),"raw_path":str(raw.relative_to(OUT)),"raw_sha256":sha256(body),"raw_bytes":len(body),"observations":{}}
    if status!=200:
        result["status"]="HTTP_ERROR"; result["response_preview"]=body[:300].decode("utf-8",errors="replace"); return result
    try:
        rows=list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    except Exception as exc:
        result["status"]="PARSE_ERROR"; result["error"]=str(exc); return result
    obs={}; dup=[]; nonfinite=[]
    for row in rows:
        p=str(row.get("TIME_PERIOD","")).strip(); rv=str(row.get("OBS_VALUE","")).strip()
        if not p or rv in {"","NaN","nan"}: continue
        try: v=float(rv)
        except ValueError:
            result["status"]="NON_NUMERIC_OBSERVATION"; return result
        if not math.isfinite(v): nonfinite.append(p); continue
        if p in obs: dup.append(p); continue
        obs[p]=v
    result.update({"status":"AVAILABLE" if obs and not dup and not nonfinite else "SERIES_INCOMPLETE","observation_count":len(obs),"first_observation":min(obs) if obs else None,"last_observation":max(obs) if obs else None,"duplicate_periods":dup,"non_finite_periods":nonfinite,"observations":obs})
    return result

def decomp(series,keys):
    f1=series[keys["F1"]]; f11=series[keys["F11"]]; f12=series[keys["F12"]]
    if any(x.get("status")!="AVAILABLE" for x in (f1,f11,f12)):
        return {"status":"SOURCE_INCOMPLETE","common_observation_count":0,"max_abs_residual_million_RON":None,"break_periods":{}}
    a={str(k):float(v) for k,v in f1["observations"].items()}
    b={str(k):float(v) for k,v in f11["observations"].items()}
    c={str(k):float(v) for k,v in f12["observations"].items()}
    common=sorted(set(a)&set(b)&set(c))
    residual={p:a[p]-b[p]-c[p] for p in common}
    return {
        "status":"PASS_WITHIN_0.1_MILLION_RON" if residual and max(abs(v) for v in residual.values())<=0.1 else "FAIL",
        "common_observation_count":len(common),
        "first_common_period":common[0] if common else None,
        "last_common_period":common[-1] if common else None,
        "max_abs_residual_million_RON":max((abs(v) for v in residual.values()),default=None),
        "break_periods":{p:{"F1":a.get(p),"F11":b.get(p),"F12":c.get(p),"residual":residual.get(p)} for p in BREAK_PERIODS},
    }

def main():
    contract=load_contract()
    required=set(); addresses={}
    for code in contract["source"]["resident_source_sectors"]:
        for measure in contract["source"]["measures"]:
            for entry in contract["source"]["entries"]:
                m={}
                for instrument in contract["source"]["instruments"]:
                    k=key("W0",code,"S1",entry,measure,instrument); m[instrument]=k; required.add(k)
                addresses[f"W0:{code}:{entry}:{measure}"]=m
    for measure in contract["source"]["measures"]:
        for entry in contract["source"]["entries"]:
            m={}
            for instrument in contract["source"]["instruments"]:
                k=key("W1","S1","S1",entry,measure,instrument); m[instrument]=k; required.add(k)
            addresses[f"W1:S1:{entry}:{measure}"]=m

    series={}
    with ThreadPoolExecutor(max_workers=10) as ex:
        fut={ex.submit(fetch,k,contract):k for k in sorted(required)}
        for i,f in enumerate(as_completed(fut),1):
            k=fut[f]; series[k]=f.result(); print(f"[{i}/{len(fut)}] {series[k].get('status')} {k}",flush=True)

    decompositions={addr:decomp(series,keys) for addr,keys in addresses.items()}
    availability={addr:{instr:series[k].get("status") for instr,k in keys.items()} for addr,keys in addresses.items()}

    resident_liability_f1={}
    for code in contract["source"]["resident_source_sectors"]:
        resident_liability_f1[code]={}
        for measure in contract["source"]["measures"]:
            k=addresses[f"W0:{code}:L:{measure}"]["F1"]
            item=series[k]
            resident_liability_f1[code][measure]={
                "status":item.get("status"),
                "break_periods":{p:item.get("observations",{}).get(p) for p in BREAK_PERIODS},
                "latest_period":item.get("last_observation"),
                "latest_value":item.get("observations",{}).get(item.get("last_observation")) if item.get("last_observation") else None,
            }

    comparisons={}
    for measure in contract["source"]["measures"]:
        for instrument in contract["source"]["instruments"]:
            s121=series[addresses[f"W0:S121:A:{measure}"][instrument]]
            wa=series[addresses[f"W1:S1:A:{measure}"][instrument]]
            wl=series[addresses[f"W1:S1:L:{measure}"][instrument]]
            def vals(item):
                return {str(k):float(v) for k,v in item.get("observations",{}).items()} if item.get("status")=="AVAILABLE" else {}
            a,b,c=vals(s121),vals(wa),vals(wl)
            common_a=sorted(set(a)&set(b)); common_l=sorted(set(a)&set(c))
            diff_a={p:a[p]-b[p] for p in common_a}; diff_l={p:a[p]-c[p] for p in common_l}
            comparisons[f"{measure}:{instrument}"]={
                "S121_minus_W1_A_max_abs_million_RON":max((abs(v) for v in diff_a.values()),default=None),
                "S121_minus_W1_L_max_abs_million_RON":max((abs(v) for v in diff_l.values()),default=None),
                "break_periods":{
                    p:{"S121_A":a.get(p),"W1_A":b.get(p),"W1_L":c.get(p)}
                    for p in BREAK_PERIODS
                }
            }

    report={
        "audit_version":"0.1",
        "phase":"Sectoral Financial Positions — Phase C F1/QSA semantics diagnostic",
        "contract":"model/dynamics/sectoral_financial_positions_phase_c_diagnostic_contract.json",
        "series_requested":len(required),
        "series_status_counts":dict(Counter(str(x.get("status")) for x in series.values())),
        "network_errors_present":any(x.get("status")=="NETWORK_ERROR" for x in series.values()),
        "availability_by_address":availability,
        "F1_equals_F11_plus_F12":decompositions,
        "resident_F1_liabilities":resident_liability_f1,
        "S121_vs_W1_comparisons":comparisons,
        "source_results":series,
        "reference_mode_status_changed":False,
        "readiness_count_changed":False,
        "accounting_readiness_changed":False,
        "behavioural_closure_changed":False,
        "diagnostic_only":True,
    }
    (OUT/"sectoral_financial_positions_phase_c_diagnostic.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "series_requested":report["series_requested"],
        "series_status_counts":report["series_status_counts"],
        "network_errors_present":report["network_errors_present"],
        "resident_F1_liabilities":resident_liability_f1,
        "S121_vs_W1_comparisons":comparisons,
        "diagnostic_only":True,
    },indent=2))
    if report["network_errors_present"]:
        raise SystemExit("Network errors make the Phase C diagnostic inconclusive; see retained artifact.")

if __name__=="__main__":
    main()
