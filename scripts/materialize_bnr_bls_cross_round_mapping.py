from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model"/"calibration_validation"/"bnr_bls_cross_round_mapping_contract.json"


def quarter_index(period: str) -> int:
    y,q=period.split("-Q")
    return int(y)*4+int(q)-1


def quarter_from_date(text: str) -> str:
    dt=datetime.strptime(text,"%d/%m/%Y")
    return f"{dt.year:04d}-Q{(dt.month-1)//3+1}"


def load_cells(path: Path) -> dict:
    j=json.loads(path.read_text(encoding="utf-8"))
    sheets={}
    for sheet in j["sheets"]:
        sheets[sheet["name"]]={
            cell["coordinate"]:cell["value"]
            for cell in sheet["cells"]
        }
    return {"raw":j,"sheets":sheets}


def choose_sheet(sheets: dict, aliases: list[str]) -> tuple[str,dict]:
    hits=[name for name in aliases if name in sheets]
    if len(hits)!=1:
        raise ValueError(f"expected exactly one sheet alias from {aliases}, got {hits}")
    name=hits[0]
    return name,sheets[name]


def numeric(cellmap: dict, coord: str) -> float:
    value=cellmap.get(coord)
    if not isinstance(value,(int,float)):
        raise ValueError(f"expected numeric {coord}, got {value!r}")
    return float(value)


def legacy_row(contract: dict, source: dict) -> dict:
    root=ROOT/contract["legacy_extraction_vintage"]
    loaded=load_cells(root/source["file"])
    _,companies=choose_sheet(loaded["sheets"],contract["sheet_name_aliases"]["companies"])
    _,households=choose_sheet(loaded["sheets"],contract["sheet_name_aliases"]["households"])

    date_rule=contract["date_rule"]
    round_company=companies.get(date_rule["legacy_round_date_cell"])
    if not isinstance(round_company,str) or not round_company.strip():
        raise ValueError(
            f"{source['source_id']} missing authoritative companies-sheet "
            f"round date at {date_rule['legacy_round_date_cell']}"
        )
    quarter=quarter_from_date(round_company.strip())

    household_header_diagnostics={
        coord:households.get(coord)
        for coord in date_rule["household_header_diagnostic_cells"]
    }

    row={
        "quarter":quarter,
        "reference_date":round_company.strip(),
        "source_id":source["source_id"],
        "source_kind":"legacy_xls_full_cell_extraction",
    }
    validation={
        "round_date_authority":{
            "sheet":date_rule["legacy_round_date_authoritative_sheet"],
            "cell":date_rule["legacy_round_date_cell"],
            "value":round_company.strip(),
            "household_header_diagnostics":household_header_diagnostics,
            "household_header_date_consistency_required":
                date_rule["household_header_date_consistency_required"],
        }
    }
    for obs in contract["realised_observables"]:
        cellmap=companies if obs["question_id"].startswith("C") else households
        if cellmap.get(obs["question_cell"]) != obs["question_id"]:
            raise ValueError(
                f"{source['source_id']} {obs['id']} question-id mismatch at "
                f"{obs['question_cell']}"
            )
        metric_label=str(cellmap.get(obs["metric_label_cell"],"")).strip()
        if metric_label not in obs["allowed_metric_labels"]:
            raise ValueError(
                f"{source['source_id']} {obs['id']} metric label mismatch: "
                f"{metric_label!r}"
            )
        row[obs["id"]]=numeric(cellmap,obs["net_percentage_cell"])
        validation[obs["id"]]={
            "question_id":obs["question_id"],
            "question_cell":obs["question_cell"],
            "net_percentage_cell":obs["net_percentage_cell"],
            "metric_label":metric_label,
        }

    # Explicitly verify, but do not materialize, the DSTI term-change questions.
    for qid,coord in [("P0303","A59"),("P1103","A212")]:
        if households.get(coord) != qid:
            raise ValueError(f"{source['source_id']} missing {qid} at {coord}")

    row["_validation"]=validation
    return row


def may_2025_row(contract: dict) -> dict:
    review=json.loads((ROOT/contract["xlsx_layout_review"]).read_text(encoding="utf-8"))
    s=review["realised_bls_semantics"]
    return {
        "quarter":contract["may_2025_rule"]["round"],
        "reference_date":review["source_workbooks"]["english"]["round_date"],
        "source_id":"bls_2025_may_xlsx_review",
        "source_kind":"independently_reviewed_xlsx_layout",
        "nfc_credit_standards":float(s["nfc_credit_standards"]["net_percentage"]),
        "nfc_loan_demand":float(s["nfc_loan_demand"]["net_percentage"]),
        "household_mortgage_credit_standards":float(s["household_mortgage_credit_standards"]["net_percentage"]),
        "household_consumer_credit_standards":float(s["household_consumer_credit_standards"]["net_percentage"]),
        "household_mortgage_loan_demand":float(s["household_mortgage_loan_demand"]["net_percentage"]),
        "household_consumer_loan_demand":float(s["household_consumer_loan_demand"]["net_percentage"]),
        "_validation":{"source_review":contract["xlsx_layout_review"]},
    }


def all_quarters(start: str,end: str) -> list[str]:
    a,b=quarter_index(start),quarter_index(end)
    out=[]
    for idx in range(a,b+1):
        y,q0=divmod(idx,4)
        out.append(f"{y:04d}-Q{q0+1}")
    return out


def main() -> None:
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows=[legacy_row(c,item) for item in c["source_round_mapping"]]
    rows.append(may_2025_row(c))
    rows.sort(key=lambda r:quarter_index(r["quarter"]))

    quarters=[r["quarter"] for r in rows]
    if len(quarters)!=len(set(quarters)):
        raise RuntimeError(f"duplicate BLS quarters: {quarters}")

    expected=all_quarters(quarters[0],quarters[-1])
    missing=[q for q in expected if q not in set(quarters)]

    out_dir=ROOT/"data"/"processed"
    out_dir.mkdir(parents=True,exist_ok=True)
    panel_path=out_dir/c["output_files"]["panel"]
    fields=[
        "quarter","reference_date","source_id","source_kind",
        "nfc_credit_standards","nfc_loan_demand",
        "household_mortgage_credit_standards",
        "household_consumer_credit_standards",
        "household_mortgage_loan_demand",
        "household_consumer_loan_demand",
    ]
    with panel_path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key:row[key] for key in fields})

    audit={
        "audit_version":"0.1",
        "phase":c["phase"],
        "status":"PASS_BLS_MULTI_ROUND_MAPPING_WITH_EXPLICIT_GAPS",
        "observed_round_count":len(rows),
        "first_observed_quarter":quarters[0],
        "last_observed_quarter":quarters[-1],
        "expected_quarter_count_between_bounds":len(expected),
        "coverage_fraction":len(rows)/len(expected),
        "observed_quarters":quarters,
        "missing_quarters":missing,
        "legacy_round_validations":{
            row["source_id"]:row["_validation"]
            for row in rows
            if row["source_kind"]=="legacy_xls_full_cell_extraction"
        },
        "may_2025_source_review":c["xlsx_layout_review"],
        "dsti_boundary":c["dsti_boundary"],
        "interpolation_performed":False,
        "synthetic_quarters_created":False,
        "parameter_estimation_performed":False,
        "model_selection_performed":False,
        "system_dynamics_activation":False,
        "behavioural_closure_change":False,
        "hard_rules":c["hard_rules"],
    }
    audit_path=ROOT/"model"/"calibration_validation"/c["output_files"]["audit"]
    audit_path.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
