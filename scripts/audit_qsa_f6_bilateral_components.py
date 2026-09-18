from __future__ import annotations
import csv, hashlib, io, json, math, os, urllib.error, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

OUT=Path(os.environ.get("F6_COMPONENT_OUT","f6_component_artifacts")); OUT.mkdir(parents=True,exist_ok=True)
API="https://data-api.ecb.europa.eu/service/data/QSA/"
USER_AGENT="romanian-monetary-dynamics/0.1.0 (+GitHub F6 bilateral components)"
SECTORS=("H","C","F","G","X","BNR"); RESIDENT=("H","C","F","G","BNR")
DIRECT={"H":"S1M","C":"S11","G":"S13","BNR":"S121"}
COMPONENTS=("F61","F62","F63","F64","F65","F66","F63_F64_F65")
SIX=("F61","F62","F63","F64","F65","F66")
BLOCK=("F61","F62","F63_F64_F65","F66")
TOL=0.1

@dataclass(frozen=True)
class Term:
    coefficient: float
    key: str

def sector_terms(s):
    if s in DIRECT: return ((DIRECT[s],1.0),)
    if s=="F": return (("S12",1.0),("S121",-1.0))
    raise ValueError(s)

def key(area,ref,cp,entry,measure,instrument):
    return ".".join(("Q","N","RO",area,ref,cp,"N",entry,measure,instrument,"_Z","_Z","XDC","_T","S","V","N","_T"))

def candidate_terms(holder,issuer,measure,instrument):
    if holder=="X" and issuer=="X": return {}
    if holder=="X":
        return {"issuer_liability_W1":tuple(Term(c,key("W1",s,"S1","L",measure,instrument)) for s,c in sector_terms(issuer))}
    if issuer=="X":
        return {"holder_asset_W1":tuple(Term(c,key("W1",s,"S1","A",measure,instrument)) for s,c in sector_terms(holder))}
    a=[]; l=[]
    for hs,hc in sector_terms(holder):
        for is_,ic in sector_terms(issuer):
            c=hc*ic
            a.append(Term(c,key("W2",hs,is_,"A",measure,instrument)))
            l.append(Term(c,key("W2",is_,hs,"L",measure,instrument)))
    return {"holder_asset_W2":tuple(a),"issuer_liability_W2":tuple(l)}

def aggregate_terms(sector,entry,measure,instrument):
    return tuple(Term(c,key("W0",s,"S1",entry,measure,instrument)) for s,c in sector_terms(sector))

def total_terms(area,entry,measure,instrument):
    return (Term(1.0,key(area,"S1","S1",entry,measure,instrument)),)

def sha256(b): return hashlib.sha256(b).hexdigest()

def fetch(k):
    q=urllib.parse.urlencode({"startPeriod":"2025-Q1","endPeriod":"2025-Q4","format":"csvdata"})
    url=f"{API}{k}?{q}"; req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/csv"})
    for attempt in range(1,4):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                body=r.read(); status=int(r.status); headers=dict(r.headers.items())
            break
        except urllib.error.HTTPError as e:
            body=e.read(); status=int(e.code); headers=dict(e.headers.items()); break
        except (urllib.error.URLError,TimeoutError) as e:
            if attempt==3: return {"key":k,"url":url,"status":"NETWORK_ERROR","error":str(e),"rows":[]}
    p=OUT/"raw"/f"{sha256(k.encode())[:16]}.raw"; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(body)
    out={"key":k,"url":url,"http_status":status,"raw_path":str(p.relative_to(OUT)),"raw_sha256":sha256(body),"raw_bytes":len(body),"content_type":headers.get("Content-Type"),"rows":[]}
    if status!=200: out["status"]="HTTP_ERROR"; return out
    rows=[]
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        if not row.get("TIME_PERIOD") or row.get("OBS_VALUE") in (None,""): continue
        try: v=float(row["OBS_VALUE"])
        except ValueError: continue
        rows.append({"period":row["TIME_PERIOD"],"value":v,"unit":row.get("UNIT_MEASURE") or row.get("UNIT"),"unit_mult":row.get("UNIT_MULT"),"instrument":row.get("INSTR_ASSET"),"maturity":row.get("MATURITY")})
    out["rows"]=rows; out["status"]="AVAILABLE" if rows else "NO_OBSERVATIONS"; return out

