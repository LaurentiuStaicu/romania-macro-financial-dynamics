from __future__ import annotations

import csv, hashlib, io, json, math, os, time
import urllib.error, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SECTORAL_POSITIONS_ESA_F1_REAUDIT_OUT","sectoral_positions_esa_f1_reaudit_artifacts"))
OUT.mkdir(parents=True, exist_ok=True)
API = "https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT = "romanian-monetary-dynamics/0.1.0 (+GitHub exploratory ESA F1 applicability re-audit)"
TOL = 0.1
REQUIRED_2025 = ("2025-Q1","2025-Q2","2025-Q3","2025-Q4")
SECTORS = ("H","C","F","G","X","BNR")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_contract() -> dict:
    return json.loads((ROOT/"model/dynamics/sectoral_financial_positions_esa_f1_applicability_reaudit_contract_executed_2026-09-19.json").read_text(encoding="utf-8"))

def key(area: str, ref_sector: str, cp_sector: str, entry: str, measure: str, instrument: str) -> str:
    return ".".join(("Q","N","RO",area,ref_sector,cp_sector,"N",entry,measure,instrument,"_Z","_Z","XDC","_T","S","V","N","_T"))

def fetch(series_key: str, contract: dict) -> dict[str, object]:
    query = urllib.parse.urlencode({"startPeriod":contract["source"]["requested_start"],"endPeriod":contract["source"]["requested_end"],"format":"csvdata"})
    url=f"{API}{series_key}?{query}"
    request=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/csv,application/vnd.sdmx.data+csv;version=1.0.0"})
    body=b""; status=0; headers={}; last=None
    for attempt in range(1,4):
        try:
            with urllib.request.urlopen(request,timeout=45) as response:
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
            return {"key":series_key,"url":url,"status":"NETWORK_ERROR","error":str(last),"observations":{}}
    raw=OUT/"raw"/f"{sha256(series_key.encode())[:20]}.csv"; raw.parent.mkdir(parents=True,exist_ok=True); raw.write_bytes(body)
    result={"key":series_key,"url":url,"http_status":status,"content_type":headers.get("Content-Type"),"raw_path":str(raw.relative_to(OUT)),"raw_sha256":sha256(body),"raw_bytes":len(body),"observations":{}}
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

def obs(series_by_key: dict[str,dict[str,object]], k: str) -> dict[str,float] | None:
    item=series_by_key[k]
    if item.get("status")!="AVAILABLE": return None
    return {str(p):float(v) for p,v in item["observations"].items()}

def combine(terms: list[tuple[float,dict[str,float]]]) -> dict[str,float]:
    if not terms: return {}
    common=set(terms[0][1])
    for _,m in terms[1:]: common &= set(m)
    return {p:sum(c*m[p] for c,m in terms) for p in sorted(common)}

def subtract(a: dict[str,float], b: dict[str,float]) -> dict[str,float]:
    return combine([(1.0,a),(-1.0,b)])

def net(a: dict[str,float], l: dict[str,float]) -> dict[str,float]:
    return subtract(a,l)

