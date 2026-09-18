from __future__ import annotations
import argparse, json
from fractions import Fraction
from pathlib import Path

SECTORS=("H","C","F","G","X","BNR")
RESIDENT=("H","C","F","G","BNR")
TOL=0.1

def variables():
    return [(h,i) for h in SECTORS for i in SECTORS if not (h=="X" and i=="X")]

def rref_nullspace(equations,vars_):
    idx={v:i for i,v in enumerate(vars_)}
    m=[]
    for eq in equations:
        row=[Fraction(0) for _ in vars_]
        for v,c in eq.items(): row[idx[v]]=Fraction(c)
        m.append(row)
    rows=len(m); cols=len(vars_); piv=[]; pr=0
    for c in range(cols):
        cand=next((r for r in range(pr,rows) if m[r][c]!=0),None)
        if cand is None: continue
        m[pr],m[cand]=m[cand],m[pr]
        p=m[pr][c]; m[pr]=[x/p for x in m[pr]]
        for r in range(rows):
            if r==pr: continue
            f=m[r][c]
            if f!=0: m[r]=[m[r][j]-f*m[pr][j] for j in range(cols)]
        piv.append(c); pr+=1
        if pr==rows: break
    free=[c for c in range(cols) if c not in piv]
    ns=[]
    for f in free:
        v=[Fraction(0) for _ in range(cols)]; v[f]=Fraction(1)
        for r,p in enumerate(piv): v[p]=-m[r][f]
        ns.append(v)
    return len(piv),ns

def identify(eqs,vars_):
    rank,ns=rref_nullspace(eqs,vars_)
    unique=[]; nonunique=[]
    for i,v in enumerate(vars_):
        label=f"{v[0]}→{v[1]}"
        (unique if all(n[i]==0 for n in ns) else nonunique).append(label)
    return {"variables":len(vars_),"equations":len(eqs),"rank":rank,"nullity":len(vars_)-rank,"unique_cell_count":len(unique),"nonunique_cell_count":len(nonunique),"unique_cells":unique,"nonunique_cells":nonunique}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase-a-report",type=Path,default=Path("f6_phase_a_artifacts/f6_insurance_pensions_coverage_audit.json"))
    p.add_argument("--out",type=Path,default=Path("f6_rank_artifacts"))
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    phase=json.loads(a.phase_a_report.read_text(encoding="utf-8"))
    if phase["instrument"]!="F6": raise RuntimeError("Phase A report is not F6")
    if phase["network_errors_present"]: raise RuntimeError("Phase A network errors block rank claim")
    if phase["cell_status_counts"].get("OBSERVABLE_OR_EXACT_DERIVATION",0)!=0: raise RuntimeError("Phase C expects zero direct bilateral total-F6 cells")

    aggregate={(x["measure"],x["kind"],x["sector"]):x for x in phase["aggregate_reconciliation"]}
    totals={}
    for x in phase["total_economy_component_controls"]:
        totals[(x["measure"],x["area"],x["entry"])]=x["values_million_RON"]["F6"]

    vars_=variables(); analyses={}
    for measure in ("stock","flow"):
        eqs=[]; labels=[]
        def add(eq,label): eqs.append(eq); labels.append(label)
        for s in RESIDENT:
            h=aggregate[(measure,"holder_total",s)]["official_F6_aggregate_million_RON"]
            i=aggregate[(measure,"issuer_total",s)]["official_F6_aggregate_million_RON"]
            if h is None or i is None: raise RuntimeError(f"Missing W0 F6 control {measure} {s}")
            add({(s,j):1 for j in SECTORS},f"W0-holder:{s}")
            add({(j,s):1 for j in SECTORS},f"W0-issuer:{s}")
        wa=totals[(measure,"W1","A")]; wl=totals[(measure,"W1","L")]
        if wa is None or wl is None: raise RuntimeError(f"Missing W1 F6 controls {measure}")
        add({(h,"X"):1 for h in RESIDENT},"W1-assets")
        add({("X",i):1 for i in RESIDENT},"W1-liabilities")
        ident=identify(eqs,vars_)

        hs=sum(float(aggregate[(measure,"holder_total",s)]["official_F6_aggregate_million_RON"]) for s in RESIDENT)
        is_=sum(float(aggregate[(measure,"issuer_total",s)]["official_F6_aggregate_million_RON"]) for s in RESIDENT)
        da=hs-float(wa); dl=is_-float(wl); resid=da-dl
        analyses[measure]={
          "equation_labels":labels,
          "unconditional_identification":ident,
          "RHS_accounting_identity":{
            "resident_holder_W0_sum_million_RON":hs,
            "W1_assets_million_RON":wa,
            "domestic_from_assets_million_RON":da,
            "resident_issuer_W0_sum_million_RON":is_,
            "W1_liabilities_million_RON":wl,
            "domestic_from_liabilities_million_RON":dl,
            "residual_million_RON":resid,
            "status":"PASS" if abs(resid)<=TOL else "FAIL"
          }
        }

    freeze=all(analyses[m]["unconditional_identification"]["unique_cell_count"]==0 for m in ("stock","flow")) and all(analyses[m]["RHS_accounting_identity"]["status"]=="PASS" for m in ("stock","flow"))
    report={
      "audit_version":"0.1","instrument":"F6","phase":"exact aggregate-control rank audit",
      "benchmark_changed":False,"materialization_allowed_by_this_phase":False,"behavioural_closure_changed":False,
      "phase_A_source_summary":{"series_requested":phase["series_requested"],"series_status_counts":phase["series_status_counts"],"cell_status_counts":phase["cell_status_counts"],"network_errors_present":phase["network_errors_present"]},
      "analyses":analyses,
      "disposition":"FREEZE_F6_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY" if freeze else "REVIEW_F6_IDENTIFICATION_BEFORE_DISPOSITION",
      "rule":"Only published W0/W1 total-F6 equations enter the unconditional rank system. No issuer applicability, non-negativity or missing-to-zero equation is added."
    }
    (a.out/"f6_aggregate_rank_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"stock":analyses["stock"],"flow":analyses["flow"],"disposition":report["disposition"]},indent=2))

if __name__=="__main__": main()