def vals(series,measure,instrument):
    if series.get("status")!="AVAILABLE": return None
    rows=series["rows"]
    if any(r.get("unit")!="XDC" or str(r.get("unit_mult"))!="6" or r.get("instrument")!=instrument or r.get("maturity") not in {"_Z",None} for r in rows): return None
    needed=("2025-Q4",) if measure=="LE" else ("2025-Q1","2025-Q2","2025-Q3","2025-Q4")
    m={str(r["period"]):float(r["value"]) for r in rows}
    if not all(p in m and math.isfinite(m[p]) for p in needed): return None
    return [m[p] for p in needed]

def evaluate(terms,series,measure,instrument):
    total=0.0; detail=[]
    for t in terms:
        vs=vals(series[t.key],measure,instrument); detail.append({"coefficient":t.coefficient,"key":t.key,"usable":vs is not None,"values":vs})
        if vs is None: return None,detail
        total+=t.coefficient*(vs[0] if measure=="LE" else sum(vs))
    return total,detail

def resolve(formulas,series,measure,instrument):
    ors={}
    for name,terms in formulas.items():
        value,detail=evaluate(terms,series,measure,instrument); ors[name]={"value_million_RON":value,"terms":detail}
    usable={n:x for n,x in ors.items() if x["value_million_RON"] is not None}
    if not usable: return {"status":"UNRESOLVED_SOURCE_COVERAGE","value_million_RON":None,"selected_orientation":None,"orientation_results":ors}
    vv=[float(x["value_million_RON"]) for x in usable.values()]
    if len(vv)>1 and max(vv)-min(vv)>TOL: return {"status":"ORIENTATION_CONFLICT","value_million_RON":None,"selected_orientation":None,"orientation_results":ors}
    sel="holder_asset_W2" if "holder_asset_W2" in usable else next(iter(usable))
    return {"status":"OBSERVABLE_OR_EXACT_DERIVATION","value_million_RON":usable[sel]["value_million_RON"],"selected_orientation":sel,"orientation_results":ors}

