from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model"/"calibration_validation"/"bnr_bls_cross_round_mapping_contract.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def recovered_rows(contract: dict) -> tuple[list[dict], dict, Path]:
    review_path=ROOT/contract["recovered_round_semantic_review"]
    review=json.loads(review_path.read_text(encoding="utf-8"))
    policy=contract["recovered_round_policy"]
    if review["status"] != policy["required_status"]:
        raise RuntimeError(f"recovered-round semantic review not passed: {review['status']}")
    if review["passed_rounds"] != policy["allowed_quarters"]:
        raise RuntimeError(
            f"unexpected recovered-round set: {review['passed_rounds']}"
        )

    rows=[]
    validations={}
    for item in review["results"]:
        quarter=item["target_quarter"]
        if quarter not in policy["allowed_quarters"]:
            raise RuntimeError(f"unauthorized recovered quarter: {quarter}")
        if policy["require_all_six_observables_passed"] and not item["all_six_observables_passed"]:
            raise RuntimeError(f"six-observable semantic gate failed: {quarter}")
        if policy["require_dsti_boundary_markers_verified"] and not item["dsti_boundary_markers_verified"]:
            raise RuntimeError(f"DSTI boundary markers failed: {quarter}")

        identity=item["round_identity"]
        authority=identity["authority"]
        if authority=="WORKBOOK_COMPANIES_A1":
            reference_date=identity["raw_workbook_header"]
        elif authority=="OFFICIAL_BNR_PUBLICATION_QUARTER":
            if identity.get("silent_date_normalisation_performed") is not False:
                raise RuntimeError(f"silent date normalisation state invalid: {quarter}")
            reference_date=""
        else:
            raise RuntimeError(f"unsupported recovered-round authority: {authority}")

        source=item["row"]
        row={
            "quarter":quarter,
            "reference_date":reference_date,
            "source_id":source["source_id"],
            "source_kind":source["source_kind"],
            "nfc_credit_standards":float(source["nfc_credit_standards"]),
            "nfc_loan_demand":float(source["nfc_loan_demand"]),
            "household_mortgage_credit_standards":float(source["household_mortgage_credit_standards"]),
            "household_consumer_credit_standards":float(source["household_consumer_credit_standards"]),
            "household_mortgage_loan_demand":float(source["household_mortgage_loan_demand"]),
            "household_consumer_loan_demand":float(source["household_consumer_loan_demand"]),
        }
        rows.append(row)

        observable_validations={}
        for key,value in item["observable_validations"].items():
            copied=dict(value)
            numeric_value=copied.get("value")
            if isinstance(numeric_value,float) and numeric_value.is_integer():
                copied["value"]=int(numeric_value)
            observable_validations[key]=copied
        validations[quarter]={
            "source_id":item["source_id"],
            "round_identity":item["round_identity"],
            "observable_validations":observable_validations,
            "all_six_observables_passed":item["all_six_observables_passed"],
            "dsti_boundary_markers_verified":item["dsti_boundary_markers_verified"],
        }
    return rows,validations,review_path


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
    recovered,recovered_validations,semantic_path=recovered_rows(c)
    rows.extend(recovered)
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

    promotion_path=ROOT/c["canonical_promotion_review"]
    promotion=json.loads(promotion_path.read_text(encoding="utf-8"))
    expected_files={item["path"]:item for item in promotion["expected_candidate_files"]}
    promoted_panel_sha=sha256(panel_path)
    approved_sha=promotion["approved_post_promotion"]["canonical_panel_sha256"]
    if promoted_panel_sha != approved_sha:
        raise RuntimeError(
            f"materialized panel SHA mismatch: {promoted_panel_sha} != {approved_sha}"
        )

    audit={
        "audit_version":"0.1",
        "phase":c["phase"],
        "status":c["canonical_status"],
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
        "recovered_missing_round_validations":{
            "semantic_review":c["recovered_round_semantic_review"],
            "semantic_review_sha256":sha256(semantic_path),
            "rounds":recovered_validations,
        },
        "canonical_panel_promotion":{
            "review":c["canonical_promotion_review"],
            "source_candidate_contract":promotion["source_candidate_contract"],
            "source_workflow_run_id":promotion["source_workflow_run_id"],
            "source_job_id":promotion["source_job_id"],
            "source_artifact_id":promotion["source_artifact_id"],
            "source_artifact_name":promotion["source_artifact_name"],
            "source_artifact_zip_sha256":promotion["source_artifact_zip_sha256"],
            "candidate_panel_sha256":expected_files["bnr_bls_realised_rounds_candidate.csv"]["sha256"],
            "candidate_audit_sha256":expected_files["bnr_bls_panel_regeneration_candidate_audit.json"]["sha256"],
            "previous_canonical_panel_sha256":promotion["expected_pre_promotion"]["canonical_panel_sha256"],
            "promoted_canonical_panel_sha256":approved_sha,
            "promoted_rounds":c["recovered_round_policy"]["allowed_quarters"],
            "remaining_gap":missing[0] if len(missing)==1 else missing,
            "parameter_estimation_authorized":promotion["promotion_effect"]["parameter_estimation_authorized"],
            "behavioural_closure_change":promotion["promotion_effect"]["behavioural_closure_change"],
        },
    }
    audit_path=ROOT/"model"/"calibration_validation"/c["output_files"]["audit"]
    audit_path.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