def main() -> None:
    contract=load_contract()
    required=set()
    total={}
    for code in ("S1M","S11","S12","S121","S13"):
        for measure in ("LE","F"):
            for entry in ("A","L"):
                k=key("W0",code,"S1",entry,measure,"F"); total[(code,measure,entry)]=k; required.add(k)
    f1a={}
    for code in ("S12","S121","S13"):
        for measure in ("LE","F"):
            k=key("W0",code,"S1","A",measure,"F1"); f1a[(code,measure)]=k; required.add(k)
    ext={}
    for measure in ("LE","F"):
        for entry in ("A","L"):
            for instrument in ("F","F1"):
                k=key("W1","S1","S1",entry,measure,instrument); ext[(measure,entry,instrument)]=k; required.add(k)

    series={}
    with ThreadPoolExecutor(max_workers=8) as ex:
        fut={ex.submit(fetch,k,contract):k for k in sorted(required)}
        for i,f in enumerate(as_completed(fut),1):
            k=fut[f]; series[k]=f.result()
            print(f"[{i}/{len(fut)}] {series[k].get('status')} {k}",flush=True)

    unavailable=sorted(k for k in required if series[k].get("status")!="AVAILABLE")
    network=any(x.get("status")=="NETWORK_ERROR" for x in series.values())
    sectors={"stock":{},"flow":{}}
    errors=[]
    for label,measure in (("stock","LE"),("flow","F")):
        def gt(code,entry): return obs(series,total[(code,measure,entry)])
        def gf1(code): return obs(series,f1a[(code,measure)])

        for sector,code in (("H","S1M"),("C","S11")):
            a=gt(code,"A"); l=gt(code,"L")
            if a is None or l is None:
                errors.append(f"{label}:{sector}:source_missing"); sectors[label][sector]={"assets":{},"liabilities":{},"net":{}}
            else:
                sectors[label][sector]={"assets":a,"liabilities":l,"net":net(a,l)}

        bta=gt("S121","A"); bl=gt("S121","L"); bf1=gf1("S121")
        if bta is None or bl is None or bf1 is None:
            errors.append(f"{label}:BNR:source_missing"); sectors[label]["BNR"]={"assets":{},"liabilities":{},"net":{}}
        else:
            ba=subtract(bta,bf1); sectors[label]["BNR"]={"assets":ba,"liabilities":bl,"net":net(ba,bl)}

        gta=gt("S13","A"); gl=gt("S13","L"); gf=gf1("S13")
        if gta is None or gl is None or gf is None:
            errors.append(f"{label}:G:source_missing"); sectors[label]["G"]={"assets":{},"liabilities":{},"net":{}}
        else:
            ga=subtract(gta,gf); sectors[label]["G"]={"assets":ga,"liabilities":gl,"net":net(ga,gl)}

        s12a=gt("S12","A"); s12l=gt("S12","L"); s12f1=gf1("S12")
        s121a=gt("S121","A"); s121l=gt("S121","L"); s121f1=gf1("S121")
        if any(v is None for v in (s12a,s12l,s12f1,s121a,s121l,s121f1)):
            errors.append(f"{label}:F:source_missing"); sectors[label]["F"]={"assets":{},"liabilities":{},"net":{}}
        else:
            fa=subtract(subtract(s12a,s12f1),subtract(s121a,s121f1)); fl=subtract(s12l,s121l)
            sectors[label]["F"]={"assets":fa,"liabilities":fl,"net":net(fa,fl)}

        wa=obs(series,ext[(measure,"A","F")]); wl=obs(series,ext[(measure,"L","F")])
        waf1=obs(series,ext[(measure,"A","F1")]); wlf1=obs(series,ext[(measure,"L","F1")])
        if any(v is None for v in (wa,wl,waf1,wlf1)):
            errors.append(f"{label}:X:source_missing"); sectors[label]["X"]={"assets":{},"liabilities":{},"net":{}}
        else:
            rea=subtract(wa,waf1); rel=subtract(wl,wlf1)
            sectors[label]["X"]={"assets":rel,"liabilities":rea,"net":net(rel,rea)}

    assessments={}
    minimum=int(contract["consistency_gates"]["minimum_common_observation_count"])
    for label in ("stock","flow"):
        sets=[set(sectors[label][s]["net"]) for s in SECTORS]
        common=set.intersection(*sets) if sets else set(); periods=sorted(common)
        residuals={p:sum(sectors[label][s]["net"][p] for s in SECTORS) for p in periods}
        threshold=float(contract["consistency_gates"]["system_stock_residual_max_abs_million_RON" if label=="stock" else "system_flow_residual_max_abs_million_RON"])
        missing=[p for p in REQUIRED_2025 if p not in common]
        rec=bool(residuals) and all(math.isfinite(v) and abs(v)<=threshold for v in residuals.values())
        assessments[label]={"common_observation_count":len(periods),"first_common_period":periods[0] if periods else None,"last_common_period":periods[-1] if periods else None,"missing_required_2025_periods":missing,"max_absolute_system_residual_million_RON":max((abs(v) for v in residuals.values()),default=None),"reconciliation_threshold_million_RON":threshold,"system_reconciliation_pass":rec,"system_residuals_million_RON":residuals}
    measures_pass=all(x["common_observation_count"]>=minimum and not x["missing_required_2025_periods"] and x["system_reconciliation_pass"] for x in assessments.values())
    eligible=not unavailable and not network and not errors and measures_pass
    report={"audit_version":"0.1","phase":"Exploratory post-run ESA F1 applicability re-audit","reference_mode":"sectoral_financial_positions","contract":"model/dynamics/sectoral_financial_positions_esa_f1_applicability_reaudit_contract_executed_2026-09-19.json","source":{"series_requested":len(required),"series_status_counts":dict(Counter(str(x.get('status')) for x in series.values())),"network_errors_present":network,"unavailable_mandatory_series":unavailable},"construction_errors":errors,"measure_assessments":assessments,"sector_series":sectors,"source_results":series,"promotion_eligible":False,"formal_reference_mode_gate":False,"raw_gate_condition_would_pass":eligible,"accounting_spine_changed":False,"accounting_readiness_changed":False,"bilateral_materialization":False,"behavioural_closure_changed":False,"promotion_status":"EXPLORATORY_ONLY_NO_PROMOTION"}
    (OUT/"sectoral_financial_positions_phase_b_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"series_requested":len(required),"series_status_counts":report["source"]["series_status_counts"],"unavailable_mandatory_series_count":len(unavailable),"construction_errors":errors,"measure_assessments":assessments,"promotion_eligible":False,"raw_gate_condition_would_pass":eligible,"promotion_status":report["promotion_status"]},indent=2))
    if False:
        raise SystemExit("Sectoral-financial-positions Phase B gate did not pass; see retained audit artifact.")

if __name__=="__main__":
    main()