def main():
    required=set(); plans=[]
    for measure in ("LE","F"):
        for h in SECTORS:
            for i in SECTORS:
                by={}
                for comp in COMPONENTS:
                    fs=candidate_terms(h,i,measure,comp); by[comp]=fs
                    for ts in fs.values(): required.update(t.key for t in ts)
                plans.append((measure,h,i,by))
    controls=[]
    for measure in ("LE","F"):
        for sector in RESIDENT:
            for kind,entry in (("holder_total","A"),("issuer_total","L")):
                ts=aggregate_terms(sector,entry,measure,"F6"); controls.append((measure,kind,sector,ts)); required.update(t.key for t in ts)
    totals=[]
    for measure in ("LE","F"):
        for area in ("W0","W1"):
            for entry in ("A","L"):
                ts=total_terms(area,entry,measure,"F6"); totals.append((measure,area,entry,ts)); required.update(t.key for t in ts)

    series={}
    with ThreadPoolExecutor(max_workers=12) as ex:
        fut={ex.submit(fetch,k):k for k in sorted(required)}
        for n,f in enumerate(as_completed(fut),1):
            k=fut[f]; series[k]=f.result(); print(f"[{n}/{len(fut)}] {k}",flush=True)

    cells=[]; counts={c:Counter() for c in COMPONENTS}
    for measure,h,i,by in plans:
        label="stock" if measure=="LE" else "flow"
        if h=="X" and i=="X":
            cells.append({"measure":label,"holder":h,"issuer":i,"status":"OUTSIDE_BOUNDARY_NOT_APPLICABLE","value_million_RON":None,"components":{}}); continue
        resolved={}
        for comp in COMPONENTS:
            x=resolve(by[comp],series,measure,comp); resolved[comp]=x; counts[comp][x["status"]]+=1
        six_ok=all(resolved[c]["status"]=="OBSERVABLE_OR_EXACT_DERIVATION" for c in SIX)
        block_ok=all(resolved[c]["status"]=="OBSERVABLE_OR_EXACT_DERIVATION" for c in BLOCK)
        six_value=sum(float(resolved[c]["value_million_RON"]) for c in SIX) if six_ok else None
        block_value=sum(float(resolved[c]["value_million_RON"]) for c in BLOCK) if block_ok else None
        if six_ok and block_ok and abs(six_value-block_value)>TOL:
            status="COMPONENT_IDENTITY_CONFLICT"; value=None
        elif six_ok:
            status="EXACT_COMPONENT_DERIVATION"; value=six_value
        elif block_ok:
            status="EXACT_COMPONENT_DERIVATION"; value=block_value
        else:
            status="UNRESOLVED_COMPONENT_COVERAGE"; value=None
        cells.append({"measure":label,"holder":h,"issuer":i,"status":status,"value_million_RON":value,"six_component_candidate_million_RON":six_value,"transmission_block_candidate_million_RON":block_value,"components":resolved})

    recon=[]
    for measure,kind,sector,ts in controls:
        label="stock" if measure=="LE" else "flow"; official,detail=evaluate(ts,series,measure,"F6")
        related=[c for c in cells if c["measure"]==label and (c["holder"]==sector if kind=="holder_total" else c["issuer"]==sector) and c["status"]!="OUTSIDE_BOUNDARY_NOT_APPLICABLE"]
        complete=all(c["status"]=="EXACT_COMPONENT_DERIVATION" for c in related)
        bilateral=sum(float(c["value_million_RON"]) for c in related) if complete else None
        residual=None if official is None or bilateral is None else bilateral-float(official)
        status="CONTROL_UNAVAILABLE" if official is None else "BILATERAL_COVERAGE_INCOMPLETE" if not complete else "PASS" if abs(residual)<=TOL else "FAIL"
        recon.append({"measure":label,"kind":kind,"sector":sector,"bilateral_complete":complete,"bilateral_sum_million_RON":bilateral,"official_F6_aggregate_million_RON":official,"residual_million_RON":residual,"status":status,"terms":detail})

    total_items=[]; lookup={}
    for measure,area,entry,ts in totals:
        label="stock" if measure=="LE" else "flow"; value,detail=evaluate(ts,series,measure,"F6"); lookup[(label,area,entry)]=value
        total_items.append({"measure":label,"area":area,"entry":entry,"value_million_RON":value,"status":"AVAILABLE" if value is not None else "UNAVAILABLE","terms":detail})
    external=[]
    for label in ("stock","flow"):
        for kind,related,entry in (
            ("resident_holder_to_X",[c for c in cells if c["measure"]==label and c["issuer"]=="X" and c["holder"] in RESIDENT],"A"),
            ("X_holder_to_resident_issuer",[c for c in cells if c["measure"]==label and c["holder"]=="X" and c["issuer"] in RESIDENT],"L")):
            complete=all(c["status"]=="EXACT_COMPONENT_DERIVATION" for c in related); bilateral=sum(float(c["value_million_RON"]) for c in related) if complete else None; official=lookup[(label,"W1",entry)]
            residual=None if bilateral is None or official is None else bilateral-float(official)
            status="CONTROL_UNAVAILABLE" if official is None else "BILATERAL_COVERAGE_INCOMPLETE" if not complete else "PASS" if abs(residual)<=TOL else "FAIL"
            external.append({"measure":label,"kind":kind,"bilateral_complete":complete,"bilateral_sum_million_RON":bilateral,"published_W1_F6_million_RON":official,"residual_million_RON":residual,"status":status})

    report={"audit_version":"0.1","instrument":"F6","phase":"bilateral component coverage audit","benchmark_changed":False,"materialization_allowed_by_this_phase":False,"behavioural_closure_changed":False,"series_requested":len(required),"series_status_counts":dict(Counter(str(x.get("status")) for x in series.values())),"component_cell_status_counts":{c:dict(counts[c]) for c in COMPONENTS},"derived_F6_cell_status_counts":dict(Counter(c["status"] for c in cells)),"reconciliation_status_counts":dict(Counter(x["status"] for x in recon)),"external_control_status_counts":dict(Counter(x["status"] for x in external)),"network_errors_present":any(x.get("status")=="NETWORK_ERROR" for x in series.values()),"cells":cells,"aggregate_reconciliation":recon,"total_F6_controls":total_items,"external_F6_controls":external,"rule":"F6 is derived bilaterally only from a complete six-component identity or a complete F61+F62+F63_F64_F65+F66 transmission-block identity. No missing component or issuer zero is inferred."}
    (OUT/"f6_bilateral_component_coverage_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"series_requested":report["series_requested"],"series_status_counts":report["series_status_counts"],"component_cell_status_counts":report["component_cell_status_counts"],"derived_F6_cell_status_counts":report["derived_F6_cell_status_counts"],"network_errors_present":report["network_errors_present"]},indent=2))

if __name__=="__main__": main()
